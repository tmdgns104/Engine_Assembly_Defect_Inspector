"""Service-side capture control and exact consumed-packet trace, no camera access."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import uuid
import queue
import threading

from src.vision.diagnostic_capture import RESERVE_BYTES, validate_request


class AsyncTrace:
    """Bounded sidecar writer: runtime locks must never wait for SD-card writes."""
    def __init__(self, stream, max_records=1200):
        self.stream=stream
        self.queue=queue.Queue(maxsize=max_records)
        self.stopping=threading.Event()
        self.error=None
        self.thread=threading.Thread(target=self._run,name='diagnostic-trace-writer',daemon=True)
        self.thread.start()

    def write(self,line):
        if self.error: raise OSError(self.error)
        self.queue.put_nowait(line)

    def flush(self):
        # Actual flush belongs to the writer thread, never the runtime caller.
        if self.error: raise OSError(self.error)

    def _run(self):
        try:
            while not self.stopping.is_set() or not self.queue.empty():
                try:line=self.queue.get(timeout=.05)
                except queue.Empty:continue
                try:
                    self.stream.write(line)
                    self.stream.flush()
                finally:self.queue.task_done()
        except Exception as error:self.error=str(error)
        finally:self.stream.close()

    def close(self):
        self.stopping.set()
        self.thread.join(5)
        if self.thread.is_alive(): raise OSError('DIAGNOSTIC_TRACE_FLUSH_TIMEOUT')
        if self.error: raise OSError(self.error)


class DiagnosticController:
    def __init__(self, service):
        self.service = service
        self.root = Path(__file__).resolve().parents[3] / 'captures'
        self.value = {'state': 'IDLE'}
        self.trace = None
        self.clip_id = None
        self.events = []
        self.trace_error = None

    def update(self, value):
        if value and (value.get('clip_id') == self.clip_id or self.clip_id is None):
            self.value = value
            if self.trace_error:
                self.value=dict(value,state='ERROR',error=self.trace_error)
            elif self.trace and self.trace.error:
                self.value=dict(value,state='ERROR',error='TRACE_WRITE: '+self.trace.error)
            elif self.trace and value.get('state') in ('SAVED','SAVED_WITH_DROPS') and self.trace.queue.unfinished_tasks:
                self.value=dict(value,state='SAVING')

    def start(self, body, context):
        request = validate_request(body)
        if self.value['state'] in ('STARTING', 'RECORDING', 'SAVING'):
            raise ValueError('CAPTURE_ALREADY_ACTIVE_OR_SAVING')
        if self.service.active or self.service.state != 'IDLE' or not self.service.status()['camera_ready']:
            raise ValueError('CAPTURE_REQUIRES_READY_CAMERA_AND_NO_ACTIVE_INSPECTION')
        self.root.mkdir(exist_ok=True)
        if shutil.disk_usage(self.root).free < RESERVE_BYTES + request['max_bytes']:
            raise OSError('CAPTURE_DISK_RESERVE_REQUIRED')
        folder = self.root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_') + request['clip_id'] + '_' + uuid.uuid4().hex[:8])
        folder.mkdir()
        self.close()
        trace = AsyncTrace((folder / 'runtime.jsonl').open('x', encoding='utf-8'))
        try:
            self.service.commands.put_nowait(dict(type='diagnostic_capture', action='start', folder=str(folder),
                                                  request=request, context=context))
        except Exception:
            trace.close()
            raise
        self.trace = trace
        self.trace_error = None
        self.clip_id = request['clip_id']
        self.value = dict(state='STARTING', clip_id=self.clip_id, path=str(folder), error=None)
        return self.value

    def stop(self):
        if self.value['state'] in ('STARTING', 'RECORDING'):
            self.service.commands.put_nowait(dict(type='diagnostic_capture', action='stop'))
            self.value = dict(self.value, state='SAVING')
        return self.value

    def worker_exited(self):
        """Cached progress is not proof that a dead Worker is still saving."""
        if self.value['state'] in ('STARTING', 'RECORDING', 'SAVING'):
            self.value = dict(self.value, state='ERROR',
                error='CAPTURE_WORKER_EXITED_BEFORE_SAVE_CONFIRMED',
                last_reported_saved_frames=self.value.get('saved_frames', 0),
                counts_authority='LAST_WORKER_REPORT_NOT_DISK_AUDIT',
                buffered_data_recoverable=False)
            if self.trace:
                self.trace.stopping.set()  # Drain asynchronously, no runtime lock wait.

    def record(self, value):
        if self.trace and not self.trace_error and value.get('clip_id') == self.clip_id:
            try:
                self.trace.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
                self.trace.flush()
            except Exception as error:
                # Diagnostics cannot change product/PLC decisions. An incomplete
                # trace invalidates the clip and is visible to the operator.
                self.value = dict(self.value, state='ERROR', error='RUNTIME_TRACE_WRITE: ' + str(error))
                self.trace_error=self.value['error']
                self.trace.stopping.set()  # No join while holding runtime locks.

    def close(self):
        if self.trace:
            self.trace.close()
            self.trace = None
