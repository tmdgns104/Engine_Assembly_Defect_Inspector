"""Single journal writer supervising an isolated GPU/camera process."""

import multiprocessing as mp
import queue
import threading
import time
import uuid
import json

from src.journal.sqlite import ConflictError, Journal
from src.recipe.package import load_package
from src.vision.inspection_worker import worker_main
from src.control.mock_cell import MockCell
from src.decision.calibration import station_fingerprint
from apps.edge_service.mock_port import ServiceMockPort


class ProcessFlag:
    """Single-writer shared flag; a killed child cannot strand a Condition lock."""
    def __init__(self, context): self.value = context.RawValue('b', False)
    def set(self): self.value.value = True
    def clear(self): self.value.value = False
    def is_set(self): return bool(self.value.value)
    def wait(self, seconds):
        deadline = time.monotonic()+seconds
        while not self.is_set() and time.monotonic()<deadline:
            time.sleep(min(.02,max(0,deadline-time.monotonic())))
        return self.is_set()


class InspectionService:
    def __init__(self, package_root, station, data_root, worker_target=worker_main):
        self.station = dict(station)
        self.package = load_package(package_root)
        self.journal = Journal(data_root, station['station_id'])
        selected=self.journal.db.execute("SELECT value FROM service_state WHERE key='active_package'").fetchone()
        if selected:
            self.package=load_package(selected[0])
        self.recovery = self.journal.recover()
        self.session = self.journal.new_session(station['cell_id'])
        self.calibration = self._load_calibration()
        self.lock = threading.RLock()
        self.worker_target = worker_target
        self.ctx = mp.get_context('spawn')
        # Server-owned bounded queues survive a Worker killed during a large PNG transfer.
        self.manager = self.ctx.Manager()
        self.active = None
        self.state, self.error, self.backend = 'INIT', None, None
        self.preview, self.preview_received = None, 0
        self.closed = threading.Event()
        self.close_complete=False
        self.process = None
        self.mock = MockCell(ServiceMockPort(self))
        self.sender = None
        self.switching = False
        self._launch()
        self.monitor = threading.Thread(target=self._monitor, daemon=True)
        self.monitor.start()

    def _calibration_matches(self, candidate):
        if not candidate or candidate.get('coordinate_space') != 'normalized_image':
            return False
        expected = {'manifest_sha256': self.package.manifest_hash,
                    'product_id': self.package.manifest['product_id'],
                    'capture_sha256': self.package.manifest['files']['capture']['sha256'],
                    'recipe_sha256': self.package.manifest['files']['recipe']['sha256'],
                    'station_id': self.station['station_id'], 'cell_id': self.station['cell_id'],
                    'station_sha256': station_fingerprint(self.station)}
        return all(candidate.get(key) == value for key, value in expected.items())

    def _load_calibration(self):
        candidate = self.journal.calibration(self.package.manifest_hash, self.station['station_id'])
        if (self._calibration_matches(candidate) and candidate.get('confirmed') is True
                and candidate.get('source_inspection_id') == self._latest_reference_id()):
            return candidate
        return None

    def _latest_reference_id(self):
        # A new reference attempt invalidates use of an older approval, even
        # after restart or a failed capture. The historical approval stays intact.
        with self.journal.lock:
            row = self.journal.db.execute(
                "SELECT inspection_id FROM inspections WHERE cell_id=? "
                "AND json_extract(package_json,'$.manifest_sha256')=? "
                "AND json_extract(request_json,'$.kind')='calibrate' ORDER BY rowid DESC LIMIT 1",
                (self.station['cell_id'], self.package.manifest_hash)).fetchone()
        return row[0] if row else None

    def _launch(self):
        self.generation = uuid.uuid4().hex
        self.commands, self.results, self.previews = (self.manager.Queue(maxsize=n) for n in (1, 2, 1))
        self.stopping, self.cancellation = ProcessFlag(self.ctx), ProcessFlag(self.ctx)
        self.heartbeat = self.ctx.RawValue('d', time.monotonic())
        self.started = time.monotonic()
        self.preview, self.backend = None, None
        self.state, self.error = 'INIT', None
        self.process = self.ctx.Process(target=self.worker_target, args=(str(self.package.root), self.station,
            self.generation, self.commands, self.results, self.previews, self.stopping,
            self.cancellation, self.heartbeat), daemon=True)
        self.process.start()

    def _stop_worker(self):
        self.stopping.set()
        self.process.join(3)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(3)
        if self.process.is_alive():
            raise RuntimeError('WORKER_STOP_UNCONFIRMED')

    def _fault(self, reason):
        self.state, self.error, self.preview = 'RECOVERY', reason, None
        self.cancellation.set()
        if self.active:
            try:
                self.journal.cancel(self.active['inspection_id'], reason)
            except Exception as error:
                self.error += '; JOURNAL: ' + str(error)
            self.active = None

    def _monitor(self):
        while not self.closed.wait(.03):
            with self.lock:
                try:
                    while True:
                        message = self.results.get_nowait()
                        if message['generation'] != self.generation:
                            continue
                        if message['type'] == 'ready':
                            self.backend, self.state = message['backend'], 'IDLE'
                        elif message['type'] == 'fault':
                            self._fault(message['error'])
                        elif message['type'] == 'result':
                            if not self.active or message['inspection_id'] != self.active['inspection_id']:
                                self.journal.finish(message['inspection_id'], message['result'], ())
                                continue
                            if time.monotonic() > self.active['deadline'] or self.cancellation.is_set():
                                self.journal.cancel(message['inspection_id'], 'CANCELLED_OR_EXPIRED')
                            else:
                                message['result']['execution'] = {'source': 'mock' if self.backend.get('backend')=='mock' else 'live', 'control': self.active['request'].get('control_mode','manual'),
                                    'station_id': self.station['station_id'], 'worker_generation': self.generation}
                                message['result']['worker_result_received_ms'] = (time.monotonic()-self.active['accepted_monotonic'])*1000
                                self.journal.finish(message['inspection_id'], message['result'], message['images'])
                                # This separate immutable event measures through the completed result commit.
                                elapsed=(time.monotonic()-self.active['accepted_monotonic'])*1000
                                with self.journal.lock,self.journal.db:
                                    self.journal._event('INSPECTION_DURABLE_TIMING',{'inspection_id':message['inspection_id'],
                                        'request_to_durable_result_ms':elapsed,'clock':'edge_monotonic',
                                        'source_mode':'mock' if self.backend.get('backend')=='mock' else 'live'})
                            self.active = None
                            self.state = 'IDLE'
                except queue.Empty:
                    pass
                except Exception as error:
                    self._fault('RESULT_STORAGE_OR_WORKER_ERROR: ' + str(error))
                try:
                    while True:
                        preview = self.previews.get_nowait()
                        if preview['generation'] == self.generation and self.state != 'RECOVERY':
                            self.preview, self.preview_received = preview, time.monotonic()
                except queue.Empty:
                    pass
                if self.active and time.monotonic() > self.active['deadline']:
                    # Cancel acknowledgement is not worker termination. Remain unavailable.
                    self.journal.cancel(self.active['inspection_id'], 'DEADLINE_EXCEEDED')
                    self.cancellation.set()
                    self.state = 'CANCELLING'
                    if time.monotonic() > self.active['deadline'] + 5:
                        self._stop_worker()
                        self._fault('WORKER_DEADLINE_RECOVERY_REQUIRED')
                if self.state != 'RECOVERY' and not self.process.is_alive():
                    self._fault('WORKER_EXITED')
                if self.state not in ('RECOVERY', 'INIT') and time.monotonic()-self.heartbeat.value > 5:
                    self._fault('WORKER_HEARTBEAT_LOST')
                if self.state == 'INIT' and time.monotonic()-self.started > self.station.get('startup_timeout_seconds', 90):
                    self._fault('WORKER_STARTUP_TIMEOUT')
                try:
                    before=self.mock.state
                    self.mock.tick()
                    if before!=self.mock.state:
                        with self.journal.lock,self.journal.db:
                            self.journal._event('MOCK_STATE_CHANGED',self.mock.status())
                except Exception as error:
                    self.mock.transition('FAULT','CONTROL_ERROR: '+str(error))

    def status(self):
        with self.lock:
            storage_error = None
            try:
                self.journal.capacity()
            except OSError as error:
                storage_error = str(error)
            camera = bool(self.preview and time.monotonic()-self.preview_received < 2 and self.process.is_alive())
            control_idle=self.mock.state in ('IDLE','RECOVERY')
            with self.journal.lock:
                pending_cycles=self.journal.db.execute("SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchone()[0]
            return {'app_release': 'app_v007', 'state': self.state, 'error': self.error or storage_error,
                'ready': self.state == 'IDLE' and camera and bool(self.calibration) and not storage_error and not self.switching and control_idle and not pending_cycles,
                'camera_ready': camera, 'worker_pid': self.process.pid, 'worker_alive': self.process.is_alive(),
                'plc_session_id': self.session, 'cell_id': self.station['cell_id'],
                'active_inspection_id': self.active['inspection_id'] if self.active else None,
                'backend': self.backend, 'package': self.package.snapshot(),
                'calibration_confirmed': bool(self.calibration), 'recovery': self.recovery,
                'calibration_source_inspection_id': self.calibration.get('source_inspection_id') if self.calibration else None,
                'latest_reference_inspection_id': self._latest_reference_id(),
                'mock':self.mock.status(),'pc_sync':{'error':self.sender.error,'last_success':self.sender.last_success} if self.sender else {'state':'NOT_CONFIGURED'}}

    def allocate_request(self):
        with self.lock,self.journal.lock,self.journal.db:
            key='request_counter:'+str(self.session)
            row=self.journal.db.execute('SELECT value FROM service_state WHERE key=?',(key,)).fetchone()
            number=int(row[0])+1 if row else 1
            if number>4294967295:raise ConflictError('REQUEST_COUNTER_EXHAUSTED_RESTART_SESSION_REQUIRED')
            self.journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(number)))
            return {'cell_id':self.station['cell_id'],'plc_session_id':self.session,'request_id':number,
                'cycle_id':number,'attempt':1,'package_sha256':self.package.manifest_hash}

    def submit(self, request):
        with self.lock:
            # Check old keys before checking busy/session: transport retries return the original job.
            existing = self.journal.find_request(request)
            if existing:
                return self.journal.detail(existing['inspection_id']), False
            if request['cell_id'] != self.station['cell_id'] or request['plc_session_id'] != self.session:
                raise ConflictError('SESSION_MISMATCH')
            if request.get('package_sha256') != self.package.manifest_hash:
                raise ConflictError('PACKAGE_MISMATCH')
            if request.get('kind') not in ('inspect', 'calibrate') or not isinstance(request.get('view_assessment'), dict):
                raise ValueError('Invalid inspection request')
            if self.switching or (self.mock.state not in ('IDLE','RECOVERY') and request!=self.mock.job):
                raise ConflictError('CONTROL_CYCLE_BUSY')
            with self.journal.lock:
                unresolved=self.journal.db.execute("SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchone()[0]
            if unresolved and request!=self.mock.job:
                raise ConflictError('UNFINISHED_CYCLE_RECOVERY_REQUIRED')
            if request.get('control_mode')=='mock' and request!=self.mock.job:
                raise ConflictError('CONTROL_AGENT_OWNS_MOCK_REQUESTS')
            if self.state != 'IDLE' or self.active:
                raise ConflictError('BUSY_OR_RECOVERY')
            if not self.status()['camera_ready']:
                raise ConflictError('CAMERA_NOT_READY')
            if request['kind'] == 'inspect' and not self.calibration:
                raise ConflictError('CALIBRATION_REQUIRED')
            if request['kind'] == 'calibrate':
                view = request['view_assessment']
                if (view.get('product_identity') != 'human_confirmed' or view.get('alignment_confirmed') is not True
                        or any(view.get('visible_slots', {}).get(s['id']) is not True for s in self.package.recipe['slots'])):
                    raise ConflictError('정상 제품의 배치와 모든 자리 가시성을 사람이 먼저 확인해 주세요.')
            identifier, created = self.journal.admit(request, self.package.snapshot())
            if request['kind'] == 'calibrate':
                self.calibration = None
            accepted = time.monotonic()
            self.active = {'inspection_id': identifier, 'request': request, 'accepted_monotonic': accepted,
                'deadline': accepted + self.station['inspection_timeout_seconds'], 'calibration': self.calibration}
            self.cancellation.clear()
            self.state = 'BUSY'
            try:
                self.commands.put_nowait(self.active)
            except queue.Full:
                self._fault('COMMAND_QUEUE_FULL')
                raise ConflictError('COMMAND_QUEUE_FULL')
            return self.journal.detail(identifier), created

    def cancel(self, identifier):
        with self.lock:
            if self.active and self.active['inspection_id'] == identifier:
                self.journal.cancel(identifier, 'USER_CANCELLED')
                self.cancellation.set()
                self.state = 'CANCELLING'
            return self.journal.detail(identifier)

    def confirm_calibration(self, identifier, confirmed):
        with self.lock:
            if confirmed is not True or self.state != 'IDLE':
                raise ConflictError('HUMAN_CONFIRMATION_OR_IDLE_REQUIRED')
            detail = self.journal.detail(identifier)
            if not detail or detail['state'] != 'COMPLETE' or detail['request']['kind'] != 'calibrate':
                raise ConflictError('REFERENCE_RESULT_REQUIRED')
            candidate = (detail['result'] or {}).get('calibration_candidate')
            if (not self._calibration_matches(candidate) or candidate.get('source_inspection_id') != identifier
                    or detail['plc_session_id'] != self.session or identifier != self._latest_reference_id()):
                raise ConflictError('CURRENT_PACKAGE_REFERENCE_REQUIRED')
            candidate = dict(candidate, confirmed=True, source_inspection_id=identifier)
            self.journal.save_calibration(self.package.manifest_hash, self.station['station_id'], candidate)
            self.calibration = candidate
            return candidate

    def activate(self, package_root):
        candidate = load_package(package_root)
        with self.lock:
            if self.active or self.state not in ('IDLE', 'RECOVERY') or self.switching or self.mock.state not in ('IDLE','RECOVERY'):
                raise ConflictError('IDLE_REQUIRED')
            with self.journal.lock:
                pending=self.journal.db.execute("SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchone()[0]
            if pending:raise ConflictError('UNFINISHED_CYCLE_RECOVERY_REQUIRED')
            self.switching=True
            previous = self.package
            self._stop_worker()
            self.package = candidate
            self.calibration = self._load_calibration()
            self.session = self.journal.new_session(self.station['cell_id'])
            self._launch()
        deadline = time.monotonic() + self.station.get('startup_timeout_seconds',90)
        while time.monotonic() < deadline:
            with self.lock:
                state = self.state
            if state == 'IDLE':
                with self.lock,self.journal.lock,self.journal.db:
                    self.journal.db.execute("INSERT INTO service_state VALUES ('active_package',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(candidate.root),))
                    self.journal._event('PACKAGE_ACTIVATED',{'manifest_sha256':candidate.manifest_hash})
                    self.switching=False
                return {'activated': True, 'package': candidate.manifest_hash}
            if state == 'RECOVERY':
                break
            time.sleep(.05)
        with self.lock:
            failure = self.error or 'ACTIVATION_TIMEOUT'
            self._stop_worker()
            self.package = previous
            self.calibration = self._load_calibration()
            self.session = self.journal.new_session(self.station['cell_id'])
            self._launch()
        deadline = time.monotonic() + self.station.get('startup_timeout_seconds',90)
        while time.monotonic() < deadline and self.state == 'INIT':
            time.sleep(.05)
        with self.lock,self.journal.lock,self.journal.db:
            self.switching=False
            self.journal._event('PACKAGE_ACTIVATION_FAILED',{'reason':failure,'previous_restored':self.state=='IDLE','previous_manifest_sha256':previous.manifest_hash})
        return {'activated':False,'reason':failure,'previous_restored':self.state == 'IDLE'}

    def close(self):
        if self.close_complete:return
        if self.sender:self.sender.close()
        self.closed.set()
        self.monitor.join(5)
        with self.lock:
            if self.active:
                self.journal.cancel(self.active['inspection_id'], 'SERVICE_SHUTDOWN')
            self._stop_worker()
            self.journal.close()
            self.manager.shutdown()
            self.close_complete=True
