"""Experiment triggers only. No camera access, vision logic or physical PLC driver."""
from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class ReadBool:
    valid: bool
    value: bool | None


class MockPlcGateway:
    """In-memory BOOL gateway; write outcomes are explicit, including ambiguity.

    A future Omron adapter must implement read_request/write with bounded I/O
    outside the camera thread. This release has no network implementation.
    """
    def __init__(self):
        self.request=False
        self.result=False
        self.done=False
        self.connected=True
        self.fail_next=None
        self.unknown_next=None
        self.writes=[]

    def read_request(self):
        return ReadBool(self.connected,self.request if self.connected else None)

    def write(self,tag,value):
        if tag not in ('Jetson_Result','Jetson_Done') or type(value) is not bool:
            raise ValueError('INVALID_MOCK_WRITE')
        if not self.connected: return 'FAILED'
        if self.fail_next==tag:
            self.fail_next=None
            return 'FAILED'
        if self.unknown_next==tag:
            self.unknown_next=None
            return 'UNKNOWN'
        setattr(self,'result' if tag=='Jetson_Result' else 'done',value)
        self.writes.append((tag,value))
        self.writes=self.writes[-100:]
        return 'ACKNOWLEDGED'

    def status(self):
        return dict(backend='MOCK',connected=self.connected,Inspection_Request=self.request,
                    Jetson_Result=self.result,Jetson_Done=self.done,result_true_means='PASS',
                    contract_confirmed=False,physical_output_enabled=False)


