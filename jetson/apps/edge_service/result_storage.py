"""One bounded durability owner; it never starts inspection or publishes results."""
import queue
import json
import threading
import time
from copy import deepcopy

from src.journal.request_start import execute_request_job, validate_job
from src.camera.fresh_frame import finite_number


def raw_storage_within_deadline(context):
    """A queued durable receipt is judged at completion, not monitor polling.

    Only this Writer supplies durable_monotonic, after all mandatory writes.
    A missing receipt still uses current time so a hung Writer cannot renew it.
    """
    completed = context.get('durable_monotonic')
    # Snapshot the Writer receipt before reading the clock; otherwise a receipt
    # published between the reads can look spuriously future-dated.
    now = time.monotonic()
    stamp = now if completed is None else completed
    return (finite_number(stamp) and finite_number(now) and 0 <= stamp <= now
            and stamp < context['active']['deadline'])


class ResultStorage:
    def __init__(self, journal):
        self.journal = journal
        self.jobs = queue.Queue(maxsize=1)
        self.completed = queue.Queue(maxsize=1)
        self.final_completed = queue.Queue(maxsize=1)
        self.audit_completed = queue.Queue(maxsize=1)
        self.request_completed = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name='inspection-storage', daemon=True)
        self.thread.start()

    def submit(self, context, message):
        # Caller holds service.lock and keeps active reserved until completion.
        self.jobs.put_nowait(('raw', context, message))

    def submit_final(self, context, final):
        self.jobs.put_nowait(('final', context, final))

    def submit_audit(self, context, payload):
        # Runtime reserves the next admission until this exact job completes.
        self.jobs.put_nowait(('audit', context, payload))

    def submit_request(self, context, job):
        """Reserve one typed durability job; context identity belongs to caller."""
        validate_job(job)
        self.jobs.put_nowait(('request', context, deepcopy(job)))

    def _run(self):
        while not self.stop.is_set() or not self.jobs.empty():
            try:
                kind, context, message = self.jobs.get(timeout=.05)
            except queue.Empty:
                continue
            started = time.monotonic()
            result, error = None, None
            if kind == 'request' or kind not in ('raw', 'final', 'audit'):
                timings = {}
                try:
                    if kind != 'request':
                        raise ValueError('UNKNOWN_STORAGE_JOB_KIND:' + str(kind))
                    result = execute_request_job(self.journal, message, timings)
                except Exception as exc:
                    result = getattr(exc, 'result', None)
                    error = type(exc).__name__ + ':' + str(exc)
                finished = time.monotonic()
                self.request_completed.put_nowait(dict(context=context, result=result,
                    error=error, durable_monotonic=finished if error is None else None,
                    duration_ms=(finished-started)*1000, timings=timings))
                continue
            if kind == 'audit':
                try:
                    with self.journal.lock, self.journal.db:
                        self.journal._event(message['event'], message)
                        self.journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            ('production_publication:'+context['inspection_id'], json.dumps(message)))
                except Exception as exc:
                    error = type(exc).__name__+':'+str(exc)
                self.audit_completed.put_nowait(dict(context=context, error=error,
                    duration_ms=(time.monotonic()-started)*1000))
                continue
            if kind == 'final':
                try:
                    self.journal.commit_integrated(message)
                except Exception as exc:
                    error = type(exc).__name__+':'+str(exc)
                self.final_completed.put_nowait(dict(context=context, final=message, error=error))
                continue
            try:
                result = self.journal.finish(message['inspection_id'], message['result'], message['images'])
                elapsed = (time.monotonic()-context['active']['accepted_monotonic'])*1000
                timing = dict(inspection_id=message['inspection_id'], request_to_durable_result_ms=elapsed,
                              storage_commit_ms=(time.monotonic()-started)*1000, clock='edge_monotonic',
                              source_mode=message['result']['execution']['source'])
                binding = context['active'].get('production_binding') or {}
                motion = binding.get('inspection_motion_mode')
                if motion in ('CONVEYOR_MOTION_DEV', 'CONVEYOR_MOTION_PLC_BENCH'):
                    field = ('mock_request_to_durable_result_ms' if motion == 'CONVEYOR_MOTION_DEV'
                             else 'plc_request_to_durable_result_ms')
                    timing[field] = (time.monotonic()-binding['request_accepted_monotonic'])*1000
                with self.journal.lock, self.journal.db:
                    self.journal._event('INSPECTION_DURABLE_TIMING', timing)
            except Exception as exc:
                error = type(exc).__name__+':'+str(exc)
                timing = dict(inspection_id=message['inspection_id'], storage_commit_ms=(time.monotonic()-started)*1000)
            if error is None:
                context['durable_monotonic'] = time.monotonic()
            self.completed.put_nowait(dict(context=context, result=result, error=error, timing=timing))

    def close(self):
        self.stop.set()
        self.thread.join(5)
        if self.thread.is_alive():
            raise RuntimeError('RESULT_STORAGE_STOP_UNCONFIRMED')
