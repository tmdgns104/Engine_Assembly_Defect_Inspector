"""Append-only supervised abort settlement, never a classification or a grant.

Not exposed to HTTP/admission. A stopped-site maintenance procedure supplies
fresh read-only C/owner evidence and the existing revoked approval row. Missing
evidence fails closed. Original inspections and approval ledgers are untouched.
"""
import hashlib
from copy import deepcopy
import json
import math
import time
import uuid
from datetime import datetime, timezone

POLICY = 'SUPERVISED_ABORT_WITHOUT_PLC_RESULT_V1'
CANCELLED_POLICY = 'CANCELLED_ADMISSION_WITHOUT_PLC_RESULT_V1'
CANCELLED_EVENT = 'CANCELLED_ADMISSION_ABORT_SETTLED'
CANCELLED_CONFIRMATIONS = ['PHYSICAL_STOP', 'PRODUCT_REMOVED_OR_HELD_OFF_LINE', 'ABORT_WITHOUT_RESULT']
COUNTERS = ('result_count', 'done_count', 'completed_count')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def validate_evidence(row, proof, now):
    request = json.loads(row['request_json'])
    binding = request['runtime_binding']
    result = json.loads(row['result_json'])
    if (row['state'] != 'COMPLETE' or not row['completed_at'] or result.get('storage_success') is not True
            or binding.get('plc_contract') != 'OPENER_CYCLIC'):
        raise ValueError('ABORT_REQUIRES_DURABLE_RAW_OPENER_RECORD')
    _validate_control_evidence(row, proof, now)