class LabController:
    """One owner, one bounded request, one immutable result per entry/edge.

    Called under the Service lock. Port.start must return an admitted inspection
    ID; poll returns only that ID's durable result. Events persist separately.
    """
    def __init__(self,port,gateway=None):
        self.port=port
        self.gateway=gateway or MockPlcGateway()
        self.mode='MANUAL'
        self.state='STOPPED'
        self.session=None
        self.job=None
        self.latest_id=None
        self.publication={}
        self.reason=None
        self.last_frame=None
        self.last_epoch=None
        self.last_pts=None
        self.counters={}
        self.entered_at=0.
        self.hold_until=0.
        self.clear_deadline=0.

    def transition(self,state,reason=None):
        self.state,self.reason=state,reason
        self.port.event(dict(event='LAB_STATE',source_mode=self.mode,session_id=self.session,
                             state=state,reason=reason,inspection_id=self.job))

    def select(self,mode,confirmed,now):
        if mode not in ('MANUAL','LAB_AUTO','MOCK_PLC'): raise ValueError('INVALID_MODE')
        if self.job is not None or self.state=='WAIT_REQUEST_CLEAR': raise ValueError('INSPECTION_OR_HANDSHAKE_BUSY')
        if mode!='MANUAL' and confirmed is not True: raise ValueError('EXPERIMENT_CONFIRMATION_REQUIRED')
        self.mode=mode
        self.session=uuid.uuid4().hex if mode!='MANUAL' else None
        self.last_frame=self.last_epoch=self.last_pts=None
        self.counters={}
        self.transition({'MANUAL':'STOPPED','LAB_AUTO':'WAIT_PRODUCT','MOCK_PLC':'RESYNC'}[mode])

    def stop(self):
        if self.job:
            self.port.cancel(self.job)
            self.publish('CANCELLED',None)
        self.job=None
        self.mode='MANUAL'
        self.session=None
        self.counters={}
        self.transition('STOPPED','EXPLICIT_STOP_REQUIRES_NEW_SESSION')

    def resync(self):
        if self.mode!='MOCK_PLC': raise ValueError('MOCK_MODE_REQUIRED')
        if self.job is not None: raise ValueError('INSPECTION_BUSY')
        sample=self.gateway.read_request()
        if not sample.valid or sample.value is not False: raise ValueError('VALID_REQUEST_LOW_REQUIRED')
        outcome=self.gateway.write('Jetson_Done',False)
        if outcome!='ACKNOWLEDGED':
            self.transition('RESYNC','DONE_RESET_'+outcome)
            return
        self.transition('ARMED')

    def publish(self,status,decision):
        self.publication=dict(inspection_id=self.job,source_mode=self.mode,session_id=self.session,
            vision_decision=decision,publication_backend='MOCK' if self.mode=='MOCK_PLC' else 'NONE',
            publication_status=status,physical_output_enabled=False,human_acceptance='PENDING')
        self.port.event(dict(event='LAB_PUBLICATION',**self.publication))

    def fault(self,reason,outcome='FAILED',decision=None):
        if self.job:
            self.port.cancel(self.job)
            self.publish(outcome,decision)
        elif self.state=='WAIT_REQUEST_CLEAR' and self.latest_id:
            self.job=self.latest_id
            self.publish(outcome,decision or self.publication.get('vision_decision'))
        self.job=None
        self.transition('RESYNC',reason)

    def start(self,reason=None):
        self.job=self.port.start(self.mode,self.session,reason)
        self.latest_id=self.job
        self.transition('INSPECTING',reason)

    def reinspect(self):
        if self.mode!='LAB_AUTO' or self.state not in ('WAIT_PRODUCT','WAIT_STABLE','RESULT_HOLD','WAIT_PRODUCT_EXIT') or self.job:
            raise ValueError('LAB_REINSPECTION_NOT_READY')
        self.start()
        return self.job

    def consecutive(self,key,condition,now,count,seconds):
        if not condition:
            self.counters.pop(key,None)
            return False
        n,since=self.counters.get(key,(0,now))
        self.counters[key]=(n+1,since)
        return n+1>=count and now-since>=seconds

    def tick(self,now,scene,camera_ready):
        if self.mode=='MANUAL': return
        if self.mode=='MOCK_PLC':
            self.tick_mock(now)
            return
        if self.job:
            value=self.port.poll(self.job)
            if value is not None:
                self.publish('NOT_APPLICABLE',value['decision'])
                self.job=None
                self.hold_until=now+1
                self.counters={}
                self.transition('RESULT_HOLD')
            return
        if self.state=='WAIT_STABLE' and not camera_ready:
            self.start('CAMERA_NOT_READY')
            return
        if self.state=='WAIT_STABLE' and now-self.entered_at>=8:
            self.start('LAB_STABILITY_TIMEOUT')
            return
        if self.state=='RESULT_HOLD':
            if now>=self.hold_until: self.transition('WAIT_PRODUCT_EXIT')
            return
        if not camera_ready or not scene:
            self.counters={}
            return
        frame=scene.get('frame_id'); epoch=scene.get('camera_epoch'); pts=scene.get('source_pts_ns')
        if frame is None or pts is None or frame==self.last_frame: return
        if self.last_epoch is not None and epoch!=self.last_epoch:
            self.counters={}
            self.last_pts=None
            if self.state=='WAIT_STABLE':
                self.start('CAMERA_EPOCH_CHANGED')
                return
        if self.last_pts is not None and pts<=self.last_pts:
            self.counters={}
            return
        self.last_frame,self.last_epoch,self.last_pts=frame,epoch,pts
        # Never use part presence or final PASS as the entry/stability condition.
        present=bool(scene.get('product') or scene.get('products'))
        if self.state=='WAIT_PRODUCT':
            if self.consecutive('entry',present,now,3,.5):
                self.entered_at=now; self.counters={}; self.transition('WAIT_STABLE')
        elif self.state=='WAIT_STABLE':
            stable=present and scene.get('stable') is True and scene.get('quality_valid') is True and scene.get('pose',{}).get('reliable') is True
            if self.consecutive('stable',stable,now,3,.6): self.start()
        elif self.state=='WAIT_PRODUCT_EXIT':
            valid_absence=not present and scene.get('quality_valid') is True and scene.get('reason_code')=='PRODUCT_ENVELOPE_NOT_FOUND'
            if self.consecutive('exit',valid_absence,now,6,1.5):
                self.counters={}; self.transition('WAIT_PRODUCT')

    def tick_mock(self,now):
        sample=self.gateway.read_request()
        if not sample.valid:
            if self.state!='RESYNC': self.fault('REQUEST_READ_FAILED')
            return
        if self.state=='RESYNC':
            # Initial low may arm, but faults require the explicit resync action.
            if self.reason is None and sample.value is False: self.resync()
            return
        if self.state=='ARMED':
            if sample.value is True: self.start()
            return
        if self.state=='INSPECTING':
            if sample.value is False:
                self.fault('REQUEST_CLEARED_DURING_INSPECTION','CANCELLED')
                return
            value=self.port.poll(self.job)
            if value is None: return
            decision=value['decision']
            if decision=='ERROR':
                self.fault('VISION_SYSTEM_ERROR',decision=decision)
                return
            if decision not in ('PASS','FAIL','REVIEW'):
                self.fault('INVALID_VISION_DECISION',decision=decision)
                return
            outcome=self.gateway.write('Jetson_Result',decision=='PASS')
            if outcome!='ACKNOWLEDGED':
                self.fault('RESULT_WRITE_'+outcome,outcome,decision)
                return
            outcome=self.gateway.write('Jetson_Done',True)
            if outcome!='ACKNOWLEDGED':
                self.fault('DONE_WRITE_'+outcome,outcome,decision)
                return
            self.publish('ACKNOWLEDGED',decision)
            self.job=None
            self.clear_deadline=now+20
            self.transition('WAIT_REQUEST_CLEAR')
        elif self.state=='WAIT_REQUEST_CLEAR':
            if sample.value is False:
                outcome=self.gateway.write('Jetson_Done',False)
                if outcome!='ACKNOWLEDGED': self.fault('DONE_RESET_'+outcome,outcome)
                else: self.transition('ARMED')
            elif now>=self.clear_deadline: self.fault('REQUEST_CLEAR_TIMEOUT')

    def status(self):
        return dict(source_mode=self.mode,state=self.state,reason=self.reason,session_id=self.session,
                    inspection_id=self.job,latest_inspection_id=self.latest_id,publication=self.publication,
                    human_acceptance='PENDING',physical_output_enabled=False,mock=self.gateway.status())
