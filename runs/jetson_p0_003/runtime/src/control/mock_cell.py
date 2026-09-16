"""Virtual single-cycle controller. No motor, physical PLC or automatic product restart."""
import time


class MockCell:
    def __init__(self,port,clock=time.monotonic,timeout=15):
        self.port,self.clock,self.timeout=port,clock,timeout
        self.state='RECOVERY';self.start_high=False;self.job=None;self.result=None
        self.deadline=None;self.consumed=False;self.result_ack=False;self.disposition=None
        self.reason='EXPLICIT_RECOVERY_REQUIRED';self.transitions=[]

    def transition(self,state,reason):
        self.state,self.reason=state,reason
        self.transitions.append({'state':state,'reason':reason,'monotonic':self.clock(),
            'source_mode':'mock','control_mode':'mock'})

    def recover(self):
        if self.state!='RECOVERY':raise ValueError('RECOVERY_ONLY')
        self.port.recover()
        self.transition('IDLE','RECOVERY_ACKNOWLEDGED_NO_AUTO_START')

    def start(self,level,view):
        rising=level and not self.start_high;self.start_high=level
        if not rising:return False
        if self.state!='IDLE':raise ValueError('CYCLE_NOT_IDLE')
        if not view:raise ValueError('PER_PRODUCT_VISIBILITY_REQUIRED')
        self.job=self.port.prepare(view)
        self.result=None;self.consumed=False;self.result_ack=False;self.disposition=None
        self.deadline=self.clock()+.2
        self.transition('POSITIONING','VIRTUAL_POSITIONING')
        return True

    def tick(self):
        now=self.clock()
        if self.state=='POSITIONING' and now>=self.deadline:
            self.deadline=now+.2;self.transition('SETTLING','VIRTUAL_SETTLING')
        elif self.state=='SETTLING' and now>=self.deadline:
            try:self.port.submit(self.job)
            except Exception as error:self.transition('FAULT','SUBMIT_FAILED: '+str(error));return
            self.deadline=now+self.timeout;self.transition('WAIT_RESULT','REQUEST_ACCEPTED')
        elif self.state=='WAIT_RESULT':
            if not self.port.healthy(self.job):
                self.port.cancel(self.job);self.transition('FAULT','HEARTBEAT_OR_SESSION_LOST');return
            if now>self.deadline:
                self.port.cancel(self.job);self.transition('FAULT','RESULT_TIMEOUT');return
            result=self.port.poll(self.job)
            if result is None:return
            for key in ('cell_id','plc_session_id','request_id','cycle_id'):
                if result['request'][key]!=self.job[key]:
                    self.transition('FAULT','RESULT_KEY_MISMATCH');return
            if result.get('storage_success') is not True:
                self.transition('FAULT','RESULT_NOT_DURABLE');return
            self.result=result;self.consumed=True
            self.transition({'PASS':'RELEASE','FAIL':'HOLD','REVIEW':'HOLD','ERROR':'FAULT'}[result['decision']],
                            'RESULT_CONSUMED_ONCE: '+result['decision'])
        if self.consumed and not self.result_ack:
            # Lost ACK causes a repeat of the acknowledgement, never repeat consumption/release.
            self.result_ack=self.port.ack_result(self.job) is True

    def finish(self,disposition):
        allowed={'RELEASE':('RELEASED',),'HOLD':('REMOVED','QUARANTINED'),'FAULT':('ABORTED',)}
        if disposition not in allowed.get(self.state,()):raise ValueError('INVALID_TERMINAL_DISPOSITION')
        if self.consumed and not self.result_ack:raise ValueError('RESULT_ACK_PENDING')
        self.disposition=disposition
        self.transition('COMPLETE','VIRTUAL_PROCESSING_COMPLETE_NOT_PHYSICAL_MOTION')

    def acknowledge_cycle(self):
        if self.state!='COMPLETE':raise ValueError('CYCLE_NOT_COMPLETE')
        if self.port.terminal(self.job,self.disposition) is True:
            self.transition('IDLE','CYCLE_ACK_DURABLE')
            self.job=None
            return True
        return False

    def status(self):
        return {'state':self.state,'reason':self.reason,'job':self.job,'result_ack':self.result_ack,
                'disposition':self.disposition,'physical_motion_verified':False,'automatic_reinspection':False}
