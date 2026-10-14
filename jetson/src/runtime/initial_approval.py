"""Durable, explicit one-product commissioning permission, never area CLEAR.

Only the running Runtime consumes requests. The operator CLI writes a request
bound to a live challenge. A reserved ID is permanently spent even if a crash
prevents C receipt. There is deliberately no restore/retry of stored grants.
"""
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid

POLICY = 'EXPLICIT_ONE_SHOT_V1'

# These pre-integration requests completed in the original inspector. New
# Runtime requests persist plc_contract in runtime_binding before admission.
LEGACY_AUTHORITIES = frozenset((
    'WHOLE_PRODUCT_TRACK_AND_LATCHED_MOCK_REQUEST',
    'WHOLE_PRODUCT_TRACK_AND_LATCHED_PLC_REQUEST',
))


def legacy_terminal_identity(identifier, request, identity):
    """Recognize the old contract positively; absence of a final alone is not proof."""
    if not isinstance(request, dict):
        return False
    binding = request.get('runtime_binding')
    if not isinstance(binding, dict) or not isinstance(identity, dict):
        return False
    integrated_markers = ('plc_contract', 'line_cycle_id', 'line_session_id',
                          'inspection_start_policy', 'integrated_decision_required')
    if any(key in value for value in (request, binding, identity) for key in integrated_markers):
        return False
    return bool(binding.get('authority') in LEGACY_AUTHORITIES
        and identity.get('inspection_id') == identifier
        and all(binding.get(key) and identity.get(key) == binding[key]
                for key in ('authority', 'runtime_session_id', 'plc_request_token')))


def count_unfinished_inspections(db):
    """Read-only admission check; never migrate history or create final decisions.

    ACCEPTED always blocks. A production COMPLETE record still needs durable
    completion and either its integrated final or a recognized legacy identity.
    Unknown contracts fail closed; no date cutoff or per-record exemption file.
    Project only small fields from large result JSON (never load image metadata).
    """
    rows = db.execute("""
        SELECT i.inspection_id, i.state, i.request_json, i.completed_at,
               json_extract(i.result_json, '$.storage_success'),
               json_extract(i.result_json, '$.production_identity'),
               EXISTS(SELECT 1 FROM service_state s
                      WHERE s.key = 'integrated_decision:' || i.inspection_id)
        FROM inspections i
        WHERE i.state = 'ACCEPTED' OR (i.state = 'COMPLETE' AND (
            json_extract(i.request_json, '$.control_mode') = 'production' OR
            json_type(i.request_json, '$.runtime_binding.plc_contract') IS NOT NULL))
        """)
    blockers = 0
    for identifier, state, raw_request, completed, stored, raw_identity, has_final in rows:
        if state == 'ACCEPTED' or not completed or stored != 1:
            blockers += 1
        elif not has_final and not legacy_terminal_identity(
                identifier, json.loads(raw_request), json.loads(raw_identity or 'null')):
            from src.runtime.aborted_recovery import valid_abort
            if not valid_abort(db, identifier):
                blockers += 1
    return blockers


class JournalAdmissionGuard:
    """Recheck on either connection's writes and on every operator submission."""
    def __init__(self):
        self.key = None
        self.blockers = None

    def count(self, db, *, fresh=False):
        key = (db, db.total_changes, db.execute('PRAGMA data_version').fetchone()[0])
        if fresh or key != self.key:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('JOURNAL_INTEGRITY_FAILED')
            self.blockers = count_unfinished_inspections(db)
            self.key = key
        return self.blockers

def atomic_json(path, value):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()

def stopped_snapshot(s, now):
    return bool(s and s['connected'] and s['fresh'] and s['run_idle'] and s['bool_valid']
        and 0 <= now-s['generated'] <= .5 and 0 <= now-s['received'] <= .2
        and not s['controls']['Inspection_Request'] and not s['controls']['Mc_Run']
        and s['controls']['EStop_OK'] and s['controls']['Stop_PB']
        and s['raw100'] == '00000000' and s['request_id'] == 0
        and s['phase'] in ('DISARMED', 'SYNC_LOW'))

