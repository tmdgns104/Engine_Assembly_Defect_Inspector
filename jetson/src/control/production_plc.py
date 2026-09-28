"""Three BOOL contract. No PLC library, socket or physical output lives here.

Request edges and vision identity are independent of visual product clearance.
After uncertain transport, explicit valid-low resynchronization is mandatory.
"""
from dataclasses import dataclass
from typing import Protocol
import uuid


def decision_bit(decision):
    if decision not in ('PASS','FAIL','REVIEW','ERROR'):
        raise ValueError('UNKNOWN_VISION_DECISION')
    return decision != 'PASS'  # Current project contract: False=OK, True=NG.


@dataclass(frozen=True)
class IoResult:
    status: str
    value: bool | None = None
    error: str | None = None


class PlcGateway(Protocol):
    def read_request(self) -> IoResult: ...
    def write_result(self, value: bool) -> IoResult: ...
    def write_done(self, value: bool) -> IoResult: ...
    def health(self) -> dict: ...
    def close(self): ...


class MockPlcGateway:
    backend='MOCK'
    def __init__(self):
        self.request=False; self.result=False; self.done=False
        self.connected=True; self.fail_next=None; self.unknown_next=None
        self.writes=[]
    def read_request(self):
        if not self.connected: return IoResult('FAILED',error='MOCK_READ_FAILED')
        if type(self.request) is not bool: return IoResult('FAILED',error='REQUEST_NOT_BOOL')
        return IoResult('ACK',self.request)
    def _write(self,tag,value):
        if type(value) is not bool: raise ValueError('BOOL_REQUIRED')
        if not self.connected: return IoResult('FAILED',error='MOCK_DISCONNECTED')
        if self.fail_next==tag:
            self.fail_next=None
            return IoResult('FAILED',error='MOCK_WRITE_FAILED')
        self.writes.append((tag,value))
        setattr(self,'result' if tag=='Jetson_Result' else 'done',value)
        if self.unknown_next==tag:
            self.unknown_next=None
            return IoResult('UNKNOWN',error='MOCK_ACK_LOST')
        return IoResult('ACK',value)
    def write_result(self,value): return self._write('Jetson_Result',value)
    def write_done(self,value): return self._write('Jetson_Done',value)
    def health(self):
        return dict(backend='MOCK',available=self.connected,physical_output_enabled=False,
            Inspection_Request=self.request,Jetson_Result=self.result,Jetson_Done=self.done,
            result_true_means='NG',contract_confirmed=False,hardware_status='HARDWARE_NOT_VERIFIED')
    def close(self): self.connected=False


