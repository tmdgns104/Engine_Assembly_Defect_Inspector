"""Synthetic Runtime/Journal repeat cycles plus narrow HTTP authorization."""
import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from notebook.tests import test_full_frame_request as base
from src.runtime.supervised_approval import SupervisedApproval, POLICY, CONFIRMATIONS
from src.runtime.standalone_web import configure_line_web, line_view
from src.runtime.supervised_web import PREPARE_PATH

class RuntimeRepeat(unittest.TestCase):
    observe=base.RuntimeFixture.observe
    trigger=base.RuntimeFixture.trigger
    complete=base.RuntimeFixture.complete
    def setUp(self):
        base.RuntimeFixture.setUp(self)
        self.r.line_profile.update(cycle_admission=POLICY,initial_authorization=POLICY)
        self.a=SupervisedApproval(self.j.root/'initial',self.g.runtime_session)
        self.addCleanup(self.a.close)
        self.r.initial_approval=self.a
        self.g.supervised_arm=Mock()
        self.g.writes_enabled=True
        self.seq=0
        self.now=time.monotonic()
        self.observe(1,0)
        self.g.set(self.now,'DISARMED',number=0,request=False,Mc_Run=False)
        self.g.s.update(result_count=0,done_count=0,completed_count=0,approval_id='')
    def poll(self,at):
        self.g.s.update(generated=at,received=at)
        self.r._poll_cyclic_plc(at)
    def approve(self,at):
        self.poll(at)
        self.assertTrue(self.a.challenge['eligible'],self.a.status())
        identifier=self.a.submit(self.a.challenge['id'],list(CONFIRMATIONS),at)
        self.poll(at)
        self.g.s.update(approval_id=identifier,phase='SYNC_LOW')
        return identifier
    def cycle(self,number,decision):
        self.now=time.monotonic()
        approval=self.approve(self.now)
        self.assertIsNone(self.r.bridge.inspection_id)
        self.assertIsNone(self.r.latest_packet)
        self.assertFalse(self.r._clear(self.now))
        self.observe(number*10+1,.01)
        self.g.s.update(phase='IDLE',controls=dict(Inspection_Request=False,Mc_Run=True,EStop_OK=True,Stop_PB=True))
        self.poll(self.now+.1)
        self.g.s.update(phase='REQUEST_RECEIVED',request_id=number,accepted_at=self.now+.2)
        self.g.s['controls']['Inspection_Request']=True
        self.poll(self.now+.2)
        self.observe(number*10+2,.3)
        self.trigger(.4)
        self.assertEqual(len(self.submitted),number)
        self.poll(self.now+.4)
        self.trigger(.4)
        self.assertEqual(len(self.submitted),number)
        with patch('src.runtime.standalone.time.monotonic',return_value=self.now+.4):
            identifier=self.complete(decision)
        row=self.j.detail(identifier)
        identity=dict(inspection=identifier,session=row['request']['runtime_binding']['runtime_session_id'],
            cycle=row['request']['runtime_binding']['cycle_id'],track=self.r.history[0]['track_uid'],
            request=self.r.handshake.token,approval=approval)
        self.assertEqual(self.r.history[0]['plc_result_value'],int(decision!='PASS'))
        self.g.s.update(phase='READY_NEXT',result_count=number,done_count=number,completed_count=number)
        self.g.s['controls'].update(Inspection_Request=False,Mc_Run=False)
        self.poll(self.now+.5)
        self.assertEqual(self.a.state,'COMPLETED_WAIT_OPERATOR')
        self.assertTrue(self.r.history[0]['cyclic_done_reset_observed'])
        count=self.g.supervised_arm.call_count
        self.poll(self.now+.55)
        self.assertEqual(self.g.supervised_arm.call_count,count)
        return identity
    def test_four_durable_cycles_unique_identities_no_automatic_grant(self):
        identities=[self.cycle(i+1,d) for i,d in enumerate(('PASS','FAIL','REVIEW','ERROR'))]
        for key in identities[0]:
            self.assertEqual(len({v[key] for v in identities}),4,key)
        self.assertEqual(self.g.result.call_count,4)
        self.assertEqual(self.j.db.execute('SELECT count(*) FROM inspections').fetchone()[0],4)
        self.assertEqual(self.a.db.execute('SELECT count(*) FROM approvals').fetchone()[0],4)
        self.assertEqual(self.r.cyclic_admissions,4)
        evidence=[json.loads(row[0]) for row in self.a.db.execute('SELECT value FROM supervised_evidence')]
        self.assertTrue(all(e['ai_clearance_granted'] is False for e in evidence))
        self.assertEqual(evidence[-1]['previous']['decision'],'REVIEW')
        with self.assertRaises(ValueError):
            self.r._commit_and_publish(identities[0]['inspection'],{'decision':'PASS'},self.now+.6)
        self.assertEqual(self.g.result.call_count,4)
    def test_previous_assembly_owner_still_working_blocks_preparation(self):
        self.r.assembly.status=lambda:dict(ready=True,active_identifier='old',pending=0)
        self.poll(self.now)
        self.assertFalse(self.a.challenge['eligible'])
        self.assertEqual(self.a.challenge['reason'],'WAIT_ASSEMBLY_OWNER_IDLE')

    def test_missing_product_deadline_ERROR_can_prepare_again_after_completed_transfer(self):
        grant=self.approve(self.now)
        self.g.s.update(phase='REQUEST_RECEIVED',request_id=1,accepted_at=self.now+.2)
        self.g.s['controls'].update(Inspection_Request=True,Mc_Run=True)
        self.poll(self.now+.2)
        self.trigger(31)
        self.assertEqual(self.r.history[0]['decision'],'ERROR')
        self.assertEqual(self.r.history[0]['source'],'NO_ACTUAL_INSPECTION')
        self.g.s.update(phase='READY_NEXT',result_count=1,done_count=1,completed_count=1)
        self.g.s['controls'].update(Inspection_Request=False,Mc_Run=False)
        self.poll(self.now+31.1)
        self.assertTrue(self.a.challenge['eligible'],self.a.status())
        next_grant=self.approve(self.now+31.2)
        self.assertNotEqual(grant,next_grant)
        self.assertEqual(self.g.result.call_count,1)
    def test_current_storage_or_worker_fault_blocks_preparation(self):
        self.service.active='old'
        self.poll(self.now)
        self.assertFalse(self.a.challenge['eligible'])
        self.g.supervised_arm.assert_not_called()

    def test_assembly_queue_handoff_and_previous_frames_cannot_open_next_trial(self):
        from src.vision.assembly_inspection import AssemblyInspector
        inspector=AssemblyInspector(self.j.root,self.j.root/'assembly',start=False)
        inspector.jobs.put({'inspection_id':'old'})
        inspector.jobs.get_nowait()  # Taken but active_identifier not assigned yet.
        self.assertEqual(inspector.status()['outstanding'],1)
        self.r.assembly=inspector
        self.assertFalse(self.r._supervised_settlement()['clean'])
        inspector.jobs.task_done()
        self.r.assembly.ready=True
        self.approve(self.now+.1)
        self.observe(2,.05)  # Older than this approval's source-time cutoff.
        self.assertIsNone(self.r.latest_packet)

