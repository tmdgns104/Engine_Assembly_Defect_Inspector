"""Single service-owned journal. Durable assets precede immutable result/event/outbox commit."""

import json
import shutil
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from apps.edge_service.bench import atomic_write
from src.recipe.package import canonical, sha256


class ConflictError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_key(request):
    if not isinstance(request.get("cell_id"), str) or not request["cell_id"].strip() or len(request["cell_id"]) > 100:
        raise ValueError("Invalid cell_id")
    for key in ("plc_session_id", "request_id", "cycle_id", "attempt"):
        if type(request.get(key)) is not int or not 1 <= request[key] <= 4294967295:
            raise ValueError("Invalid " + key)
    return (request["cell_id"], request["plc_session_id"], request["request_id"])


SCHEMA = """
CREATE TABLE cycles (
 cell_id TEXT NOT NULL CHECK(length(trim(cell_id))>0),
 plc_session_id INTEGER NOT NULL CHECK(plc_session_id BETWEEN 1 AND 4294967295),
 cycle_id INTEGER NOT NULL CHECK(cycle_id BETWEEN 1 AND 4294967295),
 started_at TEXT NOT NULL, terminal TEXT,
 PRIMARY KEY(cell_id,plc_session_id,cycle_id));
CREATE TABLE inspections (
 inspection_id TEXT PRIMARY KEY, cell_id TEXT NOT NULL, plc_session_id INTEGER NOT NULL,
 request_id INTEGER NOT NULL CHECK(request_id BETWEEN 1 AND 4294967295), cycle_id INTEGER NOT NULL,
 attempt INTEGER NOT NULL CHECK(attempt>=1), fingerprint TEXT NOT NULL, request_json TEXT NOT NULL,
 package_json TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('ACCEPTED','COMPLETE','CANCELLED')),
 decision TEXT CHECK(decision IN ('PASS','FAIL','REVIEW','ERROR')), result_json TEXT,
 accepted_at TEXT NOT NULL, completed_at TEXT,
 UNIQUE(cell_id,plc_session_id,request_id),
 FOREIGN KEY(cell_id,plc_session_id,cycle_id) REFERENCES cycles(cell_id,plc_session_id,cycle_id));
CREATE TABLE defects (defect_id TEXT PRIMARY KEY, inspection_id TEXT NOT NULL REFERENCES inspections,
 code TEXT NOT NULL, slot TEXT, payload_json TEXT NOT NULL);
CREATE TABLE frame_assets (asset_id TEXT PRIMARY KEY, inspection_id TEXT NOT NULL REFERENCES inspections,
 kind TEXT NOT NULL, relative_path TEXT NOT NULL UNIQUE, sha256 TEXT NOT NULL, width INTEGER NOT NULL CHECK(width>0),
 height INTEGER NOT NULL CHECK(height>0), bytes INTEGER NOT NULL CHECK(bytes>0), capture_at TEXT, view TEXT NOT NULL,
 sync_state TEXT NOT NULL DEFAULT 'PENDING');
CREATE TABLE events (event_id TEXT PRIMARY KEY, producer_id TEXT NOT NULL, producer_session TEXT NOT NULL,
 producer_seq INTEGER NOT NULL, occurred_at TEXT NOT NULL, received_at TEXT NOT NULL,
 event_type TEXT NOT NULL, payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 UNIQUE(producer_id,producer_session,producer_seq));
CREATE TABLE outbox (event_id TEXT PRIMARY KEY REFERENCES events, state TEXT NOT NULL DEFAULT 'PENDING',
 attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, acknowledged_at TEXT);
CREATE TABLE dispositions (disposition_id TEXT PRIMARY KEY, inspection_id TEXT NOT NULL REFERENCES inspections,
 disposition TEXT NOT NULL CHECK(disposition IN ('PENDING','RELEASED','QUARANTINED','REMOVED','ABORTED')),
 actor TEXT NOT NULL, reason TEXT NOT NULL, occurred_at TEXT NOT NULL);
CREATE TABLE calibrations (calibration_id TEXT PRIMARY KEY, package_sha256 TEXT NOT NULL,
 station_id TEXT NOT NULL, payload_json TEXT NOT NULL, confirmed_at TEXT NOT NULL);
CREATE TABLE service_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE quarantine (quarantine_id TEXT PRIMARY KEY, event_id TEXT, reason TEXT NOT NULL,
 payload_json TEXT NOT NULL, received_at TEXT NOT NULL);
PRAGMA user_version=1;
"""


