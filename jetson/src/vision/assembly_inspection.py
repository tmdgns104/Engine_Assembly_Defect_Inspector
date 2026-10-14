"""Frozen assembly inference as a required asynchronous decision component."""
import json
import queue
import os

from src.vision.misassembly_shadow import ShadowObserver


class AssemblyInspector(ShadowObserver):
    def __init__(self, *args, **kwargs):
        self.ready = False
        self.load_error = None
        super().__init__(*args, **kwargs)

    def _save(self, identifier, value):
        value.update(source='ASSEMBLY_INSPECTOR', used_by_final_policy=True,
                     timing_scope='REQUIRED_COMPONENT_BEFORE_PLC_PUBLICATION')
        super()._save(identifier, value)
        folder = self.evidence_path(identifier).parent
        for path in folder.iterdir():
            if path.is_file():
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
        if os.name == 'posix':
            descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        self.latest.update(source='ASSEMBLY_INSPECTOR', used_by_final_policy=True)

    def _run(self):
        try:
            self.loaded = self.loader()
            self.ready = True
        except Exception as error:
            self.load_error = f'{type(error).__name__}:{error}'
            return
        while not self.stop.is_set():
            try: row = self.jobs.get(timeout=.2)
            except queue.Empty: continue
            try:
                self.process_one(row)
            except Exception as error:
                try:
                    self._save(row['inspection_id'], dict(state='ERROR',
                        reason=f'{type(error).__name__}:{error}', inspection_id=row['inspection_id'],
                        production_decision=row['decision'], plc_output=False))
                except Exception as storage_error:
                    self.ready = False
                    self.load_error = 'ASSEMBLY_RECORDING_FAILED:' + str(storage_error)
                    return

    def result(self, identifier):
        path = self.evidence_path(identifier)
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None

    def status(self):
        return dict(self.latest, pending=self.jobs.qsize(), ready=self.ready,
                    error=self.load_error, mode='REQUIRED_FINAL_COMPONENT')
