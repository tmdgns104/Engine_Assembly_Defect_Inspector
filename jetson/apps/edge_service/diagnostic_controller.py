"""Service-side capture control and exact consumed-packet trace, no camera access."""
from src import config as parameters
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import uuid
import queue
import threading
from types import SimpleNamespace

from src.vision.diagnostic_capture import RESERVE_BYTES, validate_request

RUN_TRACE_BYTES = 8*1024*1024


class BufferedTrace:
    """Operating trace stays in bounded memory until Runtime grants safe STOP IO."""
    def __init__(self, folder):
        self.folder = Path(folder)
        self.lines = []
        self.bytes = 0
        self.error = None
        self.stopping = threading.Event()
        self.abandoned = threading.Event()
        self.queue = SimpleNamespace(unfinished_tasks=1)
        self.thread = None

    def write(self, line):
        if self.stopping.is_set(): return
        if len(line) > 65536 or len(self.lines) >= 1200 or self.bytes+len(line.encode('utf-8')) > RUN_TRACE_BYTES//2:
            self.error = 'RUN_TRACE_LIMIT'
            self.stopping.set()
            raise OSError(self.error)
        self.lines.append(line)
        self.bytes += len(line.encode('utf-8'))

    def flush(self):
        pass  # Acquisition never asks the filesystem to flush.

    def seal(self):
        self.stopping.set()

    def permit_flush(self, signals):
        self.seal()
        if self.thread is None:
            self.thread = threading.Thread(target=self._save,args=(signals,),
                                           name='stopped-runtime-trace-writer',daemon=True)
            self.thread.start()

    def _save(self, signals):
        def wait_safe():
            while signals.flush_until.value <= time.monotonic():
                if self.abandoned.wait(.02): raise OSError('RUN_TRACE_WORKER_SHUTDOWN')
        try:
            wait_safe()
            with (self.folder/'runtime.jsonl').open('x',encoding='utf-8') as stream:
                for line in self.lines:
                    wait_safe(); stream.write(line); stream.flush()
            wait_safe()
            with (self.folder/'trace_receipt.json').open('x',encoding='utf-8') as stream:
                json.dump(dict(state='ERROR' if self.error else 'SAVED',error=self.error,
                    records=len(self.lines),bytes=self.bytes,policy='RENEWABLE_SAFE_STOP_LEASE'),stream)
        except Exception as error:
            self.error=type(error).__name__+':'+str(error)
        finally:
            self.queue.unfinished_tasks=0

    def close(self):
        if self.queue.unfinished_tasks:
            self.error = self.error or 'RUN_TRACE_UNSAVED_ON_CLOSE'
            self.abandoned.set()


class AsyncTrace:
    """Bounded sidecar writer: runtime locks must never wait for SD-card writes."""
    def __init__(self, stream, max_records=parameters.DIAGNOSTIC_TRACE_RECORDS):
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
            if value.get('mode') == 'RUN_DIAGNOSTIC':
                value = dict(value, worker_state=value['state'])
            self.value = value
            if self.trace_error:
                self.value=dict(value,state='ERROR',error=self.trace_error)
            elif self.trace and self.trace.error:
                self.value=dict(value,state='ERROR',error='TRACE_WRITE: '+self.trace.error)
            elif self.trace and value.get('state') in ('SAVED','SAVED_WITH_DROPS') and self.trace.queue.unfinished_tasks:
                self.value=dict(value,state='SAVING')

    def arm_run(self, body, context, signals):
        from src.vision.run_capture import validate_run_request
        request = validate_run_request(body)
        if self.value['state'] in ('STARTING','ARMED','RECORDING','WAIT_SAFE_FLUSH','SAVING'):
            raise ValueError('CAPTURE_ALREADY_ACTIVE_OR_SAVING')
        if isinstance(self.trace,BufferedTrace) and self.trace.queue.unfinished_tasks:
            raise ValueError('RUN_TRACE_UNSAVED')
        if self.service.active or self.service.state != 'IDLE' or not self.service.health()['camera_ready']:
            raise ValueError('CAPTURE_REQUIRES_READY_CAMERA_AND_NO_ACTIVE_INSPECTION')
        self.root.mkdir(exist_ok=True)
        if shutil.disk_usage(self.root).free < RESERVE_BYTES+request['max_bytes']:
            raise OSError('CAPTURE_DISK_RESERVE_REQUIRED')
        folder=self.root/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ_')+request['clip_id']+'_'+uuid.uuid4().hex[:8])
        folder.mkdir()
        self.close()
        trace=BufferedTrace(folder)
        worker_request=dict(request,max_bytes=request['max_bytes']-RUN_TRACE_BYTES)
        try:
            self.service.commands.put_nowait(dict(type='run_capture',action='arm',folder=str(folder),
                request=worker_request,context=dict(context,total_memory_limit_bytes=request['max_bytes'])))
        except Exception:
            trace.close(); raise
        self.trace,self.trace_error,self.clip_id=trace,None,request['clip_id']
        self.value=dict(state='STARTING',clip_id=self.clip_id,path=str(folder),mode='RUN_DIAGNOSTIC',error=None)
        return self.value

    def start(self, body, context):
        request = validate_request(body)
        if (self.value.get('worker_state',self.value['state']) in ('STARTING','ARMED','RECORDING','WAIT_SAFE_FLUSH','SAVING')
                or isinstance(self.trace,BufferedTrace) and self.trace.queue.unfinished_tasks):
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
        if self.value['state'] in ('STARTING', 'ARMED', 'RECORDING', 'WAIT_SAFE_FLUSH', 'SAVING'):
            self.value = dict(self.value, state='ERROR', worker_state='ERROR',
                error='CAPTURE_WORKER_EXITED_BEFORE_SAVE_CONFIRMED',
                last_reported_saved_frames=self.value.get('saved_frames', 0),
                counts_authority='LAST_WORKER_REPORT_NOT_DISK_AUDIT',
                buffered_data_recoverable=False)
            if self.trace:
                self.trace.stopping.set()  # Drain asynchronously, no runtime lock wait.

    def record(self, value):
        if self.trace and not self.trace_error and value.get('clip_id') == self.clip_id:
            try:
                self.trace.write(json.dumps(value, ensure_ascii=isinstance(self.trace,BufferedTrace), allow_nan=False) + '\n')
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