def _validate_control_evidence(row, proof, now, *, confirmations=None):
    """Shared actual PLC/owner proof; never change a row to satisfy validation."""
    binding = json.loads(row['request_json'])['runtime_binding']
    token = binding['plc_request_token']
    boot, connection, number = token.split(':')
    identity = (int(boot, 16), int(connection), int(number))
    failed, current, approval, owners = (proof[k] for k in ('failed', 'current', 'approval', 'owners'))
    plc_owned = proof.get('request_authority') == 'PLC_AUTOMATIC_REPEAT'
    if (type(failed.get('pid')) is not int or failed['pid'] <= 0
            or not {'active_inspection_id', 'assembly_active'}.issubset(owners)):
        raise ValueError('EXPLICIT_OWNER_AND_PROCESS_EVIDENCE_REQUIRED')
    events = failed.get('events', [])
    if (not isinstance(events, list) or not 2 <= len(events) <= 32
            or failed.get('trace_sha256') != digest(canonical(events))):
        raise ValueError('BOUNDED_ABORT_TRACE_REQUIRED')
    accepted = next((e for e in events if e.get('event') == 'REQUEST_RECEIVED'), None)
    aborted = events[-1]
    # These are adapter-lifetime counters, not counters for this request.
    # Preserve validation of old receipts. The new baseline joins the durable
    # binding to its C acceptance event; it is not a fabricated IPC packet.
    baseline = {key: 0 for key in COUNTERS}
    if proof.get('counter_evidence') == 'REQUEST_BASELINE_V1':
        snapshot = failed.get('request_snapshot', {})
        if (not plc_owned or not accepted or events[0] != accepted
                or snapshot.get('evidence_source') != 'BOUND_REQUEST_AND_C_EVENT'
                or binding.get('runtime_session_id') != failed.get('runtime_session')
                or type(binding.get('request_accepted_monotonic')) not in (int, float)
                or abs(binding['request_accepted_monotonic'] - accepted.get('monotonic_s', -1e99)) > .00001
                or any(type(snapshot.get(key)) is not int or snapshot[key] < 0 for key in COUNTERS)
                or any(accepted.get(key) != snapshot[key] for key in COUNTERS)):
            raise ValueError('REQUEST_COUNTER_BASELINE_REQUIRED')
        baseline = {key: snapshot[key] for key in COUNTERS}
    elif proof.get('counter_evidence') is not None:
        raise ValueError('UNKNOWN_ABORT_COUNTER_EVIDENCE')
    if (not accepted or aborted.get('event') != 'TRIAL_ABORTED_NO_NEW_DONE'
            or aborted.get('phase') != 'DISARMED' or aborted.get('armed') is not False
            or accepted.get('monotonic_s', 1e99) >= aborted.get('monotonic_s', 0)
            or any(e.get('connection_session') != identity[1] or e.get('trial_request_id') != identity[2]
                   or e.get('pid') != failed.get('pid')
                   or any(e.get(k) != baseline[k] for k in COUNTERS) for e in events)):
        raise ValueError('MATCHING_REQUEST_ABORT_WITHOUT_TX_REQUIRED')
    if (proof.get('inspection_id') != row['inspection_id']
            or proof.get('result_sha256') != digest(row['result_json'])
            or tuple(failed.get(k) for k in ('boot','connection','request_id')) != identity
            or failed.get('phase') != 'DISARMED' or failed.get('armed') is not False
            or (not plc_owned and failed.get('initial_revoked') is not True)
            or any(failed.get(k) != baseline[k] for k in COUNTERS)
            or failed.get('raw100') != '00000000'
            or len(failed.get('trace_sha256', '')) != 64):
        raise ValueError('NO_RESULT_AND_IRREVOCABLE_ABORT_EVIDENCE_REQUIRED')
    if plc_owned:
        accepted_snapshot = failed.get('request_snapshot', {})
        cycle = failed.get('cycle_policy', {})
        if (approval is not None or failed.get('approval_id') != ''
                or failed.get('initial_revoked') is not False or failed.get('initial_approval') is not None
                or cycle.get('policy') != 'PLC_AUTOMATIC_REPEAT' or cycle.get('software_permission_required') is not False
                or tuple(accepted_snapshot.get(k) for k in ('boot','connection','request_id')) != identity
                or accepted_snapshot.get('phase') != 'REQUEST_RECEIVED' or accepted_snapshot.get('approval_id') != ''
                or aborted.get('publication_enabled') is not False
                or current.get('boot') == identity[0]):
            raise ValueError('PLC_OWNED_ABORT_AND_NEW_ADAPTER_BOOT_REQUIRED')
    elif (not isinstance(approval, dict) or approval.get('state') != 'REVOKED' or approval.get('token') != token
            or not approval.get('id') or approval.get('id') != failed.get('approval_id')
            or approval.get('runtime') != failed.get('runtime_session')):
        raise ValueError('REVOKED_SPENT_APPROVAL_REQUIRED')
    if (not 0 <= now-current['observed_at'] <= .5 or not 0 <= now-current['generated'] <= .5
            or not 0 <= now-current['received'] <= .2
            or not all(current.get(k) is True for k in ('connected','fresh','run_idle','bool_valid'))
            or current.get('phase') != 'DISARMED' or current.get('raw100') != '00000000'
            or (current.get('boot'),current.get('connection')) == identity[:2]
            or current['controls'] != dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True)
            or any(current.get(k) != 0 for k in ('result_count','done_count','completed_count'))):
        raise ValueError('CURRENT_STOPPED_SEPARATE_CONTEXT_REQUIRED')
    # CommOpen preserves the spent request counter. Only a new adapter boot
    # resets it; a reconnect must not be mistaken for an unconsumed request.
    if current['boot'] == identity[0]:
        if current['request_id'] != identity[2] or current.get('approval_id') != approval['id']:
            raise ValueError('RECONNECTED_SPENT_REQUEST_MISMATCH')
    elif current['request_id'] != 0 or current.get('approval_id') or current.get('runtime_session') == failed['runtime_session']:
        raise ValueError('NEW_BOOT_MUST_HAVE_NEW_UNARMED_RUNTIME')
    if (owners.get('worker_state') != 'IDLE' or owners.get('worker_alive') is not True
            or owners.get('active_inspection_id') is not None or owners.get('storage_pending') is not False
            or owners.get('final_commit_pending') is not False
            or owners.get('assembly_active') is not None or owners.get('assembly_pending') != 0
            or owners.get('assembly_outstanding') != 0 or owners.get('runtime_session') != current.get('runtime_session')
            or not current.get('runtime_session')):
        raise ValueError('IDLE_CURRENT_OWNERS_REQUIRED')
    expected = confirmations or ['PHYSICAL_STOP','PRODUCT_HELD','ABORT_WITHOUT_RESULT']
    if (proof.get('confirmations') != expected
            or not proof.get('actor') or not proof.get('reason')):
        raise ValueError('SUPERVISED_RECOVERY_CONFIRMATION_REQUIRED')


