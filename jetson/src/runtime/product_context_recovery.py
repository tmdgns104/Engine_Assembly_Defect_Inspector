"""Exceptional stopped-site context closure, not a product approval or AI exit.

Original inspection/final/abort/approval rows stay unchanged. A receipt applies
only to its hashed historical inspection. The next request still needs a fresh
PLC edge and new frames; subsequent products still need observed separation.
"""
import json
import time
import uuid
from src.runtime.aborted_recovery import canonical, digest
from src.runtime.initial_approval import count_unfinished_inspections

POLICY = 'MAINTENANCE_PRODUCT_CONTEXT_CLOSED_V1'
EVENT = 'MAINTENANCE_PRODUCT_CONTEXT_CLOSED'


def latest_product(db):
    return db.execute("""SELECT i.* FROM inspections i
        JOIN service_state s ON s.key='integrated_decision:' || i.inspection_id
        WHERE json_extract(i.request_json,'$.runtime_binding.plc_contract')='OPENER_CYCLIC'
          AND json_type(i.request_json,'$.runtime_binding.track_id') NOT IN ('null')
        ORDER BY i.rowid DESC LIMIT 1""").fetchone()


def validate_state(row, final, proof, now):
    """Read-only eligibility shared by the UI preflight and durable closure."""
    if (row['state'] != 'COMPLETE' or not row['completed_at']
            or json.loads(row['result_json']).get('storage_success') is not True
            or proof.get('inspection_id') != row['inspection_id']
            or proof.get('request_sha256') != digest(row['request_json'])
            or proof.get('result_sha256') != digest(row['result_json'])
            or proof.get('final_sha256') != digest(final)):
        raise ValueError('DURABLE_MATCHING_PRODUCT_CONTEXT_REQUIRED')
    s, owners = proof['current'], proof['owners']
    if (not all(s.get(k) is True for k in ('connected','fresh','run_idle','bool_valid'))
            or not 0 <= now-s['observed_at'] <= .5 or not 0 <= now-s['generated'] <= .5
            or not 0 <= now-s['received'] <= .2
            or s.get('phase') not in ('DISARMED','SYNC_LOW') or s.get('raw100') != '00000000'
            or s.get('controls') != dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True)
            or type(s.get('boot')) is not int or type(s.get('connection')) is not int
            or type(s.get('request_id')) is not int or not s.get('runtime_session')):
        raise ValueError('FRESH_STOPPED_NO_OUTPUT_CONTEXT_REQUIRED')
    required = dict(worker_alive=True,camera_ready=True,active_inspection_id=None,
        storage_pending=False,final_commit_pending=False,assembly_active=None,
        assembly_pending=0,assembly_outstanding=0,worker_state='IDLE')
    if (any(k not in owners or owners[k] != value for k,value in required.items())
            or owners.get('runtime_session') != s['runtime_session']):
        raise ValueError('EXPLICIT_IDLE_OWNERS_REQUIRED')


def validate(row, final, proof, now):
    validate_state(row, final, proof, now)
    if (proof.get('confirmations') != ['PHYSICAL_STOP','PRODUCT_REMOVED_OR_HELD_OFF_LINE','CLOSE_CONTEXT_WITHOUT_RESULT']
            or not isinstance(proof.get('actor'),str) or not proof['actor'].strip()
            or not isinstance(proof.get('reason'),str) or not proof['reason'].strip()):
        raise ValueError('PHYSICAL_PRODUCT_HANDLING_CONFIRMATION_REQUIRED')


def record_context_close(journal, identifier, proof, *, now=None, recheck=None):
    now = time.monotonic() if now is None else now
    journal.capacity()
    with journal.lock, journal.db:
        if journal.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise ValueError('JOURNAL_INTEGRITY_FAILED')
        if count_unfinished_inspections(journal.db):
            raise ValueError('UNFINISHED_INSPECTION_BLOCKS_CONTEXT_RECOVERY')
        row=latest_product(journal.db)
        if not row or row['inspection_id'] != identifier:
            raise ValueError('LATEST_PRODUCT_CONTEXT_REQUIRED')
        key='product_context_closed:'+identifier
        if journal.db.execute('SELECT 1 FROM service_state WHERE key=?',(key,)).fetchone():
            raise ValueError('CONTEXT_RECOVERY_ALREADY_RECORDED')
        final=journal.db.execute('SELECT value FROM service_state WHERE key=?',('integrated_decision:'+identifier,)).fetchone()[0]
        validate(row,final,proof,now)
        receipt=dict(policy=POLICY,inspection_id=identifier,proof=proof,observed_at=now,
            recovery_id=uuid.uuid4().hex,grants_created=0,result_replay_allowed=False,
            automatic_separation_claimed=False)
        event=journal._event(EVENT,receipt)
        saved=dict(receipt,event_id=event['event_id'])
        journal.db.execute('INSERT INTO service_state VALUES (?,?)',(key,canonical(saved)))
        if recheck is not None: recheck()  # Failure rolls back both new records.
    return saved


def valid_context_close(db, identifier):
    saved=db.execute('SELECT value FROM service_state WHERE key=?',('product_context_closed:'+identifier,)).fetchone()
    if not saved: return False
    try:
        receipt=json.loads(saved[0]); proof=receipt['proof']
        row=db.execute('SELECT * FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()
        names=[c[0] for c in db.execute('SELECT * FROM inspections LIMIT 0').description]
        row=dict(zip(names,row))
        final=db.execute('SELECT value FROM service_state WHERE key=?',('integrated_decision:'+identifier,)).fetchone()[0]
        validate(row,final,proof,receipt['observed_at'])
        if (receipt['policy'] != POLICY or receipt['inspection_id'] != identifier
                or receipt['grants_created'] != 0 or receipt['result_replay_allowed'] is not False
                or receipt['automatic_separation_claimed'] is not False):return False
        event=db.execute('SELECT payload_json,payload_sha256 FROM events WHERE event_id=? AND event_type=?',
            (receipt.pop('event_id'),EVENT)).fetchone()
        return bool(event and digest(event[0])==event[1] and json.loads(event[0])['payload']==receipt)
    except (ValueError,TypeError,KeyError,IndexError):return False
