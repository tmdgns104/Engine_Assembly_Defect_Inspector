"""단일 제품 자동 운전 감독. 추적/검사/저장은 기존 소유 객체에 위임한다."""
from collections import deque
from dataclasses import asdict
import json
import queue
import time
import uuid

from src.runtime.integrated import IntegratedRuntime
from src.runtime.auto_exit import VisionExitPolicy
from src.runtime.inspection_bridge import InspectionBridge
from src.runtime.contracts import CycleStart
from src.integration.clearance import VisionExitEvidence
from src.integration.cycle_track_binding import BoundClearanceEvidence
from src.vision.auto_inspection import box_values
from src.observation.contracts import ProviderStatus


class AutomaticRuntime(IntegratedRuntime):
    def __init__(self, *args, profile, **kwargs):
        self.profile = profile
        self.operating = False
        self.armed = False
        self.empty_since = None
        self.latest_packet = None
        self.last_packet_received = None
        self.last_sequence = -1
        self.camera_epoch = None
        self.history = deque(maxlen=100)
        self.passage_id = None
        self.passage_count = 0
        self.last_observed = None
        self.phase = '운전 준비'
        self.identity_uncertain = False
        self.exit_policy = VisionExitPolicy(exit_y=profile['exit_y'],min_empty_frames=profile['empty_frames'],
            min_empty_seconds=profile['empty_seconds'],max_frame_gap=profile['max_frame_gap'])
        super().__init__(*args,**kwargs)
        self.logger.setLevel('INFO')

    def start_auto(self):
        with self.lock:
            self._available()
            if self.coordinator.active_cycle or not self.service.status()['ready'] or self.supervisor.alarm:
                raise ValueError('AUTO_NOT_READY')
            if not self.latest_packet or time.monotonic()-self.last_packet_received > self.profile['observation_stale_seconds']:
                raise ValueError('AUTO_OBSERVATION_NOT_READY')
            if self.latest_packet['package_sha256'] != self.service.package.manifest_hash:
                raise ValueError('AUTO_PACKAGE_PROFILE_MISMATCH')
            if not self.latest_packet['integrity']['valid'] or self.latest_packet['provider'] is None:
                raise ValueError('AUTO_INPUT_INTEGRITY_NOT_READY')
            self.operating = True
            self.armed = False
            self.empty_since = None
            self.phase = '빈 진입 영역 확인'
            self.supervisor.audit('AUTO_STARTED',self._context(),profile=self.profile)
            return self.status()

    def stop_auto(self):
        with self.lock:
            # 현재 제품은 계속 추적/저장/이탈 처리하되 새 제품을 받지 않는다.
            self.operating = False
            self.supervisor.audit('AUTO_STOP_REQUESTED',self._context())
            return self.status()

    def recover_empty_area(self, actor, reason, area_checked_empty):
        """불확실한 제품 교체/장치 장애용 예외 복구. 정상 제품 경로에서는 사용하지 않는다."""
        from src.tracking.contracts import require_text
        require_text(actor,'actor');require_text(reason,'reason')
        with self.lock:
            if self.operating or area_checked_empty is not True:
                raise ValueError('STOP_AND_EXPLICIT_EMPTY_AREA_CHECK_REQUIRED')
            if self.supervisor.cycle_error is None or self.service.active:
                raise ValueError('INACTIVE_INSPECTION_AND_CYCLE_ERROR_REQUIRED')
            self.service.journal.capacity()
            context=self._context()
            self.supervisor.audit('AUTO_OPERATOR_EXCEPTION_RECOVERY',context,actor=actor,reason=reason,
                source='OPERATOR_RECOVERY_EMPTY_AREA',physical_clearance_verified=False,
                recovery_action='ABORT_UNCERTAIN_CYCLE_AND_REINITIALIZE')
            self.supervisor.finish(context,'ERROR','ABORTED')
            self.history.append(dict(self.supervisor.last_cycle,passage_id=self.passage_id,
                clearance={'source':'OPERATOR_RECOVERY_EMPTY_AREA','physical_clearance_verified':False}))
            self._replace_tracking_session(uuid.uuid4().hex)
            self.identity_uncertain=False
            self.armed=False
            self.empty_since=None
            self.exit_policy.reset()
            self.phase='장치/정상 기준 확인 후 재시작 필요'
            return self.status()

    def activate_profile(self, package_root, profile):
        from src.recipe.package import load_package
        from src.runtime.auto_profile import validate_profile
        from src.runtime.cell_supervisor import FaultPolicy
        with self.lock:
            if self.operating or self.coordinator.active_cycle or self.service.active:
                raise ValueError('AUTO_IDLE_REQUIRED_FOR_PROFILE_CHANGE')
            try:
                config=validate_profile(profile,load_package(package_root))
            except Exception as error:
                self.supervisor.audit('AUTO_PROFILE_REJECTED',self._context(),reason=str(error))
                raise
            result=self.service.activate(package_root,auto_profile=profile)
            if result['activated']:
                self.profile=profile
                self.tracker_config=config
                self.supervisor.policy=FaultPolicy(profile['consecutive_error_limit'],profile['recovery_attempt_limit'])
                self.exit_policy=VisionExitPolicy(exit_y=profile['exit_y'],min_empty_frames=profile['empty_frames'],
                    min_empty_seconds=profile['empty_seconds'],max_frame_gap=profile['max_frame_gap'])
            self._replace_tracking_session(uuid.uuid4().hex)
            self.latest_packet=None
            self.last_packet_received=None
            self.camera_epoch=None
            self.armed=False
            self.phase='정상 기준 확인 필요'
            self.supervisor.audit('AUTO_PROFILE_ACTIVATION_RESULT',self._context(),result=result)
            return result

    def start_cycle(self, *args, **kwargs):
        raise ValueError('AUTO_PER_PRODUCT_MANUAL_CONTROL_FORBIDDEN')
    observe = start_cycle
    clearance = start_cycle
    recover_cycle = start_cycle

    def _new_passage(self, packet):
        self.passage_count += 1
        self.passage_id = f'{self.application_id[:8]}-{self.passage_count:06d}'
        self.snapshot = self.coordinator.start_cycle(CycleStart(self.session_id,self.passage_id))
        self.service_identity = (self.service.session,self.service.package.manifest_hash)
        self.bridge = InspectionBridge(self.service,self.coordinator)
        self.last_clearance = None
        self.exit_policy.reset()
        self.last_observed = None
        self.identity_uncertain = False
        self.supervisor.audit('AUTO_PRODUCT_ENTERED',self._context(),passage_id=self.passage_id,
            frame_id=packet['frame_id'],sequence=packet['sequence'],package_sha256=packet['package_sha256'])

    def _complete(self, evidence, aborted=False):
        context = self._context()
        decision = 'ERROR' if aborted else self.bridge.decision
        # 감사 commit 실패 시 ID 폐기/교체 또는 다음 제품 준비를 하지 않는다.
        self.supervisor.audit('AUTO_CYCLE_ABORTED' if aborted else 'AUTO_CYCLE_COMPLETE',context,
            decision=decision,clearance=evidence,physical_clearance_verified=False,
            recovery_action='NEW_TRACKING_SESSION' if aborted else 'NEXT_ENTRY')
        self.supervisor.finish(context,decision,'ABORTED' if aborted else 'COMPLETE')
        self.history.append(dict(self.supervisor.last_cycle,passage_id=self.passage_id,clearance=evidence))
        self.last_clearance = evidence
        if aborted:
            self._replace_tracking_session(uuid.uuid4().hex)
        self.armed = True
        self.last_observed = None
        self.phase = '제품 대기' if self.operating else '운전 정지'

    def _packet(self, packet):
        if packet['generation'] != self.service.generation:
            return
        if self.camera_epoch != packet['camera_epoch']:
            if self.coordinator.active_cycle:
                self._cycle_fault('CAMERA_EPOCH_CHANGED','카메라 epoch가 바뀌었습니다','camera')
            self.camera_epoch = packet['camera_epoch']
            self.last_sequence = -1
            self.armed = False
            self.empty_since = None
        if packet['sequence'] <= self.last_sequence:
            return
        self.last_sequence = packet['sequence']
        self.latest_packet = packet
        self.last_packet_received = time.monotonic()
        healthy = (packet['integrity']['valid'] and packet['provider'] is not None and
                   packet['provider']['status'] != 'AMBIGUOUS_FOREGROUND' and
                   time.monotonic()-packet['monotonic_s'] <= self.profile['observation_stale_seconds'])
        bbox = box_values(packet['provider']['observations'][0]['bbox']) if healthy and packet['provider']['observations'] else None
        active = self.coordinator.active_cycle is not None
        if not healthy:
            self.empty_since = None
            self.exit_policy.update(packet['sequence'],packet['monotonic_s'],None,False)
            self.phase = '관측 불확실'
            if active and packet['provider'] and packet['provider']['total_components'] > 1:
                self.identity_uncertain = True
                self.exit_policy.reset()
                self._cycle_fault('MULTIPLE_PRODUCTS','복수 제품은 단일 활성 제품 운전 범위 밖입니다','observation')
            elif active and self.last_observed and packet['monotonic_s']-self.last_observed['monotonic_s'] > self.profile['max_unobserved_seconds']:
                self.identity_uncertain=True
                self._cycle_fault('OBSERVATION_GAP_EXCEEDED','장기 관측 불확실: 동일 제품 재연결 근거가 없습니다','observation')
            return
        if not active:
            if not self.operating:
                return
            if not self.armed:
                if bbox is None:
                    self.empty_since = self.empty_since if self.empty_since is not None else packet['monotonic_s']
                    if packet['monotonic_s']-self.empty_since >= self.profile['initial_empty_seconds']:
                        self.armed = True
                        self.phase = '제품 대기'
                else:
                    self.empty_since = None
                    self.phase = '시작 영역 비우기 필요'
                return
            if bbox is None:
                return
            center = [(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2]
            x1,_,x2,_ = self.profile['inspection_window']
            if not center[1] <= self.profile['entry_y'] or not x1 <= center[0] <= x2:
                self.armed = False
                self.empty_since = None
                self.phase = '역진입/진입 영역 밖: 영역 비우기 필요'
                return
            if not self.service.status()['ready'] or self.supervisor.alarm:
                self.phase = '운전 불가'
                return
            self._new_passage(packet)
        if self.service_identity != (self.service.session,self.service.package.manifest_hash):
            self._cycle_fault('SERVICE_IDENTITY_CHANGED','활성 제품의 Service/package가 변경되었습니다','worker')
            return
        # LOST 이후 새 박스로 이전 제품의 출구 이력을 만들지 않는다.
        lost = self.snapshot and self.snapshot.tracker_state_after.value == 'LOST'
        exit_evidence = self.exit_policy.update(packet['sequence'],packet['monotonic_s'],bbox,
                                                healthy and not self.identity_uncertain and not (lost and bbox is not None))
        provider = self.observation.observe(packet)
        if self.error:
            if exit_evidence and self.service.active is None:
                self._complete(exit_evidence,aborted=True)
            return
        evidence = None
        if exit_evidence and self.snapshot and self.snapshot.tracker_state_after.value == 'CLEARING':
            authority = VisionExitEvidence(packet['camera_epoch'],exit_evidence['exit_observation']['sequence'],
                tuple(exit_evidence['empty_sequences']),exit_evidence['exit_observation']['monotonic_s'],packet['monotonic_s'])
            evidence = BoundClearanceEvidence(self.session_id,self.coordinator.active_cycle.cycle_id,
                self.snapshot.track_id,uuid.uuid4().hex,packet['camera_epoch'],packet['sequence'],authority)
        self.snapshot = self.coordinator.route(packet['frame_id'],packet['sequence'],packet['monotonic_s'],provider,evidence)
        state = self.snapshot.tracker_state_after.value
        if bbox is not None and state != 'LOST':
            self.last_observed = {'frame_id':packet['frame_id'],'bbox':bbox,'monotonic_s':packet['monotonic_s']}
        if state == 'LOST':
            if self.bridge.inspection_id and self.service.active:
                self.service.cancel(self.bridge.inspection_id)
            self._cycle_fault('TRACKING_LOST',str(self.snapshot.reason),'tracking')
        if self.snapshot.inspection_event:
            binding = {'sequence':packet['sequence'],'monotonic_s':packet['monotonic_s'],
                'bbox':bbox,'frame_id':packet['frame_id'],'camera_epoch':packet['camera_epoch'],
                'package_sha256':packet['package_sha256'],'passage_id':self.passage_id,
                'inspection_window':self.profile['inspection_window']}
            self.bridge.submit_window(self.snapshot.inspection_event,self.snapshot.cycle_id,{},binding)
        if self.snapshot.cycle_retired:
            self._complete(asdict(evidence))
        else:
            self.phase = ('일시 미관측' if bbox is None else
                {'TRACKING':'현재 추적','INSPECTION_READY':'검사 중','INSPECTED':'결과 확정',
                 'CLEARING':'출구 확인','LOST':'동일성 불확실: 복구 필요'}.get(state,state))

    def _poll_result(self):
        if self.error:
            return
        updated = self.bridge.poll()
        if updated:
            self.snapshot = updated
            row = self.service.journal.detail(self.bridge.inspection_id)
            self.supervisor.disposition(self._context(),self.bridge.decision,(row.get('result') or {}).get('reason',''))
        if self.bridge.error:
            self._cycle_fault('INSPECTION_ERROR',self.bridge.error,'inspection')

    def _run(self):
        while not self.stop.wait(.02):
            with self.lock:
                if self.closing:
                    continue
                try:
                    with self.service.lock:
                        self._poll_result()
                        while True:
                            try:
                                packet = self.service.products.get_nowait()
                            except queue.Empty:
                                break
                            self._packet(packet)
                            # 원본 frame identity/시각과 제품 상태의 연결. 이미지는 별도 Evidence 소유다.
                            self.logger.info(json.dumps(dict(event='AUTO_FRAME',context=self._context(),
                                packet=packet,phase=self.phase),ensure_ascii=False))
                        stale = self.last_packet_received is not None and time.monotonic()-self.last_packet_received > self.profile['observation_stale_seconds']
                        if self.service.state == 'RECOVERY' or stale:
                            self.phase = '운전 불가: 프레임/장치 복구 필요'
                            if self.coordinator.active_cycle and not self.error:
                                self._cycle_fault('FRAME_STREAM_UNAVAILABLE',self.service.error or 'OBSERVATION_STALE','camera')
                except Exception as error:
                    self.logger.exception('AUTO 처리 오류; 상태 API와 감독 thread 유지')
                    self.phase = '운전 불가: 오류 기록 확인'
                    try:
                        if self.coordinator.active_cycle:
                            self._cycle_fault('AUTO_RUNTIME_ERROR',str(error),'runtime')
                        else:
                            self.supervisor.alarm = str(error)
                    except Exception:
                        self.supervisor.alarm = 'JOURNAL_UNAVAILABLE'

    def status(self):
        value = super().status()
        packet = self.latest_packet
        stale = packet is None or self.last_packet_received is None or time.monotonic()-self.last_packet_received > self.profile['observation_stale_seconds']
        if stale or (packet and not packet['integrity']['valid']):
            value['runtime_state'] = 'NOT_READY'
        value.update(mode='auto',acceptance='ACTUAL_HCAM_VALIDATION_PENDING',operating=self.operating,
            phase=self.phase,passage_id=self.passage_id,passage_count=self.passage_count,
            history=list(self.history),last_observation=self.last_observed,
            position_known=bool(packet and packet.get('provider') and packet['provider']['observations'] and not stale
                                and not self.identity_uncertain and not (self.snapshot and self.snapshot.tracker_state_after.value=='LOST')),
            latest_frame=packet,auto_profile=self.profile,per_product_manual_controls=False)
        value['observation']['status'] = 'PACKAGE_CARRIER_MODEL; REAL_BENCH_VALIDATION_REQUIRED'
        return value