def record_abort(journal, identifier, proof, *, now=None, recheck=None):
    """Maintenance only. Call after fresh evidence collection under supervision."""
    now = time.monotonic() if now is None else now
    journal.capacity()
    with journal.lock, journal.db:
        if journal.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('JOURNAL_INTEGRITY_FAILED')
        row = journal.db.execute('SELECT * FROM inspections WHERE inspection_id=?', (identifier,)).fetchone()
        if not row: raise ValueError('INSPECTION_NOT_FOUND')
        if journal.db.execute('SELECT 1 FROM service_state WHERE key IN (?,?)',
            ('integrated_decision:'+identifier, 'aborted_cycle:'+identifier)).fetchone():
            raise ValueError('FINAL_OR_ABORT_ALREADY_RECORDED')
        validate_evidence(row, proof, now)
        if proof.get('request_authority') == 'PLC_AUTOMATIC_REPEAT':
            _require_cancel_event(journal.db, identifier)
        receipt = dict(policy=POLICY, state='ABORTED', inspection_id=identifier,
            result_sha256=digest(row['result_json']), request_sha256=digest(row['request_json']),
            completed_at=row['completed_at'], proof=proof, observed_at=now,
            recorded_at=datetime.now(timezone.utc).isoformat(), recovery_id=uuid.uuid4().hex,
            grants_created=0, result_replay_allowed=False)
        event = journal._event('SUPERVISED_CYCLE_ABORTED', receipt)
        saved = dict(receipt, event_id=event['event_id'])
        journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                           ('aborted_cycle:'+identifier, canonical(saved)))
        if recheck is not None:
            recheck()  # A changed live state rolls back both appended records.
        return saved


def valid_abort(db, identifier):
    """A bare ABORTED flag is insufficient: require the matching immutable event."""
    saved = db.execute('SELECT value FROM service_state WHERE key=?', ('aborted_cycle:'+identifier,)).fetchone()
    if not saved: return False
    try:
        receipt = json.loads(saved[0])
        row = db.execute('SELECT * FROM inspections WHERE inspection_id=?', (identifier,)).fetchone()
        # Accommodate callers with or without sqlite3.Row.
        names = [c[0] for c in db.execute('SELECT * FROM inspections LIMIT 0').description]
        row = dict(zip(names, row))
        if receipt.get('policy') == CANCELLED_POLICY:
            return _valid_cancelled_abort(db, identifier, receipt, row)
        validate_evidence(row, receipt['proof'], receipt['observed_at'])
        if receipt['proof'].get('request_authority') == 'PLC_AUTOMATIC_REPEAT':
            _require_cancel_event(db, identifier)
        if (receipt['policy'] != POLICY or receipt['state'] != 'ABORTED'
                or receipt['inspection_id'] != identifier or receipt['grants_created'] != 0
                or receipt['result_replay_allowed'] is not False
                or receipt['result_sha256'] != digest(row['result_json'])
                or receipt['request_sha256'] != digest(row['request_json'])
                or receipt['completed_at'] != row['completed_at']): return False
        event = db.execute('SELECT payload_json,payload_sha256 FROM events WHERE event_id=? AND event_type=?',
                           (receipt.pop('event_id'), 'SUPERVISED_CYCLE_ABORTED')).fetchone()
        return bool(event and digest(event[0]) == event[1] and json.loads(event[0])['payload'] == receipt)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError):
        return False


def _require_cancel_event(db, identifier):
    """PLC-owned requests have no grant to revoke; require their durable cancel."""
    rows = db.execute("SELECT payload_json,payload_sha256 FROM events WHERE "
        "event_type='LINE_CANCELLED_RESULT_BLOCKED' AND "
        "json_extract(payload_json,'$.payload.inspection_id')=?", (identifier,)).fetchall()
    if not any(digest(raw) == expected and json.loads(raw)['payload'].get('reason')
               for raw, expected in rows):
        raise ValueError('DURABLE_CANCEL_EVENT_REQUIRED')


