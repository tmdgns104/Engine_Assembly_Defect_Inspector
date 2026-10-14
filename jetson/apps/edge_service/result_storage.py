"""One bounded durability owner; it never starts inspection or publishes results."""
import queue
import threading
import time


class ResultStorage:
    def __init__(self, journal):
        self.journal = journal
        self.jobs = queue.Queue(maxsize=1)
        self.completed = queue.Queue(maxsize=1)
        self.final_completed = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._run, name='inspection-storage', daemon=True)
        self.thread.start()

    def submit(self, context, message):
        # Caller holds service.lock and keeps active reserved until completion.
        self.jobs.put_nowait(('raw', context, message))

    def submit_final(self, context, final):
        self.jobs.put_nowait(('final', context, final))

    def _run(self):
        while not self.stop.is_set():
            try:
                kind, context, message = self.jobs.get(timeout=.05)
            except queue.Empty:
                continue
            started = time.monotonic()
            result, error = None, None
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
            self.completed.put_nowait(dict(context=context, result=result, error=error, timing=timing))

    def close(self):
        self.stop.set()
        self.thread.join(5)
        if self.thread.is_alive():
            raise RuntimeError('RESULT_STORAGE_STOP_UNCONFIRMED')
