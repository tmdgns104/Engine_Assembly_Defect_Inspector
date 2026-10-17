"""Assembly reference analysis with durable evidence before PLC publication."""
import json
import queue
import os

from src.vision.misassembly_shadow import ShadowObserver


class AssemblyInspector(ShadowObserver):
    def __init__(self, *args, **kwargs):
        self.ready = False
        self.load_error = None
        self.active_identifier = None
        super().__init__(*args, **kwargs)

    def _save(self, identifier, value):
        value.update(source='ASSEMBLY_INSPECTOR', used_by_final_policy=False,
                     evidence_required_before_publication=True,
                     timing_scope='REFERENCE_ANALYSIS_AWAITED_BEFORE_PLC_PUBLICATION')
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
        self.latest.update(source='ASSEMBLY_INSPECTOR', used_by_final_policy=False,
                           evidence_required_before_publication=True)

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
            self.active_identifier = row['inspection_id']
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
            finally:
                self.active_identifier = None
                self.jobs.task_done()

    def result(self, identifier):
        path = self.evidence_path(identifier)
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None

    def status(self):
        # unfinished_tasks spans enqueue -> get -> completion, including the
        # brief handoff before active_identifier is assigned by the worker.
        with self.jobs.mutex:
            outstanding = self.jobs.unfinished_tasks
        return dict(self.latest, pending=self.jobs.qsize(), ready=self.ready,
                    active_identifier=self.active_identifier, outstanding=outstanding,
                    error=self.load_error, mode='REFERENCE_ANALYSIS_WITH_DURABLE_EVIDENCE')
