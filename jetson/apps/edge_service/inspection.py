"""Single journal writer supervising an isolated GPU/camera process."""
from src import config as parameters

import multiprocessing as mp
import queue
import threading
import time
import uuid
import json
import logging
import shutil
import math
from collections import deque

from src.journal.sqlite import ConflictError, Journal
from src.recipe.package import load_package
from src.vision.inspection_worker import worker_main
from src.control.mock_cell import MockCell
from src.decision.calibration import station_fingerprint
from apps.edge_service.mock_port import ServiceMockPort
from apps.edge_service.lab_port import ServiceLabPort
from apps.edge_service.result_storage import raw_storage_within_deadline
from src.configuration import snapshot, recorded_package, validate_package_settings, validate_worker_settings
from src.control.lab_modes import LabController


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
    def __init__(self, package_root, station, data_root, worker_target=worker_main, production=False):
        self.production_enabled = production
        self.production_owner = None
        self.configuration = snapshot()
        self.station = dict(station)
        self.package = load_package(package_root)
        self.journal = Journal(data_root, station['station_id'])
        selected=self.journal.db.execute("SELECT value FROM service_state WHERE key='active_package'").fetchone()
        if selected:
            self.package=load_package(selected[0])
        if production:
            try:
                validate_package_settings(self.package)
            except Exception:
                self.journal.db.close()
                raise
        if self.station.get('auto_profile'):
            profile=self.journal.db.execute("SELECT value FROM service_state WHERE key='active_auto_profile'").fetchone()
            if profile:
                self.station['auto_profile']=json.loads(profile[0])
        self.recovery = self.journal.recover()
        self.session = self.journal.new_session(station['cell_id'])
        self.calibration = self._load_calibration()
        self.lock = threading.RLock()
        self.worker_target = worker_target
        self.ctx = mp.get_context('spawn')
        # Server-owned bounded queues survive a Worker killed during a large PNG transfer.
        self.manager = self.ctx.Manager()
        self.active = None
        self.production_admission_pending = None
        self.progress = None
        self.state, self.error, self.backend = 'INIT', None, None
        self.preview, self.preview_received = None, 0
        self.preview_times=deque(maxlen=parameters.PREVIEW_RATE_SAMPLE_COUNT)
        self.latest_timing=None
        from apps.edge_service.result_storage import ResultStorage
        from src.runtime.health_diagnostics import HealthDiagnostics
        self.storage = ResultStorage(self.journal)
        self.storage_pending = None
        self.health_diagnostics = HealthDiagnostics()
        self._status_cache = {}
        self.closed = threading.Event()
        self.close_complete=False
        self.process = None
        self.mock = MockCell(ServiceMockPort(self))
        self.lab = LabController(ServiceLabPort(self))
        self.sender = None
        self.switching = False
        from apps.edge_service.diagnostic_controller import DiagnosticController
        self.diagnostic_capture = DiagnosticController(self)
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
        # These are small observation records, not images. Preserve intermediate
        # observations through a short consumer/Journal stall; the preview queue
        # remains latest-only. Passage source-gap and age limits still reject
        # genuinely missing or stale evidence, including longer overflows.
        self.products = self.manager.Queue(maxsize=parameters.PRODUCT_OBSERVATION_QUEUE_SIZE) if (self.station.get('auto_profile') or self.production_enabled) else None
        self.product_latest = None
        self.stopping, self.cancellation = ProcessFlag(self.ctx), ProcessFlag(self.ctx)
        self.production_tracking = ProcessFlag(self.ctx)
        # Only the native Worker implements this optional diagnostic protocol.
        # Custom/test worker call signatures remain unchanged.
        from src.vision.run_capture import RunCaptureSignals
        self.run_capture_signals = RunCaptureSignals(self.ctx) if self.worker_target is worker_main else None
        self.heartbeat = self.ctx.RawValue('d', time.monotonic())
        self.started = time.monotonic()
        self.preview, self.backend = None, None
        self.preview_times.clear()
        self.state, self.error = 'INIT', None
        self.process = self.ctx.Process(target=self.worker_target, args=(str(self.package.root), self.station,
            self.generation, self.commands, self.results, self.previews, self.stopping,
            self.cancellation, self.heartbeat) + ((self.products,) if self.products is not None else ()) + ((self.production_tracking,) if self.production_enabled else ()),
            kwargs=({'run_capture_signals':self.run_capture_signals} if self.run_capture_signals is not None else {}), daemon=True)
        self.process.start()

    def _stop_worker(self):
        self.stopping.set()
        self.process.join(3)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(3)
        if self.process.is_alive():
            raise RuntimeError('WORKER_STOP_UNCONFIRMED')

    def _record_request_failure(self, reason):
        """V2 accepted requests end with a durable ERROR, not a lost cancellation.

        The worker is still cancelled/drained by the existing monitor. A late
        result cannot replace this terminal record. Legacy cancellation is kept.
        """
        binding = self.active.get('production_binding') or {}
        if binding.get('plc_contract') in ('EXTENDED_V2', 'STANDALONE_V3'):
            row = self.journal.detail(self.active['inspection_id'])
            if row is not None and row['state'] != 'ACCEPTED':
                return
            self.journal.finish(self.active['inspection_id'], dict(
                decision='ERROR', reason=reason, reason_code=reason, observations=[],
                evidence_missing_reason='REQUEST_FAILED_BEFORE_VALID_EVIDENCE',
                production_identity=binding, physical_output_enabled=False,
                execution={'source': 'live', 'control': 'production', 'worker_generation': self.generation}))
        else:
            self.journal.cancel(self.active['inspection_id'], reason)

    def _storage_completions(self):
        try:
            completed = self.storage.completed.get_nowait()
        except queue.Empty:
            return
        context = completed['context']
        if context is not self.storage_pending:
            self._fault('STORAGE_CONTEXT_MISMATCH')
            return
        self.storage_pending = None
        self.latest_timing = completed['timing']
        matching = context['generation'] == self.generation and self.active is context['active']
        if completed['error']:
            self._fault('RESULT_STORAGE_ERROR:'+completed['error'])
        elif not matching:
            self._fault('STORAGE_COMPLETION_CONTEXT_CHANGED')
        elif not raw_storage_within_deadline(context):
            self._fault('STORAGE_DEADLINE_EXCEEDED')
        else:
            self.active = None
            if self.state not in ('RECOVERY', 'STOPPED'):
                self.state = 'IDLE'

    def health(self):
        """Current owner/worker health, independent of Journal SQL and fsync.

        This does not authorize a product or declare its result durable.
        """
        with self.lock:
            # The child renews independently of this lock. Snapshot its pulse
            # before sampling now, or a concurrent renewal looks like a future
            # heartbeat and falsely revokes PLC readiness.
            heartbeat_at = self.heartbeat.value
            now = time.monotonic()
            alive = bool(self.process and self.process.is_alive())
            camera = bool(alive and self.preview and 0 <= now-self.preview_received < 2)
            worker_age = now-heartbeat_at
            reason = self.error
            if not alive: reason = reason or 'WORKER_EXITED'
            elif not 0 <= worker_age <= 5: reason = reason or 'WORKER_HEARTBEAT_LOST'
            elif not camera: reason = reason or 'CAMERA_NOT_READY'
            if self.storage_pending:
                context = self.storage_pending
                if (context['generation'] != self.generation or self.active is not context['active']
                        or context['camera_epoch'] != (self.preview or {}).get('freshness', {}).get('camera_epoch')):
                    reason = reason or 'STORAGE_CONTEXT_CHANGED'
                if not raw_storage_within_deadline(context):
                    reason = reason or 'STORAGE_DEADLINE_EXCEEDED'
                if not self.storage.thread.is_alive(): reason = reason or 'STORAGE_WORKER_EXITED'
            disk_started = time.monotonic()
            try:
                if shutil.disk_usage(self.journal.root).free < self.journal.min_free_bytes:
                    reason = reason or 'DISK_SPACE_LOW'
            except OSError:
                reason = reason or 'STORAGE_UNAVAILABLE'
            finally:
                duration_ms = (time.monotonic()-disk_started)*1000
                self.health_diagnostics.record('HEALTH_DISK_CHECK',
                    duration_ms=duration_ms, retain=duration_ms>20)
            identity = (self.state, alive, camera, self.generation,
                        (self.preview or {}).get('freshness', {}).get('camera_epoch'), reason)
            if identity != getattr(self, '_last_health_identity', None):
                self._last_health_identity = identity
                self.health_diagnostics.record('WORKER_CAMERA_STATE', state=self.state,
                    alive=alive, camera_ready=camera, generation=self.generation,
                    camera_epoch=identity[4], reason=reason, worker_heartbeat_age_s=worker_age)
            return dict(state=self.state, error=reason, camera_ready=camera, worker_alive=alive,
                worker_pid=self.process.pid if self.process else None, worker_heartbeat_age_s=worker_age,
                ready=self.state == 'IDLE' and camera and bool(self.calibration) and not reason and not self.switching,
                active_inspection_id=self.active['inspection_id'] if self.active else None,
                storage_pending=self.storage_pending is not None, worker_generation=self.generation,
                camera_epoch=(self.preview or {}).get('freshness', {}).get('camera_epoch'))

    def _fault(self, reason):
        logging.getLogger(__name__).error('검사 Service RECOVERY: %s',reason)
        self.state, self.error, self.preview = 'RECOVERY', reason, None
        self.cancellation.set()
        if self.active and self.storage_pending is None:
            try:
                if self.active.get('production_binding'):
                    self.journal.finish(self.active['inspection_id'],dict(decision='ERROR',reason=reason,reason_code=reason,
                        disposition='REJECT',observations=[],evidence_missing_reason='SYSTEM_FAULT_BEFORE_EVIDENCE_COMMIT',
                        production_identity=self.active['production_binding'],human_acceptance='PENDING',physical_output_enabled=False,
                        execution={'source':'live','control':'production','worker_generation':self.generation}))
                else:
                    self.journal.cancel(self.active['inspection_id'], reason)
            except Exception as error:
                self.error += '; JOURNAL: ' + str(error)
            self.active = None

    def _monitor(self):
        # 예상 밖 저장/감독 오류도 thread를 종료시키지 않는다. 상태는 RECOVERY로 닫힌다.
        while not self.closed.is_set():
            try:
                self._monitor_loop()
            except Exception as error:
                logging.getLogger(__name__).exception('Service monitor 오류; 감독과 API 유지')
                with self.lock:
                    self._fault('MONITOR_ERROR: ' + str(error))
                self.closed.wait(.1)

    def _monitor_loop(self):
        while not self.closed.wait(parameters.SERVICE_POLL_SECONDS):
            waited = time.monotonic()
            with self.lock:
                self.health_diagnostics.record('SERVICE_LOCK_MONITOR', retain=time.monotonic()-waited>.02, wait_ms=(time.monotonic()-waited)*1000)
                self._storage_completions()
                try:
                    while True:
                        start = getattr(self.production_owner, 'request_start', None)
                        if start and start.deferred_events.full():
                            # Keep messages in the bounded Worker queue. Revoke
                            # authority without waiting on the busy Journal.
                            self.error = 'LATE_RESULT_AUDIT_BACKPRESSURE'
                            self.state = 'RECOVERY'
                            self.cancellation.set()
                            self.production_owner.gateway.health_update(False, False, time.monotonic())
                            break
                        message = self.results.get_nowait()
                        if message['generation'] != self.generation:
                            continue
                        if message['type'] == 'ready':
                            if self.worker_target is worker_main:
                                try:
                                    validate_worker_settings(self.configuration, message['backend'])
                                except ValueError as error:
                                    self._fault(str(error))
                                    continue
                            self.backend, self.state = message['backend'], 'IDLE'
                        elif message['type'] == 'diagnostic_capture':
                            self.diagnostic_capture.update(message['status'])
                        elif message['type'] == 'fault':
                            self._fault(message['error'])
                        elif message['type'] == 'progress':
                            if self.active and message['inspection_id']==self.active['inspection_id']:
                                self.progress={k:message[k] for k in ('inspection_id','stage','completed_frames','required_frames')}
                        elif message['type'] == 'result':
                            if message['result'].get('decision') == 'ERROR':
                                logging.getLogger(__name__).error('검사 결과 ERROR inspection=%s: %s',
                                    message['inspection_id'],message['result'].get('reason'))
                            if not self.active or message['inspection_id'] != self.active['inspection_id']:
                                if self.station.get('fresh_frame'):
                                    self._quarantine_late_result(message['inspection_id'])
                                else:
                                    self.journal.finish(message['inspection_id'], message['result'], ())
                                continue
                            rejection = self._result_context_error(message['result'])
                            if rejection:
                                self._record_request_failure(rejection)
                            elif time.monotonic() > self.active['deadline'] or self.cancellation.is_set():
                                self._record_request_failure('CANCELLED_OR_EXPIRED')
                            else:
                                if 'durable_admission_monotonic' in self.active:
                                    # A Worker-provided claim is never authority. The
                                    # active reservation supplies this after validation.
                                    message['result']['durable_admission_monotonic'] = self.active['durable_admission_monotonic']
                                message['result']['execution'] = {'source': 'mock' if self.backend.get('backend')=='mock' else 'live', 'control': self.active['request'].get('control_mode','manual'),
                                    'station_id': self.station['station_id'], 'worker_generation': self.generation}
                                message['result']['worker_result_received_ms'] = (time.monotonic()-self.active['accepted_monotonic'])*1000
                                if self.active.get('experiment_policy'):
                                    message['result'].update(self.active['experiment_policy'])
                                    message['result']['visibility_policy']='EXPERIMENT_SESSION_NOT_PER_FRAME_HAND_EVIDENCE'
                                if self.active.get('production_binding'):
                                    message['result']['production_identity']=self.active['production_binding']
                                    binding=self.active['production_binding']
                                    if binding.get('inspection_motion_mode') in ('CONVEYOR_MOTION_DEV','CONVEYOR_MOTION_PLC_BENCH') and message['result']['decision']!='ERROR':
                                        from src.vision.production_binding import motion_cycle_matches
                                        cycle=self.production_owner.coordinator.active_cycle
                                        track=self.production_owner.coordinator._tracker._track_id
                                        if not motion_cycle_matches(binding,cycle,track):
                                            from src.decision.engine_dynamic import SLOTS
                                            message['result'].update(decision='REVIEW',reason='CONVEYOR_TRACK_BINDING_UNCERTAIN',
                                                reason_code='CONVEYOR_TRACK_BINDING_UNCERTAIN',disposition='REJECT',
                                                slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'),defects=[])
                                if self.storage_pending is not None:
                                    raise RuntimeError('DUPLICATE_STORAGE_HANDOFF')
                                self.storage_pending = dict(active=self.active, generation=self.generation,
                                    camera_epoch=(self.active.get('trigger') or {}).get('capture_epoch'),
                                    inspection_id=message['inspection_id'], started=time.monotonic())
                                self.storage.submit(self.storage_pending, message)
                                continue  # active remains reserved through the durability boundary
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
                            self.diagnostic_capture.update(preview.get('diagnostic_capture'))
                            frame_id=preview.get('freshness',{}).get('frame_id')
                            if frame_id and (not self.preview_times or self.preview_times[-1][0]!=frame_id):
                                self.preview_times.append((frame_id,self.preview_received))
                except queue.Empty:
                    pass
                if self.active and self.storage_pending is None and time.monotonic() > self.active['deadline']:
                    # Cancel acknowledgement is not worker termination. Remain unavailable.
                    self._record_request_failure('DEADLINE_EXCEEDED')
                    self.cancellation.set()
                    self.state = 'CANCELLING'
                    if time.monotonic() > self.active['deadline'] + 5:
                        self._stop_worker()
                        self._fault('WORKER_DEADLINE_RECOVERY_REQUIRED')
                if not self.process.is_alive():
                    self.diagnostic_capture.worker_exited()
                    if self.state not in ('RECOVERY','STOPPED'):
                        self._fault('WORKER_EXITED')
                if self.state not in ('RECOVERY', 'INIT','STOPPED') and time.monotonic()-self.heartbeat.value > 5:
                    self._fault('WORKER_HEARTBEAT_LOST')
                if self.state == 'INIT' and time.monotonic()-self.started > self.station.get('startup_timeout_seconds', parameters.STARTUP_TIMEOUT_SECONDS):
                    self._fault('WORKER_STARTUP_TIMEOUT')
                try:
                    camera=bool(self.preview and time.monotonic()-self.preview_received<2 and self.process.is_alive() and self.state!='RECOVERY')
                    self.lab.tick(time.monotonic(),self.preview.get('scene') if camera else None,camera)
                    before=self.mock.state
                    self.mock.tick()
                    if before!=self.mock.state:
                        with self.journal.lock,self.journal.db:
                            self.journal._event('MOCK_STATE_CHANGED',self.mock.status())
                except Exception as error:
                    if self.lab.mode!='MANUAL': self.lab.fault('LAB_CONTROL_ERROR: '+str(error))
                    self.mock.transition('FAULT','CONTROL_ERROR: '+str(error))

    def _quarantine_late_result(self, identifier):
        payload = dict(inspection_id=identifier, reason='NO_MATCHING_ACTIVE_TRIGGER')
        start = getattr(self.production_owner, 'request_start', None)
        if start:
            # This flag is constructed here, never copied from a Worker result.
            start.defer_event(dict(payload, event='LATE_RESULT_QUARANTINED', event_only=True,
                monotonic_s=time.monotonic(), runtime_session_id=self.production_owner.session_id))
        else:
            with self.journal.lock, self.journal.db:
                self.journal._event('LATE_RESULT_QUARANTINED', payload)

    def preview_snapshot(self):
        """Read one immutable JPEG and its identity; no Journal or inference work.

        A preview is display-only, never a health renewal or inspection input.
        Ages use the camera/Worker's Jetson monotonic clock, not browser time.
        """
        with self.lock:
            now = time.monotonic()
            preview = self.preview
            if (not preview or not self.process or not self.process.is_alive()
                    or self.state in ('INIT', 'RECOVERY', 'STOPPED')
                    or preview.get('generation') != self.generation
                    or not 0 <= now - self.preview_received < 2):
                return None
            freshness = dict(preview.get('freshness', {}))
            source = freshness.get('estimated_source_monotonic')
            if (not freshness.get('frame_id') or not isinstance(source, (int, float))
                    or not math.isfinite(source) or not 0 <= now - source < 2):
                return None
            return dict(jpeg=preview['jpeg'], jpeg_no_slots=preview.get('jpeg_no_slots', preview['jpeg']),
                        freshness=freshness, generation=self.generation, worker_state=self.state,
                        frame_age_ms=(now - source) * 1000,
                        received_age_ms=(now - self.preview_received) * 1000)

    def status(self):
        # Snapshot camera/control memory first. A UI capacity/SQL read must not
        # hold Service.lock while a slow Journal operation owns the disk.
        with self.lock:
            value = self._status_snapshot()
        if not self.journal.lock.acquire(blocking=False):
            value.update(ready=False, journal_status='COMMITTING')
            return value
        try:
            storage_error = None
            try:
                self.journal.capacity()
            except OSError as error:
                storage_error = str(error)
            pending_cycles=self.journal.db.execute("SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchone()[0]
            reference=self.journal.db.execute(
                "SELECT inspection_id FROM inspections WHERE cell_id=? "
                "AND json_extract(package_json,'$.manifest_sha256')=? "
                "AND json_extract(request_json,'$.kind')='calibrate' ORDER BY rowid DESC LIMIT 1",
                (value['cell_id'], value['package']['manifest_sha256'])).fetchone()
            value.update(error=value['error'] or storage_error,
                ready=value['ready'] and not storage_error and not pending_cycles,
                latest_reference_inspection_id=reference[0] if reference else None,
                journal_status='AVAILABLE', journal_timing=self.journal.diagnostics.snapshot())
        finally:
            self.journal.lock.release()
        # No Service lock acquisition while Journal is held.
        with self.lock:
            current = self._status_snapshot()
            if (current['plc_session_id'] != value['plc_session_id']
                    or current['package']['manifest_sha256'] != value['package']['manifest_sha256']):
                current.update(ready=False, journal_status='CONTEXT_CHANGED')
            else:
                current.update(error=current['error'] or storage_error,
                    ready=current['ready'] and not storage_error and not pending_cycles,
                    latest_reference_inspection_id=value['latest_reference_inspection_id'],
                    journal_status=value['journal_status'], journal_timing=value['journal_timing'])
            current['health_diagnostics'] = self.health_diagnostics.snapshot()
            self._status_cache = current
            return current

    def _status_snapshot(self):
        """Caller holds Service.lock; process-local state only, no Journal I/O."""
        camera = bool(self.preview and time.monotonic()-self.preview_received < 2 and self.process.is_alive())
        control_idle=self.mock.state in ('IDLE','RECOVERY')
        return {'app_release': self.station.get('app_release', 'app_v007'), 'state': self.state, 'error': self.error,
                'ready': self.state == 'IDLE' and camera and bool(self.calibration) and not self.error and not self.switching and control_idle,
                  'camera_ready': camera, 'worker_pid': self.process.pid, 'worker_alive': self.process.is_alive(),
                  'progress':self.progress if self.active and self.progress and self.progress['inspection_id']==self.active['inspection_id'] else None,
                  'diagnostic_capture':dict(self.diagnostic_capture.value),
                  'scene':self.preview.get('scene') if camera else None,
                'plc_session_id': self.session, 'cell_id': self.station['cell_id'],
                'active_inspection_id': self.active['inspection_id'] if self.active else None,
                'backend': self.backend, 'package': self.package.snapshot(),
                'calibration_confirmed': bool(self.calibration), 'recovery': self.recovery,
                'calibration_source_inspection_id': self.calibration.get('source_inspection_id') if self.calibration else None,
                'latest_reference_inspection_id': None,
                'storage_pending': self.storage_pending is not None,
                'production_admission_pending': getattr(self, 'production_admission_pending', None) is not None,
                'status_sampled_monotonic': time.monotonic(),
                'production_enabled':self.production_enabled,'lab':self.lab.status(),
                'performance':{'camera_fps':None,'camera_fps_status':'SENSOR_FPS_UNMEASURED',
                    'processed_preview_fps':(len(self.preview_times)-1)/(self.preview_times[-1][1]-self.preview_times[0][1]) if camera and len(self.preview_times)>1 and self.preview_times[-1][1]>self.preview_times[0][1] else None,
                    'processed_preview_samples':len(self.preview_times),'latest_inspection_timing':self.latest_timing},
                'mock':self.mock.status(),'pc_sync':{'error':self.sender.error,'last_success':self.sender.last_success} if self.sender else {'state':'NOT_CONFIGURED'}}

    def _camera_ready(self):
        """Caller holds Service.lock; camera check must not query UI/Journal."""
        return bool(self.preview and 0 <= time.monotonic()-self.preview_received < 2
                    and self.process and self.process.is_alive())

    def allocate_request(self):
        with self.lock:
            if getattr(self, 'production_admission_pending', None) is not None:
                raise ConflictError('ADMISSION_PENDING')
            with self.journal.lock,self.journal.db:
                key='request_counter:'+str(self.session)
                row=self.journal.db.execute('SELECT value FROM service_state WHERE key=?',(key,)).fetchone()
                number=int(row[0])+1 if row else 1
                if number>4294967295:raise ConflictError('REQUEST_COUNTER_EXHAUSTED_RESTART_SESSION_REQUIRED')
                self.journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(number)))
                return {'cell_id':self.station['cell_id'],'plc_session_id':self.session,'request_id':number,
                    'cycle_id':number,'attempt':1,'package_sha256':self.package.manifest_hash}

    def prepare_production_admission(self, binding):
        from apps.edge_service.production_admission import prepare
        return prepare(self, binding)

    def activate_production_admission(self, context, saved):
        from apps.edge_service.production_admission import activate
        return activate(self, context, saved)

    def release_production_admission(self, context, reason):
        from apps.edge_service.production_admission import release
        return release(self, context, reason)

    def submit(self, request, *, _lab=False, _production=False):
        # Server receipt time is authoritative; clients cannot supply t0 or an epoch.
        received = time.monotonic()
        from copy import deepcopy
        request = deepcopy(request)
        with self.lock:
            if getattr(self, 'production_admission_pending', None) is not None:
                raise ConflictError('ADMISSION_PENDING')
            # Check old keys before checking busy/session: transport retries return the original job.
            existing = self.journal.find_request(request)
            if existing:
                return self.journal.detail(existing['inspection_id']), False
            if _production:
                if not self.production_enabled or self.production_owner is None or request.get('source_mode')!='PRODUCTION_AUTO' or request['runtime_binding']['runtime_session_id']!=self.production_owner.session_id:
                    raise ConflictError('PRODUCTION_OWNER_REQUIRED')
            elif self.production_owner and self.production_owner.operating:
                raise ConflictError('PRODUCTION_AUTO_OWNS_TRIGGER')
            elif _lab:
                if (self.lab.mode not in ('LAB_AUTO','MOCK_PLC') or request.get('source_mode')!=self.lab.mode
                        or request.get('lab_session_id')!=self.lab.session or request.get('kind')!='inspect'):
                    raise ConflictError('LAB_SESSION_MISMATCH')
            elif self.lab.mode!='MANUAL' or any(k in request for k in ('lab_session_id','source_mode','experiment_policy')) or request.get('control_mode')=='lab':
                raise ConflictError('MODE_OWNS_TRIGGER_OR_FORGED_EXPERIMENT_POLICY')
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
            if not InspectionService._camera_ready(self):
                raise ConflictError('CAMERA_NOT_READY')
            if request['kind'] == 'inspect' and not self.calibration:
                raise ConflictError('CALIBRATION_REQUIRED')
            if request['kind'] == 'calibrate':
                view = request['view_assessment']
                if (view.get('product_identity') != 'human_confirmed' or view.get('alignment_confirmed') is not True
                        or any(view.get('visible_slots', {}).get(s['id']) is not True for s in self.package.recipe['slots'])):
                    raise ConflictError('정상 제품의 배치와 모든 자리 가시성을 사람이 먼저 확인해 주세요.')
            trigger = None
            if self.station.get('fresh_frame'):
                from src.camera.fresh_frame import FreshFrameSelector, TriggerContext
                trigger = TriggerContext(
                    trigger_id=uuid.uuid4().hex, cell_id=request['cell_id'],
                    plc_session_id=request['plc_session_id'], cycle_id=request['cycle_id'], request_id=request['request_id'],
                    trigger_received_monotonic=received,
                    trigger_source='MOCK' if request.get('control_mode') == 'mock' else 'LOCAL_TEST',
                    capture_epoch=self.preview.get('freshness', {}).get('camera_epoch'),
                    deadline_monotonic=received+self.station['inspection_timeout_seconds'])
                # Validate configuration and bound the complete cycle before admitting it.
                selector = FreshFrameSelector(trigger, self.station['fresh_frame'],
                                               self.station['max_frame_age_seconds'], self.station['frame_spacing_seconds'])
                trigger = trigger.to_dict()
            identifier, created = self.journal.admit(request, recorded_package(self.package, self.configuration), trigger=trigger)
            if request['kind'] == 'calibrate':
                self.calibration = None
            accepted = time.monotonic()
            self.active = {'inspection_id': identifier, 'request': request, 'accepted_monotonic': accepted,
                'deadline': accepted + self.station['inspection_timeout_seconds'], 'calibration': self.calibration}
            if _production:
                self.active['production_binding']=dict(request['runtime_binding'],inspection_id=identifier)
                self.active['experiment_policy']={'source_mode':'PRODUCTION_AUTO','session_id':self.production_owner.session_id,
                    'human_acceptance':'PENDING','physical_output_enabled':False,
                    'inspection_motion_mode':self.production_owner.inspection_motion_mode,
                    'capture_zone':self.production_owner.zone}
            if _lab:
                self.active['experiment_policy']={'source_mode':self.lab.mode,'session_id':self.lab.session,
                    'human_acceptance':'PENDING','physical_output_enabled':False,
                    'trigger_reason':request.get('lab_trigger_reason')}
            if trigger:
                self.active['trigger']=trigger
                if _production:
                    # Frame selection still stops at this unchanged deadline. The service
                    # must remain alive long enough to store the resulting REVIEW.
                    self.active['capture_deadline']=selector.deadline
                    self.active['deadline']=trigger['deadline_monotonic']
                else:
                    self.active['deadline']=selector.deadline
            self.cancellation.clear()
            self.state = 'BUSY'
            try:
                self.commands.put_nowait(self.active)
            except queue.Full:
                self._fault('COMMAND_QUEUE_FULL')
                raise ConflictError('COMMAND_QUEUE_FULL')
            return self.journal.detail(identifier), created

    def _result_context_error(self, result):
        """Check session and trigger identity again at the durable publication boundary."""
        if self.active['request']['plc_session_id'] != self.session:
            return 'SESSION_MISMATCH'
        trigger = self.active.get('trigger')
        if trigger and result.get('fresh_frame', {}).get('trigger') != trigger:
            return 'TRIGGER_CONTEXT_MISMATCH'
        if 'durable_admission_monotonic' in self.active:
            from apps.edge_service.production_admission import result_context_error
            return result_context_error(self.active, result, self.station['fresh_frame'])
        return None

    def lab_action(self, action, body):
        with self.lock:
            if action=='stop':
                self.lab.stop()
            elif action=='mode':
                if self.active or getattr(self, 'production_admission_pending', None) is not None or self.switching or self.mock.state not in ('IDLE','RECOVERY'):
                    raise ConflictError('IDLE_REQUIRED')
                if not self.calibration: raise ConflictError('CALIBRATION_REQUIRED')
                if self.production_enabled and body.get('mode')=='MOCK_PLC':
                    raise ConflictError('MOCK_MOVED_TO_PRODUCTION_AUTO_CURRENT_NG_POLARITY')
                self.lab.select(body.get('mode'),body.get('confirmed'),time.monotonic())
            elif action=='reinspect':
                if self.active or getattr(self, 'production_admission_pending', None) is not None: raise ConflictError('BUSY')
                self.lab.reinspect()
            elif action=='resync': self.lab.resync()
            elif action=='request':
                if self.lab.mode!='MOCK_PLC' or type(body.get('value')) is not bool:
                    raise ValueError('MOCK_MODE_AND_BOOL_REQUIRED')
                self.lab.gateway.request=body['value']
                self.lab.tick(time.monotonic(),None,InspectionService._camera_ready(self))
            elif action=='fault':
                if self.lab.mode!='MOCK_PLC': raise ValueError('MOCK_MODE_REQUIRED')
                fault=body.get('kind')
                if fault in ('disconnect','reconnect'): self.lab.gateway.connected=fault=='reconnect'
                elif fault in ('result_fail','done_fail','done_unknown'):
                    setattr(self.lab.gateway,'unknown_next' if fault=='done_unknown' else 'fail_next',
                            'Jetson_Result' if fault=='result_fail' else 'Jetson_Done')
                else: raise ValueError('INVALID_MOCK_FAULT')
                self.lab.tick(time.monotonic(),None,InspectionService._camera_ready(self))
            else: raise ValueError('UNKNOWN_LAB_ACTION')
            return self.lab.status()

    def live_control(self, action):
        with self.lock:
            if self.active or getattr(self, 'production_admission_pending', None) is not None: raise ConflictError('CANCEL_INSPECTION_AND_WAIT_FIRST')
            if action=='stop':
                self.lab.stop()
                self._stop_worker()
                self.preview=None
                self.state='STOPPED'
            elif action=='start':
                if self.state not in ('STOPPED','RECOVERY'): return {'state':self.state}
                self.lab.stop()
                self._stop_worker()
                self.session=self.journal.new_session(self.station['cell_id'])
                self._launch()
            else: raise ValueError('UNKNOWN_LIVE_ACTION')
            return {'state':self.state}

    def cancel(self, identifier):
        with self.lock:
            if self.active and self.active['inspection_id'] == identifier:
                self.cancellation.set()
                if self.storage_pending is None:
                    self.journal.cancel(identifier, 'USER_CANCELLED')
                self.state = 'CANCELLING'
            return None if self.storage_pending else self.journal.detail(identifier)

    def confirm_calibration(self, identifier, confirmed):
        with self.lock:
            if confirmed is not True or self.state != 'IDLE' or self.lab.mode!='MANUAL':
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

    def activate(self, package_root, auto_profile=None):
        candidate = load_package(package_root)
        if self.production_enabled:
            validate_package_settings(candidate)
        if self.station.get('auto_profile'):
            from src.runtime.auto_profile import validate_profile
            validate_profile(auto_profile or self.station['auto_profile'],candidate)
        with self.lock:
            if self.active or getattr(self, 'production_admission_pending', None) is not None or self.lab.mode!='MANUAL' or self.state not in ('IDLE', 'RECOVERY') or self.switching or self.mock.state not in ('IDLE','RECOVERY'):
                raise ConflictError('IDLE_REQUIRED')
            with self.journal.lock:
                pending=self.journal.db.execute("SELECT count(*) FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchone()[0]
            if pending:raise ConflictError('UNFINISHED_CYCLE_RECOVERY_REQUIRED')
            self.switching=True
            previous = self.package
            previous_station = self.station
            self._stop_worker()
            if auto_profile is not None:
                self.station=dict(self.station,auto_profile=auto_profile)
            self.package = candidate
            self.calibration = self._load_calibration()
            self.session = self.journal.new_session(self.station['cell_id'])
            self._launch()
        deadline = time.monotonic() + self.station.get('startup_timeout_seconds',parameters.STARTUP_TIMEOUT_SECONDS)
        while time.monotonic() < deadline:
            with self.lock:
                state = self.state
            # Model READY precedes the first preview. Recovery must wait for a
            # current camera frame before reporting activation success.
            if state == 'IDLE' and self.status()['camera_ready']:
                with self.lock,self.journal.lock,self.journal.db:
                    self.journal.db.execute("INSERT INTO service_state VALUES ('active_package',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(str(candidate.root),))
                    if self.station.get('auto_profile'):
                        self.journal.db.execute("INSERT INTO service_state VALUES ('active_auto_profile',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(self.station['auto_profile']),))
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
            self.station = previous_station
            self.calibration = self._load_calibration()
            self.session = self.journal.new_session(self.station['cell_id'])
            self._launch()
        deadline = time.monotonic() + self.station.get('startup_timeout_seconds',parameters.STARTUP_TIMEOUT_SECONDS)
        while time.monotonic() < deadline and self.state == 'INIT':
            time.sleep(.05)
        with self.lock,self.journal.lock,self.journal.db:
            self.switching=False
            self.journal._event('PACKAGE_ACTIVATION_FAILED',{'reason':failure,'previous_restored':self.state=='IDLE','previous_manifest_sha256':previous.manifest_hash})
        return {'activated':False,'reason':failure,'previous_restored':self.state == 'IDLE'}

    def close(self):
        if self.close_complete:return
        # 저장 오류 때문에 Worker/카메라 종료가 건너뛰어지지 않도록 각 소유 자원을 정리한다.
        errors = []
        resource_errors = []
        def cleanup(name, action):
            try:
                action()
            except Exception as error:
                resource_errors.append(name + ': ' + str(error))
        if self.sender:cleanup('sender', self.sender.close)
        self.closed.set()
        self.monitor.join(5)
        if self.monitor.is_alive():resource_errors.append('MONITOR_STOP_UNCONFIRMED')
        # Stop the camera even if storage hangs. Never close a DB still owned
        # by the durability thread, or launch a replacement camera over it.
        self.cancellation.set()
        cleanup('worker', self._stop_worker)
        cleanup('storage', self.storage.close)
        if self.storage.thread.is_alive():
            cleanup('diagnostic_capture', self.diagnostic_capture.close)
            cleanup('manager', self.manager.shutdown)
            raise RuntimeError('; '.join(resource_errors))
        with self.lock:
            if self.active:
                try:
                    self.journal.cancel(self.active['inspection_id'], 'SERVICE_SHUTDOWN')
                except Exception as error:
                    errors.append('SHUTDOWN_JOURNAL_CANCEL: ' + str(error))
            cleanup('diagnostic_capture', self.diagnostic_capture.close)
            cleanup('journal', self.journal.close)
            cleanup('manager', self.manager.shutdown)
            self.close_complete = not resource_errors
        if errors or resource_errors:
            raise RuntimeError('; '.join(errors + resource_errors))
