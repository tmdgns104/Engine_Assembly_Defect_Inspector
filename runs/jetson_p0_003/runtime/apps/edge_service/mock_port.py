"""One Control Agent adapter to the local Service; no actual PLC outputs."""
import json
from src.recipe.package import canonical


class ServiceMockPort:
    def __init__(self,service):self.service=service

    def recover(self):
        journal=self.service.journal
        with journal.lock:
            rows=journal.db.execute("SELECT inspections.inspection_id FROM inspections JOIN cycles USING(cell_id,plc_session_id,cycle_id) WHERE cycles.terminal IS NULL AND json_extract(request_json,'$.control_mode')='mock'").fetchall()
        for row in rows:
            journal.cancel(row[0],'MOCK_RESTART_RECOVERY')
            journal.record_terminal(row[0],'ABORTED','mock-operator','Explicit recovery; physical disposition unverified')

    def prepare(self,view):
        if not self.service.status()['ready']:raise ValueError('INSPECTION_NOT_READY')
        slots=self.service.package.recipe['slots']
        if view.get('product_identity')!='human_confirmed' or view.get('alignment_confirmed') is not True or any(view.get('visible_slots',{}).get(s['id']) is not True for s in slots):
            raise ValueError('ALL_PHYSICAL_PREPARATION_CONFIRMATIONS_REQUIRED')
        return dict(self.service.allocate_request(),kind='inspect',view_assessment=view,control_mode='mock')

    def submit(self,job):return self.service.submit(job)

    def healthy(self,job):
        status=self.service.status()
        return status['worker_alive'] and status['state']!='RECOVERY' and status['plc_session_id']==job['plc_session_id']

    def poll(self,job):
        row=self.service.journal.find_request(job)
        return self.service.journal.detail(row['inspection_id'])['result'] if row else None

    def cancel(self,job):
        row=self.service.journal.find_request(job)
        if row:self.service.cancel(row['inspection_id'])

    def ack_result(self,job):
        journal=self.service.journal
        row=journal.find_request(job)
        if not row or row['state']=='ACCEPTED':return False
        key='result_ack:'+row['inspection_id']
        with journal.lock,journal.db:
            old=journal.db.execute('SELECT value FROM service_state WHERE key=?',(key,)).fetchone()
            if not old:
                journal.db.execute('INSERT INTO service_state VALUES (?,?)',(key,'ACKED'))
                journal._event('MOCK_RESULT_ACK',{'inspection_id':row['inspection_id'],'request':job,'source_mode':'mock','control_mode':'mock'})
        return True

    def terminal(self,job,disposition):
        journal=self.service.journal
        row=journal.find_request(job)
        if not row:
            identifier,_=journal.admit(job,self.service.package.snapshot())
            journal.finish(identifier,{'decision':'ERROR','reason':'MOCK_REQUEST_NOT_EXECUTED','defects':[],
                'execution':{'source':'not_executed','control':'mock'}})
        else:identifier=row['inspection_id']
        if self.service.active:raise ValueError('WORKER_TERMINATION_PENDING')
        journal.record_terminal(identifier,disposition,'mock-operator','Virtual cycle termination; physical motion unverified')
        return True