class RequestHandshake:
    def __init__(self,gateway,event,*,clear_timeout=20):
        self.gateway=gateway; self.event=event; self.clear_timeout=clear_timeout
        self.state='SYNC_LOW'; self.token=None; self.inspection_id=None
        self.request=None; self.early_off=False; self.accepted_at=None
        self.publication='NOT_STARTED'; self.reason=None; self.published_at=None
    def record(self,name,**extra):
        self.event(dict(event=name,plc_request_token=self.token,inspection_id=self.inspection_id,
            publication_backend='MOCK',publication_status=self.publication,**extra))
    def fault(self,reason,publication=None):
        self.state='RESYNC_REQUIRED'; self.reason=reason
        if publication: self.publication=publication
        self.record('PLC_FAULT',reason=reason)
    def resync(self):
        if self.inspection_id and self.state=='INSPECTING': raise ValueError('INSPECTION_RUNNING')
        read=self.gateway.read_request()
        if read.status!='ACK' or read.value is not False: raise ValueError('VALID_REQUEST_LOW_REQUIRED')
        # Explicit recovery only; never resends a historical Result.
        reply=self.gateway.write_done(False)
        if reply.status!='ACK' or reply.value is not False: raise ValueError('DONE_RESET_UNCONFIRMED')
        self.record('PLC_EXPLICIT_RESYNC')
        self.token=None; self.inspection_id=None; self.early_off=False
        self.state='ARMED'; self.request=False; self.reason=None; self.publication='NOT_STARTED'
    def poll(self,now):
        read=self.gateway.read_request()
        if read.status!='ACK' or type(read.value) is not bool:
            if self.state!='RESYNC_REQUIRED': self.fault('REQUEST_READ_FAILED')
            return
        previous=self.request; self.request=read.value
        if self.state=='SYNC_LOW':
            if read.value: self.fault('RESTART_WITH_REQUEST_HIGH')
            else: self.state='ARMED'
        elif self.state=='ARMED' and read.value and previous is False:
            self.token=uuid.uuid4().hex; self.accepted_at=now; self.early_off=False
            self.inspection_id=None; self.publication='NOT_STARTED'; self.reason=None
            self.state='REQUEST_LATCHED'; self.record('PLC_REQUEST_LATCHED')
        elif self.state in ('REQUEST_LATCHED','INSPECTING'):
            if not read.value and not self.early_off:
                self.early_off=True; self.record('PLC_REQUEST_EARLY_OFF',inspection_cancelled=False,product_clearance=False)
            elif read.value and previous is False and self.early_off:
                self.fault('OVERLAPPING_REQUEST_BEFORE_COMPLETION')
        elif self.state=='WAIT_REQUEST_OFF':
            if not read.value:
                reply=self.gateway.write_done(False)
                if reply.status!='ACK' or reply.value is not False:
                    self.fault('DONE_RESET_UNCONFIRMED',reply.status if reply.status in ('FAILED','UNKNOWN') else 'UNKNOWN')
                    return
                self.record('PLC_DONE_CLEARED',product_clearance=False,result_retained=True)
                self.state='ARMED'; self.token=None; self.inspection_id=None
            elif now-self.published_at>self.clear_timeout:
                self.fault('REQUEST_CLEAR_TIMEOUT')
    def bind(self,inspection_id):
        if self.state!='REQUEST_LATCHED' or not self.token or self.inspection_id:
            raise ValueError('REQUEST_NOT_BINDABLE')
        self.inspection_id=inspection_id; self.state='INSPECTING'
        self.record('PLC_INSPECTION_BOUND')
    def publish(self,inspection_id,decision,durable,now):
        if durable is not True: raise ValueError('DURABLE_RESULT_REQUIRED')
        if inspection_id!=self.inspection_id or not self.token: raise ValueError('PUBLICATION_IDENTITY_MISMATCH')
        if self.state!='INSPECTING':
            self.publication='BLOCKED'; self.record('PLC_PUBLICATION_BLOCKED',reason=self.reason)
            return
        self.poll(now)  # Observe early OFF/read failure immediately before writes.
        if self.state!='INSPECTING':
            self.publication='BLOCKED'; self.record('PLC_PUBLICATION_BLOCKED',reason=self.reason)
            return
        if self.early_off:
            self.fault('PLC_HANDSHAKE_CONTRACT_REQUIRED','PLC_HANDSHAKE_CONTRACT_REQUIRED')
            return
        bit=decision_bit(decision)
        self.record('PLC_DURABLE_RESULT_VERIFIED',vision_decision=decision)
        reply=self.gateway.write_result(bit)
        if reply.status!='ACK' or reply.value is not bit:
            self.fault('RESULT_WRITE_UNCONFIRMED',reply.status if reply.status in ('FAILED','UNKNOWN') else 'UNKNOWN'); return
        self.record('PLC_RESULT_ACK',value=bit)
        self.poll(now)
        if self.state!='INSPECTING' or self.early_off:
            self.fault('PLC_HANDSHAKE_CONTRACT_REQUIRED','PLC_HANDSHAKE_CONTRACT_REQUIRED'); return
        reply=self.gateway.write_done(True)
        if reply.status!='ACK' or reply.value is not True:
            self.fault('DONE_WRITE_UNCONFIRMED',reply.status if reply.status in ('FAILED','UNKNOWN') else 'UNKNOWN'); return
        self.publication='ACKNOWLEDGED'; self.state='WAIT_REQUEST_OFF'; self.published_at=now
        self.record('PLC_DONE_ACK',value=True,vision_decision=decision)
    def status(self):
        return dict(self.gateway.health(),state=self.state,plc_request_token=self.token,
            inspection_id=self.inspection_id,request_early_off=self.early_off,
            publication_status=self.publication,reason=self.reason)
