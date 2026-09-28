"""기존 소유 객체를 직렬 연결한다. 결과 확인 thread와 종료 소유자는 각각 하나다."""
from copy import deepcopy
import threading
import time
import logging
import uuid

from src.runtime.contracts import CycleStart
from src.runtime.inspection_bridge import InspectionBridge
from src.runtime.cell_supervisor import CellSupervisor
from src.runtime.vision_coordinator import VisionRuntimeCoordinator
from src.observation.contracts import ProviderStatus


class IntegratedRuntime:
    def __init__(self, service, coordinator, observation, plc, log_owner, tracker_config, recovery_policy):
        self.service, self.coordinator = service, coordinator
        self.observation, self.plc = observation, plc
        self.session_id = coordinator.runtime_session_id
        self.application_id = uuid.uuid4().hex
        self.tracker_config = tracker_config
        self.supervisor = CellSupervisor(service,plc,recovery_policy)
        self.log_owner = log_owner
        self.logger = logging.getLogger(__name__)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.closed = False
        self.closing = False
        self.error = None
        self.snapshot = None
        self.sequence = 0
        self.view = None
        self.service_identity = None
        self.last_clearance = None
        self.reported_service_fault = None
        self.bridge = InspectionBridge(service,coordinator)
        self.thread = threading.Thread(target=self._run,name='runtime-completion',daemon=True)
        self.thread.start()

    def _available(self):
        if self.closed or self.closing:
            raise ValueError('RUNTIME_CLOSED')
        if self.error:
            raise ValueError('RUNTIME_HOLD: '+self.error)

    def _context(self):
        active = self.coordinator.active_cycle
        request = self.bridge.request or {}
        return {'application_id':self.application_id,'runtime_session_id':self.session_id,
            'cycle_id':active.cycle_id if active else (self.snapshot.cycle_id if self.snapshot else None),
            'track_id':self.snapshot.track_id if self.snapshot else None,
            'request_id':request.get('request_id'),'inspection_id':self.bridge.inspection_id,
            'request_identity':{key:request.get(key) for key in ('cell_id','plc_session_id','request_id')}}

    def _cycle_fault(self, code, reason, subsystem):
        self.error = str(reason)
        self.supervisor.fault(self._context(),code,reason,subsystem)

    def _runtime_state(self, service):
        if (self.closed or self.closing or self.supervisor.alarm or service.get('error')
                or service['state'] in ('INIT','RECOVERY','CLOSED') or not self.plc.status()['available']):
            return 'NOT_READY'
        if self.supervisor.cycle_error or self.error:
            return 'DEGRADED'
        if self.coordinator.active_cycle:
            return 'RUNNING'
        return 'READY' if service.get('ready') else 'NOT_READY'

    def _identity(self, session, cycle):
        self._available()
        active = self.coordinator.active_cycle
        if session != self.session_id:
            raise ValueError('SESSION_MISMATCH')
        if active is None or active.cycle_id != cycle:
            raise ValueError('CYCLE_MISMATCH')
        if self.service_identity != (self.service.session,self.service.package.manifest_hash):
            self.error = 'SERVICE_SESSION_OR_PACKAGE_CHANGED'
            raise ValueError(self.error)

    def start_cycle(self, runtime_session_id, cycle_id, view_assessment):
        with self.lock, self.service.lock:
            self._available()
            if self.supervisor.alarm:
                raise ValueError('NOT_READY: '+self.supervisor.alarm)
            if runtime_session_id != self.session_id:
                raise ValueError('SESSION_MISMATCH')
            if self.coordinator.active_cycle is not None:
                raise ValueError('ACTIVE_CYCLE_EXISTS')
            if not isinstance(view_assessment,dict):
                raise ValueError('VIEW_ASSESSMENT_REQUIRED')
            if not self.service.status()['ready'] or not self.plc.status()['available']:
                raise ValueError('INSPECTION_SERVICE_OR_PLC_NOT_READY')
            self.snapshot = self.coordinator.start_cycle(CycleStart(runtime_session_id,cycle_id))
            self.view = deepcopy(view_assessment)
            self.service_identity = (self.service.session,self.service.package.manifest_hash)
            self.bridge = InspectionBridge(self.service,self.coordinator)
            self.last_clearance = None
            return self.status()

    def _route(self, payload, evidence=None):
        try:
            provider = self.observation.observe(payload)
            self.sequence += 1
            self.snapshot = self.coordinator.route(f'manual-{self.sequence}',self.sequence,
                                                    time.monotonic(),provider,evidence)
            if self.snapshot.tracker_state_after.value == 'LOST':
                if self.bridge.inspection_id:
                    self.service.cancel(self.bridge.inspection_id)
                self._cycle_fault('TRACKING_LOST',str(self.snapshot.reason),'tracking')
            if self.snapshot.inspection_event:
                self.bridge.submit_window(self.snapshot.inspection_event,self.snapshot.cycle_id,self.view)
            if self.snapshot.cycle_retired:
                # 기존 Journal 재사용. 검사 cycle의 INSPECTION_ONLY와 추적 cycle 완료는 다르다.
                with self.service.lock,self.service.journal.lock,self.service.journal.db:
                    self.service.journal._event('RUNTIME_CYCLE_RETIRED',{
                        'runtime_session_id':self.session_id,'cycle_id':self.snapshot.cycle_id,
                        'track_id':self.snapshot.track_id,'inspection_id':self.snapshot.inspection_id,
                        'authority':'MANUAL_DIAGNOSTIC_CLEARANCE','physical_acceptance':False})
                self.supervisor.finish(self._context(),self.bridge.decision,'COMPLETE')
        except Exception as error:
            self.error = f'{type(error).__name__}: {error}'
            self.logger.exception('통합 호출 실패; API는 유지하고 cycle을 HOLD session=%s',self.session_id)
            if self.supervisor.cycle_error is None:
                self._cycle_fault('OBSERVATION_OR_ROUTING_ERROR',self.error,'observation')
            raise
        return self.status()

    def observe(self, runtime_session_id, cycle_id, observation):
        with self.lock,self.service.lock:
            self._identity(runtime_session_id,cycle_id)
            return self._route(observation)

    def clearance(self, runtime_session_id, cycle_id, track_id, evidence_id, source_epoch,
                  source_sequence, confirmed_clear, observation):
        with self.lock,self.service.lock:
            self._identity(runtime_session_id,cycle_id)
            if self.snapshot is None or self.snapshot.track_id != track_id:
                raise ValueError('TRACK_MISMATCH')
            if self.snapshot.tracker_state_after.value != 'CLEARING':
                raise ValueError('CLEARING_REQUIRED')
            evidence = self.plc.clearance(runtime_session_id=runtime_session_id,cycle_id=cycle_id,
                track_id=track_id,evidence_id=evidence_id,source_epoch=source_epoch,
                source_sequence=source_sequence,confirmed_clear=confirmed_clear)
            self.last_clearance = {'authority':'MANUAL_DIAGNOSTIC_CLEARANCE','evidence':evidence.to_dict()}
            return self._route(observation,evidence)

    def _replace_tracking_session(self, session_id):
        """상위 명시적 복구 뒤에만 호출. 기존 H6/G를 reset하거나 내부 필드를 바꾸지 않는다."""
        self.coordinator = VisionRuntimeCoordinator(session_id,self.tracker_config)
        self.session_id = session_id
        self.bridge = InspectionBridge(self.service,self.coordinator)
        self.snapshot = None
        self.sequence = 0
        self.view = None
        self.service_identity = None
        self.error = None

    def recover_cycle(self, runtime_session_id, cycle_id, track_id, evidence_id, source_epoch,
                      source_sequence, confirmed_clear, observation):
        """오류 cycle만 명시 clearance + durable abort 후 교체한다. Service/Worker는 유지한다."""
        with self.lock,self.service.lock:
            if self.closed or self.closing:
                raise ValueError('RUNTIME_CLOSED')
            active = self.coordinator.active_cycle
            if runtime_session_id != self.session_id:
                raise ValueError('SESSION_MISMATCH')
            if active is None or active.cycle_id != cycle_id:
                raise ValueError('CYCLE_MISMATCH')
            actual_track = self.snapshot.track_id if self.snapshot else None
            if track_id != actual_track:
                raise ValueError('TRACK_MISMATCH')
            if self.supervisor.cycle_error is None:
                raise ValueError('CYCLE_ERROR_REQUIRED')
            if self.service.active is not None:
                raise ValueError('INSPECTION_STILL_ACTIVE')
            if evidence_id in self.supervisor.recovery_evidence_ids:
                raise ValueError('RECOVERY_EVIDENCE_REPLAY')
            provider = self.observation.observe(observation)
            if provider.status != ProviderStatus.NO_FOREGROUND:
                raise ValueError('RECOVERY_CLEARANCE_CONFLICT_OR_AMBIGUOUS')
            evidence = self.plc.recovery_clearance(runtime_session_id=runtime_session_id,cycle_id=cycle_id,
                track_id=track_id,evidence_id=evidence_id,source_epoch=source_epoch,
                source_sequence=source_sequence,confirmed_clear=confirmed_clear)
            context = self._context()
            replacement = uuid.uuid4().hex
            # 저장 실패 시 아래 교체 지점에 도달하지 않는다. 기존 LOST/ERROR identity를 보존한다.
            self.service.journal.capacity()
            self.supervisor.audit('CELL_CYCLE_ABORTED',context,decision='ERROR',
                reason=self.supervisor.cycle_error['reason'],runtime_state='DEGRADED',
                recovery_action='EXPLICIT_CLEARANCE_NEW_TRACKING_SESSION',
                plc_disposition='ERROR',clearance=evidence,new_runtime_session_id=replacement)
            self.supervisor.recovery_evidence_ids.add(evidence_id)
            self.supervisor.finish(context,'ERROR','ABORTED')
            self.last_clearance = evidence
            self._replace_tracking_session(replacement)
            return self.status()

    def recover_infrastructure(self, actor, reason):
        """운영자의 요청 한 번에 기존 Service activation을 최대 한 번 호출한다. 자동 retry는 없다."""
        from src.tracking.contracts import require_text
        require_text(actor,'actor')
        require_text(reason,'reason')
        with self.lock:
            if self.closed or self.closing:
                raise ValueError('RUNTIME_CLOSED')
            if self.coordinator.active_cycle is not None:
                raise ValueError('DISPOSE_ACTIVE_CYCLE_FIRST')
            limit = self.supervisor.policy.recovery_attempt_limit
            if limit is not None and self.supervisor.recovery_attempts >= limit:
                raise ValueError('RECOVERY_ATTEMPT_LIMIT')
            self.service.journal.capacity()
            self.supervisor.recovery_attempts += 1
            context = self._context()
            self.supervisor.audit('CELL_RECOVERY_ATTEMPT',context,decision=None,reason=reason,
                runtime_state='NOT_READY',recovery_action='ONE_EXPLICIT_ATTEMPT',plc_disposition=None,actor=actor)
            service = self.service.status()
            if service['state'] != 'IDLE' or not service['worker_alive'] or not service['camera_ready']:
                result = self.service.activate(self.service.package.root)
                if not result['activated']:
                    self.supervisor.alarm = 'INFRASTRUCTURE_RECOVERY_FAILED'
                    self.supervisor.audit('CELL_RECOVERY_FAILED',context,decision=None,
                        reason=result.get('reason'),runtime_state='NOT_READY',recovery_action='STOP_RETRY',plc_disposition=None)
                    return self.status()
            if not self.service.status()['ready'] or not self.plc.status()['available']:
                self.supervisor.alarm = 'INFRASTRUCTURE_NOT_READY'
                return self.status()
            replacement = uuid.uuid4().hex
            self.supervisor.audit('CELL_RECOVERY_VERIFIED',context,decision=None,reason=reason,
                runtime_state='READY',recovery_action='NEW_TRACKING_SESSION',plc_disposition=None,
                actor=actor,new_runtime_session_id=replacement)
            self._replace_tracking_session(replacement)
            self.supervisor.alarm = None
            self.supervisor.error_counts.clear()
            self.supervisor.recovery_attempts = 0
            return self.status()

    def _run(self):
        while not self.stop.wait(.03):
            with self.lock:
                if self.error or self.closing:
                    continue
                try:
                    with self.service.lock:
                        if self.service.state == 'RECOVERY':
                            fault = (self.service.generation,self.service.error)
                            if fault != self.reported_service_fault:
                                self.reported_service_fault = fault
                                if self.coordinator.active_cycle:
                                    self._cycle_fault('SERVICE_RECOVERY',self.service.error,'worker')
                                else:
                                    self.supervisor.audit('CELL_RUNTIME_FAULT',self._context(),decision=None,
                                        error_code='SERVICE_RECOVERY',reason=self.service.error,
                                        runtime_state='NOT_READY',recovery_action='WAIT_EXPLICIT_RECOVERY',
                                        plc_disposition=None)
                            continue
                    updated = self.bridge.poll()
                    if updated:
                        self.snapshot = updated
                        row = self.service.journal.detail(self.bridge.inspection_id)
                        self.supervisor.disposition(self._context(),self.bridge.decision,
                            (row.get('result') or {}).get('reason',''))
                    if self.bridge.error:
                        self._cycle_fault('INSPECTION_ERROR',self.bridge.error,'inspection')
                        self.logger.error('검사 HOLD session=%s inspection=%s: %s',
                            self.session_id,self.bridge.inspection_id,self.error)
                except Exception as error:
                    self.error = f'{type(error).__name__}: {error}'
                    self.logger.exception('결과 연결 실패; completion thread와 API 유지 session=%s',self.session_id)
                    try:
                        self._cycle_fault('RESULT_CONNECTION_ERROR',self.error,'inspection')
                    except Exception:
                        self.logger.exception('cycle 오류 기록 실패; NOT_READY 유지')

    def status(self):
        with self.lock:
            try:
                service = self.service.status() if not self.closed else {'state':'CLOSED'}
            except Exception as error:
                # 저장소 조회 자체가 실패해도 상태 endpoint는 남겨 둔다.
                service = {'state':'RECOVERY','ready':False,'error':f'STATUS_UNAVAILABLE: {error}',
                    'worker_pid':self.service.process.pid,'worker_alive':self.service.process.is_alive(),
                    'camera_ready':False}
            tracking = self.snapshot.to_dict() if self.snapshot else {'coordinator_state':'NO_ACTIVE_CYCLE',
                'track_id':None,'inspection_id':None,'cycle_id':None,'tracker_state_after':'IDLE'}
            return {'runtime_session_id':self.session_id,'mode':'mock','acceptance':'SOFTWARE_INTEGRATION_BASELINE',
                'application_id':self.application_id,'runtime_state':self._runtime_state(service),
                'last_cycle':deepcopy(self.supervisor.last_cycle),'alarm':self.supervisor.alarm,
                'supervisor':self.supervisor.status(),
                'production_acceptance':False,'error':self.error,'closed':self.closed,
                'error_log':str(self.log_owner.path),
                'stopped_at':self.error or self.bridge.error or (service.get('error')) or
                    (tracking['coordinator_state'] if service.get('ready') else service['state']),
                'inspection_service':service,'camera':{'ready':service.get('camera_ready',False)},
                'worker':{'pid':service.get('worker_pid'),'alive':service.get('worker_alive',False)},
                'package':service.get('package'),'tracking':tracking,
                'active_cycle':self.coordinator.active_cycle.to_dict() if self.coordinator.active_cycle else None,
                'inspection':self.bridge.status(),'clearance':deepcopy(self.last_clearance),
                'observation':{'adapter':self.observation.label,'status':'TEMPORARY_INTEGRATION_ADAPTER'},
                'journal':{'status':'CLOSED' if self.closed else 'OPEN',
                    'path':str(self.service.journal.root/'journal.sqlite3'),
                    'storage_error':service.get('error'),'durability':'SQLite WAL / synchronous FULL'},
                'ownership':{'normal_runtime_device':'JETSON_ORIN_NANO','laptop_required':False,
                    'camera_owner':'inspection_worker process','journal_owner':'InspectionService'},
                'plc':self.plc.status()}

    def close(self):
        with self.lock:
            if self.closed or self.closing:
                return
            self.closing = True
            self.stop.set()
        self.thread.join(5)
        errors = []
        for resource in (self.observation,self.plc,self.service):
            try:
                resource.close()
            except Exception as error:
                errors.append(str(error))
        with self.lock:
            self.closed = not errors and not self.thread.is_alive()
            self.error = '; '.join(errors) if errors else self.error
        if errors:
            self.logger.error('종료 중 오류: %s',self.error)
        self.log_owner.close()
        if not self.closed:
            raise RuntimeError('RUNTIME_SHUTDOWN_UNCONFIRMED: '+str(self.error))
