"""교체 가능한 관측/제어 경계. mock 모드에는 물리 권한이 없다."""
from typing import Protocol

from src.integration.clearance import ClearanceEvidence
from src.integration.cycle_track_binding import BoundClearanceEvidence
from src.observation.contracts import AmbiguityReason, ProviderResult, ProviderStatus
from src.tracking.contracts import NormalizedBox, ProductObservation


class ObservationSource(Protocol):
    label: str

    def observe(self, value: object) -> ProviderResult: ...
    def close(self) -> None: ...


class PLCAdapter(Protocol):
    """증거 입력 경계. 향후 실제 출력 명령의 수용 계약은 별도 구현 대상이다."""
    def clearance(self, **identity) -> BoundClearanceEvidence: ...
    def disposition_for(self, decision: str) -> str: ...
    def publish_result(self, result: dict) -> None: ...
    def recovery_clearance(self, **identity) -> dict: ...
    def status(self) -> dict: ...
    def close(self) -> None: ...


class ManualObservationSource:
    label = 'MANUAL_DIAGNOSTIC_OBSERVATION'

    def __init__(self):
        self.closed = False

    def observe(self, value: dict) -> ProviderResult:
        if self.closed:
            raise ValueError('OBSERVATION_SOURCE_CLOSED')
        status = ProviderStatus(value['status'])
        observations = ()
        reason = None
        if status == ProviderStatus.PRODUCT_OBSERVED:
            observations = (ProductObservation(NormalizedBox(*value['bbox']),self.label),)
        elif status == ProviderStatus.AMBIGUOUS_FOREGROUND:
            reason = AmbiguityReason(value['reason'])
        # 측정 영상이 없으므로 진단 counter만 0으로 표현한다. 영상 측정을 뜻하지 않는다.
        return ProviderResult(observations,status,reason,0,0,0,())

    def close(self):
        self.closed = True


class MockPLCAdapter:
    label = 'MANUAL_DIAGNOSTIC_CLEARANCE'

    def __init__(self):
        self.closed = False
        self.last_disposition = None

    def disposition_for(self, decision):
        if self.closed:
            raise ValueError('PLC_ADAPTER_UNAVAILABLE')
        return {'PASS':'PASS','FAIL':'NG','REVIEW':'REVIEW','ERROR':'ERROR'}[decision]

    def publish_result(self, result):
        self.disposition_for(result['decision'])
        from copy import deepcopy
        self.last_disposition = deepcopy(result)

    def recovery_clearance(self, **identity):
        """LOST는 H5 binding이 없으므로 상위 오류 cycle 폐기용 명시 권한을 별도로 검증한다."""
        from src.tracking.contracts import require_integer,require_text
        if self.closed:
            raise ValueError('PLC_ADAPTER_UNAVAILABLE')
        if identity.pop('confirmed_clear') is not True:
            raise ValueError('EXPLICIT_DIAGNOSTIC_CLEARANCE_REQUIRED')
        for key in ('runtime_session_id','cycle_id','evidence_id','source_epoch'):
            require_text(identity[key],key)
        require_integer(identity['source_sequence'],'source_sequence',0)
        if identity['track_id'] is not None:
            require_integer(identity['track_id'],'track_id',1)
        return dict(identity,authority=self.label,physical_clearance_verified=False)

    def clearance(self, **identity) -> BoundClearanceEvidence:
        if self.closed:
            raise ValueError('PLC_ADAPTER_UNAVAILABLE')
        confirmed = identity.pop('confirmed_clear')
        if confirmed is not True:
            raise ValueError('EXPLICIT_DIAGNOSTIC_CLEARANCE_REQUIRED')
        authority = ClearanceEvidence(True,'manual-diagnostic-operator',self.label)
        return BoundClearanceEvidence(**identity,clearance_evidence=authority)

    def status(self):
        return {'adapter':'MockPLCAdapter','authority':self.label,'available':not self.closed,
                'physical_action_accepted':False,'hardware_connected':False,
                'last_disposition':self.last_disposition}

    def close(self):
        self.closed = True