class Journal:
    def __init__(self, data_root, producer_id="edge", min_free_bytes=100_000_000, outbox_limit=10000):
        self.root = Path(data_root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.producer_id, self.producer_session = producer_id, uuid.uuid4().hex
        self.min_free_bytes, self.outbox_limit = min_free_bytes, outbox_limit
        self.db = sqlite3.connect(self.root / "journal.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if tables:
                backup = sqlite3.connect(self.root / ("migration_backup_" + uuid.uuid4().hex + ".sqlite3"))
                self.db.backup(backup)
                backup.close()
                raise RuntimeError("Unknown existing schema preserved; explicit migration required")
            self.db.executescript(SCHEMA)
        elif version != 1:
            raise RuntimeError("Unsupported journal version; database preserved")
        assert self.db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert self.db.execute("PRAGMA synchronous").fetchone()[0] == 2

    def new_session(self, cell_id):
        key = "session:" + cell_id
        with self.lock, self.db:
            row = self.db.execute("SELECT value FROM service_state WHERE key=?", (key,)).fetchone()
            value = int(row[0]) + 1 if row else 1
            if value > 4294967295:
                raise RuntimeError("Session counter exhausted; new namespace required")
            self.db.execute("INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        return value

    def capacity(self):
        with self.lock:
            pending = self.db.execute("SELECT count(*) FROM outbox WHERE state!='ACKED'").fetchone()[0]
        if shutil.disk_usage(self.root).free < self.min_free_bytes:
            raise OSError("DISK_SPACE_LOW")
        if pending >= self.outbox_limit:
            raise OSError("OUTBOX_FULL")

    def find_request(self, request):
        key = validate_key(request)
        with self.lock:
            row = self.db.execute("SELECT * FROM inspections WHERE cell_id=? AND plc_session_id=? AND request_id=?", key).fetchone()
        if row and row["fingerprint"] != sha256(canonical(request).encode()):
            raise ConflictError("REQUEST_PAYLOAD_CONFLICT")
        return dict(row) if row else None

    def admit(self, request, package_snapshot):
        validate_key(request)
        self.capacity()
        with self.lock, self.db:
            existing = self.find_request(request)
            if existing:
                return existing["inspection_id"], False
            inspection_id = uuid.uuid4().hex
            self.db.execute("INSERT INTO cycles(cell_id,plc_session_id,cycle_id,started_at) VALUES (?,?,?,?) ON CONFLICT(cell_id,plc_session_id,cycle_id) DO NOTHING",
                            (request["cell_id"], request["plc_session_id"], request["cycle_id"], now()))
            self.db.execute("INSERT INTO inspections(inspection_id,cell_id,plc_session_id,request_id,cycle_id,attempt,fingerprint,request_json,package_json,state,accepted_at) VALUES (?,?,?,?,?,?,?,?,?,'ACCEPTED',?)",
                            (inspection_id, request["cell_id"], request["plc_session_id"], request["request_id"], request["cycle_id"], request["attempt"],
                             sha256(canonical(request).encode()), canonical(request), canonical(package_snapshot), now()))
        return inspection_id, True

    def _event(self, event_type, payload):
        seq = self.db.execute("SELECT COALESCE(MAX(producer_seq),0)+1 FROM events WHERE producer_id=? AND producer_session=?", (self.producer_id,self.producer_session)).fetchone()[0]
        event = {"schema_version": 1, "event_id": uuid.uuid4().hex, "producer_id": self.producer_id,
                 "producer_session": self.producer_session, "producer_seq": seq, "occurred_at": now(),
                 "event_type": event_type, "payload": payload}
        body = canonical(event)
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)", (event["event_id"],self.producer_id,self.producer_session,seq,event["occurred_at"],now(),event_type,body,sha256(body.encode())))
        self.db.execute("INSERT INTO outbox(event_id) VALUES (?)", (event["event_id"],))
        return event

    def finish(self, inspection_id, result, images=()):
        self.capacity()
        with self.lock:
            row = self.db.execute("SELECT * FROM inspections WHERE inspection_id=?", (inspection_id,)).fetchone()
            if not row:
                raise KeyError(inspection_id)
            if row["state"] != "ACCEPTED":
                with self.db:
                    self._event("LATE_RESULT_QUARANTINED", {"inspection_id": inspection_id, "reason": row["state"]})
                return None
            if result.get("decision") not in ("PASS", "FAIL", "REVIEW", "ERROR"):
                raise ValueError("Invalid decision")
            if result["decision"] != "ERROR" and not any(image["kind"] == "raw" for image in images):
                raise ValueError("Non-error result requires original evidence")
            assets = []
            directory = self.root / "assets" / inspection_id
            directory.mkdir(parents=True, exist_ok=True)
            for image in images:
                data = image["data"]
                if not isinstance(data, bytes) or not 0 < len(data) <= 20_000_000:
                    raise ValueError("Invalid asset data")
                asset_id = uuid.uuid4().hex
                suffix = ".png" if image["kind"] == "raw" else ".jpg"
                path = directory / (asset_id + suffix)
                atomic_write(path, data)
                assets.append({"asset_id": asset_id, "inspection_id": inspection_id, "kind": image["kind"],
                               "relative_path": path.relative_to(self.root).as_posix(), "sha256": sha256(data),
                               "width": image["width"], "height": image["height"], "bytes": len(data),
                               "capture_at": image.get("capture_at"), "view": image.get("view", "top")})
            completed = dict(result, inspection_id=inspection_id, assets=assets, completed_at=now(),
                             request=json.loads(row["request_json"]), package=json.loads(row["package_json"]), accepted_at=row['accepted_at'], storage_success=True)
            with self.db:
                self.db.execute("UPDATE inspections SET state='COMPLETE',decision=?,result_json=?,completed_at=? WHERE inspection_id=? AND state='ACCEPTED'",
                                (completed["decision"],canonical(completed),completed["completed_at"],inspection_id))
                for asset in assets:
                    self.db.execute("INSERT INTO frame_assets(asset_id,inspection_id,kind,relative_path,sha256,width,height,bytes,capture_at,view) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                    tuple(asset[key] for key in ("asset_id","inspection_id","kind","relative_path","sha256","width","height","bytes","capture_at","view")))
                for defect in completed.get("defects", []):
                    self.db.execute("INSERT INTO defects VALUES (?,?,?,?,?)", (uuid.uuid4().hex,inspection_id,defect["code"],defect.get("slot"),canonical(defect)))
                self._event("INSPECTION_COMPLETED", completed)
                if completed['request'].get('control_mode') != 'mock':
                    self.db.execute("UPDATE cycles SET terminal='INSPECTION_ONLY' WHERE cell_id=? AND plc_session_id=? AND cycle_id=?",
                                    (row['cell_id'],row['plc_session_id'],row['cycle_id']))
        # Reached only after successful DB commit. The caller may publish this result now.
        return completed

    def cancel(self, inspection_id, reason):
        with self.lock, self.db:
            row = self.db.execute("SELECT * FROM inspections WHERE inspection_id=?", (inspection_id,)).fetchone()
            if row and row["state"] == "ACCEPTED":
                result = {"decision": "ERROR", "reason": reason, "inspection_id": inspection_id,
                          "storage_success": True, "completed_at": now(), "assets": [], "evidence_missing_reason": reason,
                          'request':json.loads(row['request_json']), 'package':json.loads(row['package_json']), 'accepted_at':row['accepted_at']}
                self.db.execute("UPDATE inspections SET state='CANCELLED',decision='ERROR',result_json=?,completed_at=? WHERE inspection_id=?", (canonical(result),now(),inspection_id))
                self._event("INSPECTION_CANCELLED", result)

    def recover(self):
        with self.lock:
            unfinished = self.db.execute("SELECT inspection_id FROM inspections WHERE state='ACCEPTED'").fetchall()
            known = {row[0] for row in self.db.execute("SELECT relative_path FROM frame_assets")}
        for row in unfinished:
            self.cancel(row[0], "RECOVERY_UNFINISHED_REQUEST")
        orphaned = [str(path.relative_to(self.root)) for path in (self.root / "assets").glob("*/*") if str(path.relative_to(self.root).as_posix()) not in known]
        return {"interrupted_requests": len(unfinished), "orphan_assets_preserved": orphaned}

    def detail(self, inspection_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM inspections WHERE inspection_id=?", (inspection_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        for key in ("request_json","package_json","result_json"):
            raw = item.pop(key)
            item[key.removesuffix("_json")] = json.loads(raw) if raw else None
        return item

    def history(self, product=None, decision=None, since=None, until=None, limit=50):
        clauses, args = [], []
        if product:
            clauses.append("json_extract(package_json,'$.manifest.product_id')=?"); args.append(product)
        if decision:
            clauses.append("decision=?"); args.append(decision)
        if since:
            clauses.append("accepted_at>=?"); args.append(since)
        if until:
            clauses.append("accepted_at<?"); args.append(until)
        query = "SELECT inspection_id FROM inspections" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY accepted_at DESC LIMIT ?"
        with self.lock:
            ids = [row[0] for row in self.db.execute(query, (*args, min(max(int(limit), 1), 200)))]
        return [self.detail(identifier) for identifier in ids]

    def metrics(self):
        with self.lock:
            counts = dict(self.db.execute("SELECT COALESCE(decision,'PENDING'),count(*) FROM inspections GROUP BY decision"))
            return {"attempts": sum(counts.values()), "decisions": counts,
                    "cycles": self.db.execute("SELECT count(*) FROM cycles").fetchone()[0],
                    'inspection_attempts':self.db.execute("SELECT count(*) FROM inspections WHERE json_extract(request_json,'$.kind')='inspect'").fetchone()[0],
                    'reference_captures':self.db.execute("SELECT count(*) FROM inspections WHERE json_extract(request_json,'$.kind')='calibrate'").fetchone()[0],
                    "released": self.db.execute("SELECT count(*) FROM dispositions WHERE disposition='RELEASED' AND actor!='mock-operator'").fetchone()[0],
                    "mock_released": self.db.execute("SELECT count(*) FROM dispositions WHERE disposition='RELEASED' AND actor='mock-operator'").fetchone()[0]}

    def asset(self, asset_id):
        with self.lock:
            row = self.db.execute("SELECT * FROM frame_assets WHERE asset_id=?", (asset_id,)).fetchone()
        if not row:
            return None
        path = (self.root / row["relative_path"]).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Asset path escape")
        data = path.read_bytes()
        if sha256(data) != row["sha256"]:
            raise OSError("ASSET_HASH_MISMATCH")
        return dict(row), data

    def save_calibration(self, package_hash, station, payload):
        identifier = uuid.uuid4().hex
        with self.lock, self.db:
            self.db.execute("INSERT INTO calibrations VALUES (?,?,?,?,?)", (identifier,package_hash,station,canonical(payload),now()))
        return identifier

    def calibration(self, package_hash, station):
        with self.lock:
            row = self.db.execute("SELECT payload_json FROM calibrations WHERE package_sha256=? AND station_id=? ORDER BY confirmed_at DESC LIMIT 1", (package_hash,station)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        with self.lock:
            self.db.close()

    def record_terminal(self, inspection_id, disposition, actor, reason):
        if disposition not in ('RELEASED','QUARANTINED','REMOVED','ABORTED') or not actor or not reason:
            raise ValueError('INVALID_DISPOSITION')
        with self.lock, self.db:
            row=self.db.execute('SELECT * FROM inspections WHERE inspection_id=?',(inspection_id,)).fetchone()
            if not row or row['state']=='ACCEPTED':raise ConflictError('RESULT_NOT_TERMINAL')
            if disposition=='RELEASED' and row['decision']!='PASS':raise ConflictError('RELEASE_REQUIRES_PASS')
            old=self.db.execute('SELECT * FROM dispositions WHERE inspection_id=?',(inspection_id,)).fetchone()
            if old:
                if old['disposition']!=disposition or old['actor']!=actor or old['reason']!=reason:raise ConflictError('TERMINAL_PAYLOAD_CONFLICT')
                return dict(old)
            payload={'disposition_id':uuid.uuid4().hex,'inspection_id':inspection_id,'disposition':disposition,
                     'actor':actor,'reason':reason,'occurred_at':now(),'source_mode':'mock','control_mode':'mock',
                     'cell_id':row['cell_id'],'plc_session_id':row['plc_session_id'],'cycle_id':row['cycle_id']}
            self.db.execute('INSERT INTO dispositions VALUES (?,?,?,?,?,?)',tuple(payload[k] for k in ('disposition_id','inspection_id','disposition','actor','reason','occurred_at')))
            self.db.execute('UPDATE cycles SET terminal=? WHERE cell_id=? AND plc_session_id=? AND cycle_id=?',
                (disposition,row['cell_id'],row['plc_session_id'],row['cycle_id']))
            self._event('CYCLE_TERMINAL',payload)
        return payload