def validate_cancelled_evidence(row, proof, now):
    """A durable cancellation is not a completed inspection or classification."""
    request, result = json.loads(row['request_json']), json.loads(row['result_json'])
    binding = request.get('runtime_binding', {})
    if (row['state'] != 'CANCELLED' or row['decision'] != 'ERROR' or not row['completed_at']
            or not isinstance(result, dict) or result.get('decision') != 'ERROR'
            or result.get('storage_success') is not True or result.get('assets') != []
            or result.get('inspection_id') != row['inspection_id'] or result.get('request') != request
            or not result.get('reason') or result.get('evidence_missing_reason') != result['reason']
            or binding.get('plc_contract') != 'OPENER_CYCLIC'
            or proof.get('request_authority') != 'PLC_AUTOMATIC_REPEAT'
            or proof.get('counter_evidence') != 'REQUEST_BASELINE_V1'):
        raise ValueError('DURABLE_CANCELLED_ADMISSION_WITHOUT_IMAGES_REQUIRED')
    owners = proof.get('owners', {})
    if (owners.get('production_admission_pending') is not False
            or owners.get('request_start_pending') is not False):
        raise ValueError('IDLE_ADMISSION_AND_REQUEST_STORAGE_OWNERS_REQUIRED')
    for group in ('failed', 'current'):
        values = proof.get(group, {})
        if any(type(values.get(key)) is not int or values[key] < 0
               for key in ('boot', 'connection', 'request_id', *COUNTERS)):
            raise ValueError('EXACT_NUMERIC_C_CONTEXT_REQUIRED')
    current = proof['current']
    if any(type(current.get(key)) not in (int, float)
           or not math.isfinite(current[key]) or current[key] < 0
           for key in ('observed_at', 'generated', 'received')):
        raise ValueError('FINITE_CURRENT_OBSERVATION_TIMES_REQUIRED')
    for event in proof['failed'].get('events', []):
        stamp = event.get('monotonic_s')
        if (type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0
                or any(type(event.get(key)) is not int or event[key] < 0 for key in COUNTERS)):
            raise ValueError('EXACT_NUMERIC_C_TRACE_REQUIRED')
    _validate_control_evidence(row, proof, now, confirmations=CANCELLED_CONFIRMATIONS)


def _cancelled_events(db, row):
    identifier = row['inspection_id']
    if db.execute('SELECT 1 FROM frame_assets WHERE inspection_id=? LIMIT 1', (identifier,)).fetchone():
        raise ValueError('CANCELLED_ADMISSION_HAS_IMAGE_ASSETS')
    if db.execute('SELECT 1 FROM service_state WHERE key=?', ('integrated_decision:'+identifier,)).fetchone():
        raise ValueError('CANCELLED_ADMISSION_HAS_INTEGRATED_FINAL')
    prohibited = ('INSPECTION_COMPLETED', 'INTEGRATED_FINAL_DURABLE',
                  'INTEGRATED_INSPECTION_COMPLETED', 'PLC_CYCLIC_COMPLETION_OBSERVED')
    rows = db.execute("SELECT event_id,event_type,payload_json,payload_sha256 FROM events "
        "WHERE json_extract(payload_json,'$.payload.inspection_id')=? ORDER BY rowid LIMIT 129",
        (identifier,)).fetchall()
    if len(rows) > 128:
        raise ValueError('CANCELLED_ADMISSION_EVENT_BOUND_EXCEEDED')
    result = json.loads(row['result_json'])
    binding = json.loads(row['request_json'])['runtime_binding']
    selected = {}
    for event_id, kind, raw, expected in rows:
        if kind in prohibited:
            raise ValueError('CANCELLED_ADMISSION_COMPLETION_OR_PUBLICATION_EXISTS')
        if kind not in ('INSPECTION_CANCELLED', 'LINE_CANCELLED_RESULT_BLOCKED'):
            continue
        if digest(raw) != expected:
            raise ValueError('CANCELLED_ADMISSION_EVENT_HASH_MISMATCH')
        event = json.loads(raw)
        payload = event['payload']
        if event.get('event_id') != event_id or event.get('event_type') != kind:
            raise ValueError('CANCELLED_ADMISSION_EVENT_IDENTITY_MISMATCH')
        if kind == 'INSPECTION_CANCELLED' and payload != result:
            raise ValueError('CANCELLED_ADMISSION_RESULT_EVENT_MISMATCH')
        if kind == 'LINE_CANCELLED_RESULT_BLOCKED' and (
                not payload.get('reason') or payload.get('physical_output_enabled') is not False
                or payload.get('runtime_session_id') != binding.get('runtime_session_id')
                or payload.get('request_token', binding['plc_request_token']) != binding['plc_request_token']):
            raise ValueError('CANCELLED_ADMISSION_BLOCK_EVENT_MISMATCH')
        selected.setdefault(kind, dict(event_id=event_id, sha256=expected))
    if len(selected) != 2:
        raise ValueError('DURABLE_CANCELLATION_AND_BLOCK_EVENTS_REQUIRED')
    publication = db.execute('SELECT value FROM service_state WHERE key=?',
                             ('production_publication:'+identifier,)).fetchone()
    if publication:
        value = json.loads(publication[0])
        if (value.get('event') in prohibited
                or value.get('publication_status') in ('IPC_QUEUED','CYCLIC_DONE_RESET_SENT')):
            raise ValueError('CANCELLED_ADMISSION_PUBLICATION_EXISTS')
    return selected


