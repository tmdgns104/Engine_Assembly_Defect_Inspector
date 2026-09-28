"""자동 영상 관측 계약 복원과 물리 통신을 주장하지 않는 로컬 결과 출력 경계."""
from copy import deepcopy
from src.observation.contracts import ProviderResult, ProviderStatus, AmbiguityReason
from src.tracking.contracts import ProductObservation, NormalizedBox


class WorkerObservationSource:
    label = 'PACKAGE_CARRIER_DETECTOR'
    def observe(self, packet):
        value = packet['provider']
        if not packet['integrity']['valid'] or value is None:
            raise ValueError('INVALID_FRAME_IS_NOT_AN_OBSERVATION')
        observations = tuple(ProductObservation(NormalizedBox(**o['bbox']),o['source']) for o in value['observations'])
        return ProviderResult(observations,ProviderStatus(value['status']),
            AmbiguityReason(value['reason']) if value['reason'] else None,0,0,value['total_components'],())
    def close(self):
        pass


class LocalResultOutput:
    """Journal 이벤트가 durable outbox의 근거다. PLC 수신 ACK는 생성하지 않는다."""
    def __init__(self):
        self.closed = False
        self.last_disposition = None
    def disposition_for(self, decision):
        if self.closed:
            raise ValueError('RESULT_OUTPUT_CLOSED')
        return {'PASS':'PASS','FAIL':'NG','REVIEW':'REVIEW','ERROR':'ERROR'}[decision]
    def publish_result(self, result):
        self.disposition_for(result['decision'])
        self.last_disposition = deepcopy(result)
    def status(self):
        return {'adapter':'LocalResultOutput','available':not self.closed,'hardware_connected':False,
            'physical_action_accepted':False,'authority':'VISION_ONLY_NO_PLC',
            'delivery_state':'DURABLE_LOCAL_EVENT' if self.last_disposition else 'NO_RESULT',
            'plc_transmitted':False,'plc_acknowledged':False,'last_disposition':self.last_disposition}
    def close(self):
        self.closed = True