class InitialApproval:
    def __init__(self, root, runtime_session):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.root.lstat()
        if not stat.S_ISDIR(info.st_mode) or self.root.is_symlink():
            raise ValueError('APPROVAL_DIRECTORY_INVALID')
        if os.name != 'nt' and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise ValueError('PRIVATE_APPROVAL_DIRECTORY_REQUIRED')
        self.session = runtime_session
        self.approval_id = None
        self.binding = None
        self.token = None
        self.state = 'INITIAL_DISARMED'
        self.reason = 'EXPLICIT_OPERATOR_APPROVAL_REQUIRED'
        self.expires = 0
        self.arm_deadline = 0
        self.failed = False
        self.context_loss = None
        self.challenge_at = -1e30
        self.challenge_identity = None
        self.journal_gate = JournalAdmissionGuard()
        # Existing corrupt/unknown storage raises: it is never replaced.
        self.db = sqlite3.connect(self.root/'approvals.sqlite3', check_same_thread=False)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, runtime TEXT NOT NULL, binding TEXT NOT NULL, state TEXT NOT NULL, token TEXT, reason TEXT)')
        self.db.commit()
        if self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('APPROVAL_LEDGER_INVALID')

    def _record(self, state, reason, token=None):
        if self.state == state and self.reason == reason and self.token == token:
            return
        with self.db:
            changed = self.db.execute('UPDATE approvals SET state=?,reason=?,token=? WHERE id=? AND runtime=?',
                (state,reason,token,self.approval_id,self.session)).rowcount
            if changed != 1: raise ValueError('APPROVAL_RECORD_MISSING')
        self.state, self.reason = state, reason

    def revoke(self, reason):
        if self.approval_id and self.state != 'REVOKED':
            self._record('REVOKED', reason, self.token)
        self.reason = reason

    def poll(self, snapshot, ready, epoch, generation, now, gateway, journal):
        """Called only on the Runtime owner. Storage failure disarms publication."""
        try:
            binding = dict(runtime=self.session, boot=snapshot['boot'], connection=snapshot['connection'],
                epoch=epoch, generation=generation) if snapshot else None
            if self.approval_id:
                if (not ready or binding != self.binding or not snapshot or not snapshot['fresh']
                        or not snapshot['connected'] or not snapshot['run_idle'] or not snapshot['bool_valid']):
                    self.context_loss = dict(ready=bool(ready), expected=self.binding, actual=binding,
                        snapshot_state={k:snapshot.get(k) for k in ('fresh','connected','run_idle','bool_valid','phase')}
                        if snapshot else None)
                    self.revoke('APPROVAL_CONTEXT_OR_READINESS_LOST')
                    gateway.cancel()
                elif self.state != 'REVOKED':
                    if (not self.token and now > self.arm_deadline
                            and snapshot.get('approval_id') != self.approval_id):
                        self.revoke('INITIAL_GRANT_NOT_ACKNOWLEDGED')
                        gateway.cancel()
                    elif snapshot['phase'] == 'DISARMED' and snapshot.get('approval_id') == self.approval_id:
                        self.revoke('ADAPTER_DISARMED')
                        gateway.cancel()
                    elif snapshot['phase'] == 'READY_NEXT':
                        self._record('FIRST_CYCLE_COMPLETE', 'WAIT_VERIFIED_CLEARANCE', self.token)
                    elif not self.token and now > self.expires:
                        self.revoke('INITIAL_APPROVAL_EXPIRED')
                        gateway.cancel()
                return
            with journal.lock:
                unfinished = self.journal_gate.count(journal.db,
                    fresh=(self.root/'request.json').exists())
                journal.capacity()
            eligible = bool(not self.failed and ready and epoch is not None and generation is not None
                and not unfinished and stopped_snapshot(snapshot, now))
            challenge = dict(binding=binding, generated=now, eligible=eligible,
                policy=POLICY, reason='READY_FOR_OPERATOR_APPROVAL' if eligible else 'WAIT_READY_STOPPED_CLEAN_STATE')
            if now-self.challenge_at >= .5 or self.challenge_identity != (binding, eligible):
                atomic_json(self.root/'challenge.json', challenge)
                self.challenge_at = now
                self.challenge_identity = (binding, eligible)
            request_path = self.root/'request.json'
            if not request_path.exists(): return
            if request_path.is_symlink() or request_path.stat().st_size > 4096:
                raise ValueError('APPROVAL_REQUEST_FILE_INVALID')
            request = json.loads(request_path.read_text(encoding='utf-8'))
            # A rejected request is not queued for a later favorable PLC state.
            request_path.unlink()
            identifier = request.get('approval_id', '')
            if (not eligible or request.get('binding') != binding or request.get('policy') != POLICY
                    or not 0 <= now-request.get('created', -999) <= 5
                    or request.get('confirmations') != ['PHYSICAL_STOP','SUPERVISED','NO_UNFINISHED_PRODUCT','REAL_AI_OUTPUT']
                    or len(identifier) != 32 or any(c not in '0123456789abcdef' for c in identifier)):
                raise ValueError('APPROVAL_NOT_CURRENT_OR_NOT_EXPLICIT')
            with self.db:
                self.db.execute('INSERT INTO approvals VALUES (?,?,?,?,?,?)',
                    (identifier,self.session,json.dumps(binding,sort_keys=True),'RESERVED',None,'RESERVED_BEFORE_IPC'))
            self.approval_id, self.binding = identifier, binding
            self.state, self.reason = 'RESERVED', 'WAIT_NEW_START_AND_REQUEST'
            self.expires = now + 120
            self.arm_deadline = now + 2
            # Reserve before touching IPC. Failure is intentionally not retryable.
            gateway.initial_arm(snapshot, identifier)
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError) as error:
            self.failed = True
            self.reason = 'INITIAL_APPROVAL_FAILED:' + type(error).__name__
            gateway.cancel()
            if self.approval_id:
                try: self.revoke(self.reason)
                except (OSError, sqlite3.Error, ValueError): self.state = 'STORAGE_UNCERTAIN'

    def accept(self, snapshot, token):
        if (self.failed or self.state != 'RESERVED' or self.token or not self.approval_id
                or snapshot.get('approval_id') != self.approval_id
                or snapshot['boot'] != self.binding['boot']
                or snapshot['connection'] != self.binding['connection']):
            raise ValueError('FIRST_PRODUCT_PERMISSION_MISMATCH_OR_SPENT')
        self._record('ACCEPTED', 'ONE_REQUEST_BUDGET_CONSUMED', token)
        self.token = token

    def valid(self):
        return self.approval_id is not None and not self.failed and self.state in ('RESERVED','ACCEPTED')

    def status(self):
        return dict(policy=POLICY,state=self.state,reason=self.reason,approval_id=self.approval_id,
            context_loss=self.context_loss,
            request_token=self.token, automatic_rearm=False, restored_from_disk=False,
            physical_stop_feedback='NOT_AVAILABLE_OPERATOR_CONFIRMATION_REQUIRED')

    def close(self):
        self.db.close()