class PreparationHttp(unittest.TestCase):
    setUp=RuntimeRepeat.setUp
    observe=RuntimeRepeat.observe
    poll=RuntimeRepeat.poll
    # Reuse fixture only, not the Runtime repeat tests in this class.
    def test_explicit_pairing_same_origin_bounded_post_no_other_mutation(self):
        from fastapi import FastAPI
        from notebook.tests.supervised_asgi_fixture import LocalAsgiClient as TestClient
        self.r.line_profile['supervised_web']=dict(enabled=True,allowed_hosts=['testserver'])
        self.poll(self.now)
        app=FastAPI();configure_line_web(app,self.r,{'release_id':'fixture'})
        secret=json.loads((self.a.root/'web_pairing.json').read_text())['token']
        body=dict(challenge_id=self.a.challenge['id'],confirmations=list(CONFIRMATIONS))
        headers={'Origin':'http://testserver','Authorization':'Bearer '+secret}
        with TestClient(app) as client:
            self.assertEqual(client.get('/auto',follow_redirects=False).headers['location'],'/line')
            self.assertNotIn(secret,client.get('/line').text)
            for changed in ({},{'Origin':'http://evil','Authorization':headers['Authorization']},
                            dict(headers,Host='evil')):
                self.assertEqual(client.post(PREPARE_PATH,json=body,headers=changed).status_code,403)
            for path in ('/api/v1/runtime/start','/api/v1/runtime/reset','/api/v1/inspect'):
                self.assertEqual(client.post(path,json=body,headers=headers).status_code,403)
            self.assertEqual(client.post(PREPARE_PATH,content='x'*2049,headers=headers).status_code,409)
            self.assertEqual(client.post(PREPARE_PATH,json=dict(body,confirmations=[]),headers=headers).status_code,409)
            with patch('src.runtime.standalone.time.monotonic',return_value=self.now):
                self.assertEqual(client.post(PREPARE_PATH,json=body,headers=headers).status_code,202)
                self.assertEqual(client.post(PREPARE_PATH,json=body,headers=headers).status_code,409)
            self.g.supervised_arm.assert_not_called()
            self.assertFalse(self.g.result.called)
    def test_default_profile_all_mutations_still_forbidden(self):
        from fastapi import FastAPI
        from notebook.tests.supervised_asgi_fixture import LocalAsgiClient as TestClient
        app=FastAPI();configure_line_web(app,self.r,{})
        with TestClient(app) as c:self.assertEqual(c.post(PREPARE_PATH,json={}).status_code,403)

if __name__=='__main__':unittest.main()
