"""Append-only supervised abort settlement, never a classification or a grant.

Not exposed to HTTP/admission. A stopped-site maintenance procedure supplies
fresh read-only C/owner evidence and the existing revoked approval row. Missing
evidence fails closed. Original inspections and approval ledgers are untouched.
"""
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

POLICY = 'SUPERVISED_ABORT_WITHOUT_PLC_RESULT_V1'


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
    if (not accepted or aborted.get('event') != 'TRIAL_ABORTED_NO_NEW_DONE'
            or aborted.get('phase') != 'DISARMED' or aborted.get('armed') is not False
            or accepted.get('monotonic_s', 1e99) >= aborted.get('monotonic_s', 0)
            or any(e.get('connection_session') != identity[1] or e.get('trial_request_id') != identity[2]
                   or e.get('pid') != failed.get('pid')
                   or any(e.get(k) != 0 for k in ('result_count','done_count','completed_count')) for e in events)):
        raise ValueError('MATCHING_REQUEST_ABORT_WITHOUT_TX_REQUIRED')
    if (proof.get('inspection_id') != row['inspection_id']
            or proof.get('result_sha256') != digest(row['result_json'])
            or tuple(failed.get(k) for k in ('boot','connection','request_id')) != identity
            or failed.get('phase') != 'DISARMED' or failed.get('armed') is not False
            or (not plc_owned and failed.get('initial_revoked') is not True)
            or any(failed.get(k) != 0 for k in ('result_count','done_count','completed_count'))
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
    if (proof.get('confirmations') != ['PHYSICAL_STOP','PRODUCT_HELD','ABORT_WITHOUT_RESULT']
            or not proof.get('actor') or not proof.get('reason')):
        raise ValueError('SUPERVISED_RECOVERY_CONFIRMATION_REQUIRED')


def record_abort(journal, identifier, proof, *, now=None):
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
    except (ValueError, KeyError, TypeError):
        return False


def _require_cancel_event(db, identifier):
    """PLC-owned requests have no grant to revoke; require their durable cancel."""
    rows = db.execute("SELECT payload_json,payload_sha256 FROM events WHERE "
        "event_type='LINE_CANCELLED_RESULT_BLOCKED' AND "
        "json_extract(payload_json,'$.payload.inspection_id')=?", (identifier,)).fetchall()
    if not any(digest(raw) == expected and json.loads(raw)['payload'].get('reason')
               for raw, expected in rows):
        raise ValueError('DURABLE_CANCEL_EVENT_REQUIRED')
