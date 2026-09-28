"""Experiment adapter reusing the Service allocator, Worker and durable Journal."""
import json


class ServiceLabPort:
    def __init__(self,service): self.service=service

    def start(self,mode,session,reason=None):
        service=self.service
        request=dict(service.allocate_request(),kind='inspect',view_assessment={},
                     source_mode=mode,lab_session_id=session,control_mode='lab',
                     test_label='LAB diagnostic' if reason else mode,
                     human_acceptance='PENDING',physical_output_enabled=False)
        camera=service.status()['camera_ready']
        if not camera or service.state!='IDLE' or reason=='CAMERA_EPOCH_CHANGED':
            identifier,_=service.journal.admit(request,service.package.snapshot())
            code=reason if reason in ('CAMERA_NOT_READY','CAMERA_EPOCH_CHANGED') else 'CAMERA_OR_RUNTIME_NOT_READY'
            service.journal.finish(identifier,dict(decision='ERROR',reason=code,reason_code=code,
                disposition='REJECT',source_mode=mode,human_acceptance='PENDING',
                physical_output_enabled=False,observations=[],frames=[],
                execution={'source':'not_executed','control':mode}))
            return identifier
        request['lab_trigger_reason']=reason
        detail,_=service.submit(request,_lab=True)
        return detail['inspection_id']

    def poll(self,identifier):
        detail=self.service.journal.detail(identifier)
        return detail.get('result') if detail else None

    def cancel(self,identifier):
        if self.service.active and self.service.active['inspection_id']==identifier:
            self.service.cancel(identifier)

    def event(self,value):
        journal=self.service.journal
        with journal.lock,journal.db:
            journal._event(value['event'],value)
            if value['event']=='LAB_PUBLICATION' and value.get('inspection_id'):
                journal.db.execute('INSERT INTO service_state VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                    ('lab_publication:'+value['inspection_id'],json.dumps(value)))

    def publication(self,identifier):
        journal=self.service.journal
        with journal.lock:
            row=journal.db.execute('SELECT value FROM service_state WHERE key=?',('lab_publication:'+identifier,)).fetchone()
        return json.loads(row[0]) if row else None
