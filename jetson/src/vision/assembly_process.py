"""One frozen assembly owner, isolated from Runtime/IPC's Python interpreter.

Native feature matching can hold the GIL while the live camera also uses the
GPU. Only committed row metadata crosses this boundary. The child reads the
existing PNG evidence and owns neither a camera nor a PLC connection.
"""
from copy import deepcopy
import json
import multiprocessing as mp
from pathlib import Path
import queue
import threading
import time

from src.vision.assembly_inspection import AssemblyInspector
from src.vision.misassembly_shadow import ShadowObserver


def _assembly_process(data_root, output_root, assets_root, loader, jobs, events):
    inspector = AssemblyInspector(data_root, output_root, assets_root=assets_root,
                                  loader=loader, start=False)
    try:
        inspector.loaded = inspector.loader()
        events.put(dict(kind='READY'), timeout=1)
    except Exception as error:
        events.put(dict(kind='FAILED', error=f'ASSEMBLY_LOAD:{type(error).__name__}:{error}'), timeout=1)
        return
    while True:
        row = jobs.get()
        if row is None:
            return
        identifier = row['inspection_id']
        events.put(dict(kind='STARTED', inspection_id=identifier), timeout=1)
        try:
            try:
                inspector.process_one(row)
            except Exception as error:
                inspector._save(identifier, dict(state='ERROR',
                    reason=f'{type(error).__name__}:{error}', inspection_id=identifier,
                    production_decision=row['decision'], plc_output=False))
            # _save fsyncs the evidence before this acknowledgement. The parent
            # must not infer completion from result.json appearing early.
            events.put(dict(kind='DURABLE', inspection_id=identifier,
                            latest=inspector.latest), timeout=1)
        except Exception as error:
            events.put(dict(kind='FAILED', inspection_id=identifier,
                error=f'ASSEMBLY_RECORDING_FAILED:{type(error).__name__}:{error}'), timeout=1)
            return


class ProcessAssemblyInspector:
    checked_id = staticmethod(ShadowObserver.checked_id)
    evidence_path = ShadowObserver.evidence_path

    def __init__(self, data_root, output_root, *, assets_root=None, loader=None):
        self.data_root = Path(data_root).resolve()
        self.output_root = Path(output_root).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self._ready = False
        self.load_error = None
        self.active_identifier = None
        self.pending_identifier = None
        self.completed = set()
        self.latest = dict(state='WAITING_FOR_DURABLE_INSPECTION', source='ASSEMBLY_INSPECTOR', plc_output=False)
        context = mp.get_context('spawn')
        self.jobs, self.events = context.Queue(maxsize=1), context.Queue(maxsize=4)
        self.process = context.Process(target=_assembly_process,
            args=(str(self.data_root), str(self.output_root), assets_root, loader, self.jobs, self.events),
            name='assembly-inspector', daemon=True)
        self.process.start()
        self.thread = threading.Thread(target=self._monitor, name='assembly-status', daemon=True)
        self.thread.start()

    @property
    def ready(self):
        with self.lock:
            return self._ready and not self.stop.is_set() and self.process.is_alive()

    def _monitor(self):
        while not self.stop.is_set():
            try:
                event = self.events.get(timeout=.05)
            except queue.Empty:
                if not self.process.is_alive():
                    with self.lock:
                        self._ready = False
                        self.load_error = self.load_error or 'ASSEMBLY_PROCESS_EXITED'
                    return
                continue
            with self.lock:
                kind = event['kind']
                identifier = event.get('inspection_id')
                if kind == 'READY':
                    self._ready = True
                elif kind == 'FAILED':
                    self._ready = False
                    self.load_error = event['error']
                    return
                elif identifier != self.pending_identifier:
                    self._ready = False
                    self.load_error = 'ASSEMBLY_PROCESS_IDENTITY_MISMATCH'
                    return
                elif kind == 'STARTED':
                    self.active_identifier = identifier
                elif kind == 'DURABLE':
                    self.completed.add(identifier)
                    if len(self.completed) > 512:
                        self.completed = {identifier}
                    self.latest = event['latest']
                    self.pending_identifier = self.active_identifier = None
                else:
                    self._ready = False
                    self.load_error = 'ASSEMBLY_PROCESS_PROTOCOL_ERROR'
                    return

    def submit(self, row):
        identifier = self.checked_id(row['inspection_id'])
        with self.lock:
            if identifier in self.completed or self.evidence_path(identifier).parent.exists():
                raise ValueError('DUPLICATE_ASSEMBLY_INSPECTION')
            if self.pending_identifier is not None:
                raise ValueError('ASSEMBLY_PROCESS_BUSY')
            if not self.ready:
                raise ValueError('ASSEMBLY_PROCESS_NOT_READY')
            self.pending_identifier = identifier
            try:
                self.jobs.put_nowait(deepcopy(row))
            except Exception:
                self.pending_identifier = None
                raise

    def result(self, identifier):
        self.checked_id(identifier)
        with self.lock:
            if identifier not in self.completed:
                return None
        result = json.loads(self.evidence_path(identifier).read_text(encoding='utf-8'))
        if result.get('inspection_id') != identifier:
            raise ValueError('ASSEMBLY_RESULT_IDENTITY_MISMATCH')
        return result

    def status(self):
        with self.lock:
            alive = self.process.is_alive()
            return dict(self.latest, ready=self.ready,
                pending=int(self.pending_identifier is not None and self.active_identifier is None),
                outstanding=int(self.pending_identifier is not None), active_identifier=self.active_identifier,
                error=self.load_error or ('ASSEMBLY_PROCESS_EXITED' if not alive and not self.stop.is_set() else None),
                worker_pid=self.process.pid, worker_alive=alive, mode='REFERENCE_ANALYSIS_WITH_DURABLE_EVIDENCE',
                execution_owner='ASSEMBLY_PROCESS_NO_CAMERA')

    def close(self):
        if self.stop.is_set():
            return {'worker_stopped': not self.process.is_alive()}
        self.stop.set()
        with self.lock:
            self._ready = False
        try:
            self.jobs.put_nowait(None)
        except queue.Full:
            pass
        self.process.join(3)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(3)
        self.thread.join(1)
        # A killed reader must not hold shutdown behind a queued row's feeder.
        for channel in (self.jobs, self.events):
            channel.cancel_join_thread()
            channel.close()
        if self.process.is_alive():
            raise RuntimeError('ASSEMBLY_PROCESS_STOP_UNCONFIRMED')
        return {'worker_stopped': True}