def validate_cancelled_record(db, row, proof, now):
    """Read-only maintenance preflight, also used by the append transaction."""
    validate_cancelled_evidence(row, proof, now)
    return _cancelled_events(db, row)


def record_cancelled_abort(journal, identifier, proof, *, now=None, recheck=None):
    """Append an exact stopped-site cancellation settlement, without any output.

    Recheck returns True for the legacy frozen-proof path, or a refreshed proof
    for slow historical validation. A refreshed proof may change only live
    timestamps and idle-owner observations, never request/control identity.
    """
    if not callable(recheck):
        raise ValueError('FRESH_MAINTENANCE_RECHECK_REQUIRED')
    proof = deepcopy(proof)
    started = time.monotonic()
    observed = started if now is None else now
    journal.capacity()
    with journal.lock, journal.db:
        # Keep history stable while it is checked. The live read comes last,
        # so a large journal cannot age the PLC evidence before the write.
        journal.db.execute('BEGIN IMMEDIATE')
        row = journal.db.execute('SELECT * FROM inspections WHERE inspection_id=?', (identifier,)).fetchone()
        if not row:
            raise ValueError('INSPECTION_NOT_FOUND')
        validate_cancelled_evidence(row, proof, observed)
        if journal.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('JOURNAL_INTEGRITY_FAILED')
        if journal.db.execute('SELECT 1 FROM service_state WHERE key IN (?,?)',
                ('integrated_decision:'+identifier, 'aborted_cycle:'+identifier)).fetchone():
            raise ValueError('FINAL_OR_ABORT_ALREADY_RECORDED')
        evidence = _cancelled_events(journal.db, row)
        changes = journal.db.total_changes
        refreshed = recheck()
        if journal.db.total_changes != changes:
            raise ValueError('CANCELLED_ADMISSION_CHANGED_DURING_RECOVERY')
        if isinstance(refreshed, dict):
            historical = lambda value: {k:v for k,v in value.items() if k not in ('current','owners')}
            fixed_current = lambda value: {k:v for k,v in value['current'].items()
                if k not in ('observed_at','generated','received')}
            if historical(refreshed) != historical(proof) or fixed_current(refreshed) != fixed_current(proof):
                raise ValueError('MAINTENANCE_REFRESH_IDENTITY_CHANGED')
            proof = deepcopy(refreshed)
        elif refreshed is not True:
            raise ValueError('FRESH_MAINTENANCE_RECHECK_REQUIRED')
        committed_observation = observed + time.monotonic() - started
        validate_cancelled_evidence(row, proof, committed_observation)
        receipt = dict(policy=CANCELLED_POLICY, state='ABORTED', inspection_id=identifier,
            result_sha256=digest(row['result_json']), request_sha256=digest(row['request_json']),
            completed_at=row['completed_at'], proof=proof, cancel_evidence=evidence,
            observed_at=committed_observation, recorded_at=datetime.now(timezone.utc).isoformat(),
            recovery_id=uuid.uuid4().hex, grants_created=0, result_replay_allowed=False,
            classification_created=False)
        event = journal._event(CANCELLED_EVENT, receipt)
        saved = dict(receipt, event_id=event['event_id'])
        journal.db.execute('INSERT INTO service_state VALUES (?,?)',
                           ('aborted_cycle:'+identifier, canonical(saved)))
        validate_cancelled_evidence(row, proof, observed+time.monotonic()-started)
        return saved


def _valid_cancelled_abort(db, identifier, receipt, row):
    validate_cancelled_evidence(row, receipt['proof'], receipt['observed_at'])
    if (receipt.get('state') != 'ABORTED' or receipt.get('inspection_id') != identifier
            or receipt.get('grants_created') != 0 or receipt.get('result_replay_allowed') is not False
            or receipt.get('classification_created') is not False
            or receipt.get('result_sha256') != digest(row['result_json'])
            or receipt.get('request_sha256') != digest(row['request_json'])
            or receipt.get('completed_at') != row['completed_at']
            or receipt.get('cancel_evidence') != _cancelled_events(db, row)):
        return False
    event = db.execute('SELECT payload_json,payload_sha256 FROM events WHERE event_id=? AND event_type=?',
                       (receipt.pop('event_id'), CANCELLED_EVENT)).fetchone()
    return bool(event and digest(event[0]) == event[1] and json.loads(event[0])['payload'] == receipt)
