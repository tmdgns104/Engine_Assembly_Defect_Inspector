"""검사창 → 기존 요청 → 저장 완료 identity → H6 연결. 검사 엔진을 만들지 않는다."""
from copy import deepcopy


class InspectionBridge:
    """runtime lock 아래서만 호출한다. Service lock → Journal lock 순서를 지킨다.

    monitor의 저장 transaction이 끝난 뒤 COMPLETE를 읽는다.
    Worker 결과 queue를 직접 소비하거나 검사 결과를 생성하지 않는다.
    """
    def __init__(self, service, coordinator):
        self.service = service
        self.coordinator = coordinator
        self.request = None
        self.inspection_id = None
        self.decision = None
        self.phase = 'NOT_REQUESTED'
        self.error = None

    def submit_window(self, event, cycle_id, view_assessment, auto_frame_binding=None):
        if self.request is not None:
            raise ValueError('INSPECTION_ALREADY_REQUESTED')
        with self.service.lock:
            request = self.service.allocate_request()
            request.update(kind='inspect', control_mode='manual',
                view_assessment=deepcopy(view_assessment),
                runtime_binding={'runtime_session_id':self.coordinator.runtime_session_id,
                    'cycle_id':cycle_id,'track_id':event.track_id,
                    'inspection_window':event.to_dict(),
                    'authority':'MANUAL_DIAGNOSTIC_OBSERVATION'})
            if auto_frame_binding is not None:
                request['control_mode'] = 'auto'
                request['view_assessment'] = {'source':'AUTO_WORKER_DERIVED'}
                request['runtime_binding']['authority'] = 'PACKAGE_CARRIER_DETECTOR'
                request['auto_frame_binding'] = deepcopy(auto_frame_binding)
            row,created = self.service.submit(request)
            if not created:
                raise ValueError('UNEXPECTED_EXISTING_REQUEST')
            self.request = request
            self.inspection_id = row['inspection_id']
            self.phase = 'INSPECTION_REQUESTED'

    def submit_production(self,binding):
        if self.request is not None: raise ValueError('INSPECTION_ALREADY_REQUESTED')
        with self.service.lock:
            request=dict(self.service.allocate_request(),kind='inspect',control_mode='production',
                source_mode='PRODUCTION_AUTO',view_assessment={},runtime_binding=deepcopy(binding),
                human_acceptance='PENDING',physical_output_enabled=False)
            if not self.service.status()['camera_ready'] or self.service.state!='IDLE':
                identifier,created=self.service.journal.admit(request,self.service.package.snapshot())
                self.service.journal.finish(identifier,dict(decision='ERROR',reason='CAMERA_OR_RUNTIME_NOT_READY',
                    reason_code='CAMERA_OR_RUNTIME_NOT_READY',disposition='REJECT',observations=[],
                    production_identity=dict(binding,inspection_id=identifier),human_acceptance='PENDING',
                    physical_output_enabled=False,execution={'source':'not_executed','control':'production',
                    'worker_generation':self.service.generation}))
                row=self.service.journal.detail(identifier)
            else:
                row,created=self.service.submit(request,_production=True)
            if not created: raise ValueError('UNEXPECTED_EXISTING_REQUEST')
            self.request=request; self.inspection_id=row['inspection_id']; self.phase='INSPECTION_REQUESTED'

    def poll(self):
        if self.request is None or self.phase in ('INSPECTION_DURABLE','INSPECTION_ERROR'):
            return None
        with self.service.lock:
            row = self.service.journal.detail(self.inspection_id)
            production=self.request.get('source_mode')=='PRODUCTION_AUTO'
            if not production and self.service.state in ('RECOVERY','CANCELLING'):
                return self._fail(self.service.error or self.service.state)
            if (row is None or row['request'] != self.request
                    or self.request['plc_session_id'] != self.service.session
                    or self.request['package_sha256'] != self.service.package.manifest_hash):
                return self._fail('INSPECTION_IDENTITY_MISMATCH')
            if row['state'] == 'ACCEPTED':
                self.phase = 'INSPECTION_RUNNING'
                return None
            result = row.get('result') or {}
            self.decision = row.get('decision')
            if (row['state'] != 'COMPLETE' or result.get('storage_success') is not True
                    or self.decision not in (('PASS','FAIL','REVIEW','ERROR') if production else ('PASS','FAIL','REVIEW'))):
                return self._fail(result.get('reason','INSPECTION_NOT_SUCCESSFULLY_EXECUTED'))
            if (result.get('inspection_id') != self.inspection_id or result.get('request') != self.request
                    or result.get('execution',{}).get('worker_generation') != self.service.generation):
                return self._fail('DURABLE_RESULT_CONTEXT_MISMATCH')
            # 기존 Service의 결과 commit과 이후 timing event 처리가 끝난 시점이다.
            binding = self.request['runtime_binding']
            if production:
                identity=result.get('production_identity') or {}
                if identity!=dict(binding,inspection_id=self.inspection_id):
                    return self._fail('PRODUCTION_DURABLE_IDENTITY_MISMATCH')
            snapshot = (self.coordinator.mark_inspected(binding['cycle_id'],binding['track_id'],self.inspection_id)
                        if binding.get('track_id') is not None else None)
            self.phase = 'INSPECTION_DURABLE'
            return snapshot

    def _fail(self, reason):
        self.phase = 'INSPECTION_ERROR'
        self.error = str(reason)
        # 경계 검증에 실패한 PASS를 통합 완료 결과로 노출하지 않는다.
        if self.decision == 'PASS':
            self.decision = None
        return None

    def status(self):
        return {'phase':self.phase,'inspection_id':self.inspection_id,'decision':self.decision,
                'request':deepcopy(self.request),'error':self.error,
                'running_basis':'SERVICE_BUSY_QUEUE_DISPATCH; no separate worker-start ACK',
                'durable_basis':'Journal.finish committed COMPLETE/result/assets/event/outbox'}
