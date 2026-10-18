"""Durable request-start work owned by the existing storage thread.

These jobs return detached evidence to the control owner. They never acquire a
Service/Runtime lock, dispatch a camera request, or publish a PLC result.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import time

from src.journal.sqlite import ConflictError
from src.runtime.initial_approval import count_unfinished_inspections


KINDS = frozenset(('events', 'admit', 'readiness', 'cancel', 'no_input', 'finish_no_input'))


class RequestJobError(RuntimeError):
    """Preserve an admission identity if a later evidence read fails."""
    def __init__(self, error, result):
        super().__init__(type(error).__name__ + ':' + str(error))
        self.result = result


def validate_job(job):
    if not isinstance(job, dict) or job.get('kind') not in KINDS:
        raise ValueError('UNKNOWN_REQUEST_STORAGE_JOB')


def _check_integrity(journal, timings):
    """Keep the original admission integrity gate on the storage owner."""
    started = time.monotonic()
    try:
        row = journal.db.execute('PRAGMA quick_check').fetchone()
        if not row or row[0] != 'ok':
            raise ValueError('JOURNAL_INTEGRITY_FAILED')
    finally:
        timings['integrity_check_ms'] = (time.monotonic() - started) * 1000


@contextmanager
def transaction(journal, timings, stage):
    started = time.monotonic()
    with journal.lock:
        acquired = time.monotonic()
        timings[stage + '_lock_wait_ms'] = (acquired - started) * 1000
        commit_started = None
        try:
            with journal.db:
                yield
                commit_started = time.monotonic()
            timings[stage + '_commit_ms'] = (time.monotonic() - commit_started) * 1000
        finally:
            timings[stage + '_transaction_ms'] = (time.monotonic() - acquired) * 1000


def _events(journal, job, timings):
    payloads = job['events']
    if (not isinstance(payloads, list) or not payloads or len(payloads) > 64
            or any(not isinstance(p, dict) or not isinstance(p.get('event'), str)
                   or not p['event'] for p in payloads)):
        raise ValueError('INVALID_REQUEST_EVENT_BATCH')
    with transaction(journal, timings, 'events'):
        for payload in payloads:
            journal._event(payload['event'], payload)
            if payload.get('inspection_id') is not None and payload.get('event_only') is not True:
                identifier = payload['inspection_id']
                if not isinstance(identifier, str) or not identifier:
                    raise ValueError('INVALID_EVENT_INSPECTION_ID')
                journal.db.execute(
                    'INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    ('production_publication:' + identifier, json.dumps(payload)))
    return {'event_count': len(payloads)}


def _admit(journal, job, timings):
    request = deepcopy(job['base'])
    if any(key in request for key in ('request_id', 'cycle_id', 'attempt')):
        raise ValueError('REQUEST_IDS_MUST_BE_ALLOCATED_BY_STORAGE')
    session = request.get('plc_session_id')
    if (type(session) is not int or not 1 <= session <= 4294967295
            or not isinstance(request.get('cell_id'), str)
            or not request['cell_id'].strip() or len(request['cell_id']) > 100):
        raise ValueError('INVALID_REQUEST_NAMESPACE')
    trigger = deepcopy(job.get('trigger'))
    events = job.get('events', [])
    if not isinstance(events, list):
        raise ValueError('INVALID_REQUEST_EVENT_BATCH')
    started = time.monotonic()
    with journal.lock:
        timings['admission_lock_wait_ms'] = (time.monotonic() - started) * 1000
        _check_integrity(journal, timings)
        if count_unfinished_inspections(journal.db):
            raise ConflictError('JOURNAL_UNFINISHED_INSPECTION')
        unresolved = journal.db.execute("""
            SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id)
            WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'
        """).fetchone()[0]
        if unresolved:
            raise ConflictError('UNFINISHED_CYCLE_RECOVERY_REQUIRED')
        # The control owner supplies this batch once. Its durable ordering is
        # retained before counter allocation/admission; failed jobs are never
        # retried here, since a later transaction may already have committed.
        if events:
            _events(journal, dict(events=events), timings)
        # Keep the existing durable counter semantics: a failed later admit
        # never makes a spent ID reusable, including after process restart.
        with transaction(journal, timings, 'counter'):
            key = 'request_counter:' + str(session)
            row = journal.db.execute('SELECT value FROM service_state WHERE key=?', (key,)).fetchone()
            number = int(row[0]) + 1 if row else 1
            if number > 4294967295:
                raise ConflictError('REQUEST_COUNTER_EXHAUSTED_RESTART_SESSION_REQUIRED')
            journal.db.execute(
                'INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                (key, str(number)))
        request.update(request_id=number, cycle_id=number, attempt=1)
        if trigger is not None:
            trigger.update({key: request[key] for key in
                            ('cell_id', 'plc_session_id', 'request_id', 'cycle_id')})
        admit_started = time.monotonic()
        try:
            identifier, created = journal.admit(request, job['package'], trigger=trigger)
        finally:
            timings['admit_including_commit_ms'] = (time.monotonic() - admit_started) * 1000
        result = dict(request=request, trigger=trigger, inspection_id=identifier,
                      row=None, created=created)
        try:
            result['row'] = journal.detail(identifier)
            if result['row'] is None:
                raise ValueError('ADMITTED_REQUEST_EVIDENCE_MISSING')
        except Exception as error:
            raise RequestJobError(error, result) from error
    return result


def _readiness(journal, job, timings):
    started = time.monotonic()
    with journal.lock:
        timings['readiness_lock_wait_ms'] = (time.monotonic() - started) * 1000
        _check_integrity(journal, timings)
        journal.capacity()
        unfinished = count_unfinished_inspections(journal.db)
        identifier = job.get('previous_identifier')
        row = journal.detail(identifier) if identifier else None
        saved = (journal.db.execute('SELECT value FROM service_state WHERE key=?',
                 ('integrated_decision:' + identifier,)).fetchone() if identifier else None)
        final = json.loads(saved[0]) if saved else None
        version = (journal.db.total_changes, journal.db.execute('PRAGMA data_version').fetchone()[0])
    return dict(unfinished=unfinished, previous_row=row, previous_final=final,
                previous_identifier=identifier, previous_token=job.get('previous_token'),
                journal_version=version)


def _cancel(journal, job, timings):
    identifier = job['inspection_id']
    reason = job['reason']
    if not isinstance(identifier, str) or not identifier or not isinstance(reason, str) or not reason:
        raise ValueError('INVALID_REQUEST_CANCELLATION')
    started = time.monotonic()
    with journal.lock:
        timings['cancel_lock_wait_ms'] = (time.monotonic() - started) * 1000
        if journal.detail(identifier) is None:
            raise ValueError('CANCEL_INSPECTION_NOT_FOUND')
        journal.cancel(identifier, reason)
        row = journal.detail(identifier)
        final = journal.db.execute('SELECT 1 FROM service_state WHERE key=?',
            ('integrated_decision:'+identifier,)).fetchone()
        if row['state'] in ('CANCELLED', 'COMPLETE') and not final:
            # An admission cancelled before camera dispatch has no bridge yet.
            # A no-input ERROR may also finish after STOP. Preserve that result
            # while recording that publication was blocked; a reboot must not
            # silently forget either kind of unresolved request.
            binding = row['request'].get('runtime_binding', {})
            with journal.db:
                journal._event('LINE_CANCELLED_RESULT_BLOCKED', dict(
                    inspection_id=identifier, reason=reason,
                    runtime_session_id=binding.get('runtime_session_id'),
                    request_token=binding.get('plc_request_token'),
                    stage='REQUEST_ADMISSION', physical_output_enabled=False))
    return dict(inspection_id=identifier, row=row)


def _no_input(journal, job, timings):
    final = deepcopy(job['no_input_result'])
    if not isinstance(final, dict) or final.get('decision') != 'ERROR' or job.get('trigger') is not None:
        raise ValueError('NO_INPUT_REQUIRES_ERROR_WITHOUT_CAPTURE_TRIGGER')
    result = _admit(journal, job, timings)
    identifier = result['inspection_id']
    if isinstance(final.get('production_identity'), dict):
        final['production_identity']['inspection_id'] = identifier
    started = time.monotonic()
    try:
        if not result['created']:
            raise ValueError('DUPLICATE_NO_INPUT_ADMISSION')
        result['finished_result'] = journal.finish(identifier, final, ())
        result['row'] = journal.detail(identifier)
        if result['finished_result'] is None or result['row'] is None:
            raise ValueError('NO_INPUT_DURABILITY_EVIDENCE_MISSING')
    except Exception as error:
        raise RequestJobError(error, result) from error
    finally:
        timings['no_input_finish_including_commit_ms'] = (time.monotonic() - started) * 1000
    return result


def _finish_no_input(journal, job, timings):
    """Finish the original admission, never allocate or revive a request."""
    identifier = job['inspection_id']
    final = deepcopy(job['no_input_result'])
    request = job['request']
    binding = request.get('runtime_binding', {})
    if (not isinstance(identifier, str) or not identifier
            or final.get('decision') != 'ERROR' or final.get('observations') != []
            or final.get('assets') != [] or final.get('execution', {}).get('source') != 'not_executed'
            or final.get('production_identity') != dict(binding, inspection_id=identifier)):
        raise ValueError('INVALID_UNEXECUTED_COMPLETION')
    result = dict(inspection_id=identifier, request=deepcopy(request))
    started = time.monotonic()
    try:
        row = journal.detail(identifier)
        if (not row or row['request'] != request or row['package'] != job['package']
                or row['state'] != 'ACCEPTED'):
            raise ValueError('UNEXECUTED_COMPLETION_OWNER_CHANGED_OR_TERMINAL')
        result['finished_result'] = journal.finish(identifier, final, ())
        result['row'] = journal.detail(identifier)
        if (result['finished_result'] is None or not result['row']
                or result['row']['state'] != 'COMPLETE'
                or not result['finished_result'].get('storage_success')):
            raise ValueError('UNEXECUTED_COMPLETION_NOT_DURABLE')
    except Exception as error:
        raise RequestJobError(error, result) from error
    finally:
        timings['unexecuted_finish_including_commit_ms'] = (time.monotonic() - started) * 1000
    return result


def execute_request_job(journal, job, timings):
    validate_job(job)
    started = time.monotonic()
    try:
        return {'events': _events, 'admit': _admit,
                'readiness': _readiness, 'cancel': _cancel,
                'no_input': _no_input, 'finish_no_input': _finish_no_input}[job['kind']](journal, job, timings)
    finally:
        timings[job['kind'] + '_total_ms'] = (time.monotonic() - started) * 1000
