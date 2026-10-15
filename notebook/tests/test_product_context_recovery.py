"""Maintenance closes historical physical context, never fabricates clearance."""
import copy
import json
import unittest
from unittest.mock import patch
from notebook.tests.test_automatic_runtime import AutomaticRuntimeTests as Fixture
from src.runtime import product_context_recovery as recovery


class ProductContextRecoveryTests(unittest.TestCase):
    setUp = Fixture.setUp
    frame = Fixture.frame
    observe = Fixture.observe
    poll = Fixture.poll
    trigger = Fixture.trigger
    complete = Fixture.complete
    request_and_complete = Fixture.request_and_complete

    def prepare(self):
        identifier=self.request_and_complete(1,'REVIEW')
        row=self.j.db.execute('SELECT * FROM inspections WHERE inspection_id=?',(identifier,)).fetchone()
        final=self.j.db.execute('SELECT value FROM service_state WHERE key=?',('integrated_decision:'+identifier,)).fetchone()[0]
        self.proof=dict(inspection_id=identifier, request_sha256=recovery.digest(row['request_json']),
            result_sha256=recovery.digest(row['result_json']), final_sha256=recovery.digest(final),
            actor='fixture',reason='field product removed',
            confirmations=['PHYSICAL_STOP','PRODUCT_REMOVED_OR_HELD_OFF_LINE','CLOSE_CONTEXT_WITHOUT_RESULT'],
            current=dict(self.g.s, observed_at=10,generated=10,received=10,phase='DISARMED',
                controls=dict(Inspection_Request=False,Mc_Run=False,EStop_OK=True,Stop_PB=True),
                runtime_session='current'),
            owners=dict(runtime_session='current',worker_alive=True,camera_ready=True,
                active_inspection_id=None,storage_pending=False,final_commit_pending=False,
                assembly_active=None,assembly_pending=0,assembly_outstanding=0,worker_state='IDLE'))
        return identifier

    def test_closed_context_preserves_original_and_is_not_AI_separation(self):
        identifier=self.prepare()
        before=tuple(self.j.db.execute('SELECT * FROM inspections').fetchone())
        self.r._restore_previous_product_identity()
        self.assertIsNotNone(self.r.prior_product_identity_block)
        recovery.record_context_close(self.j,identifier,self.proof,now=10)
        self.r._restore_previous_product_identity()
        self.assertIsNone(self.r.prior_product_identity_block)
        self.assertEqual(before,tuple(self.j.db.execute('SELECT * FROM inspections').fetchone()))
        self.assertEqual(self.j.db.execute("SELECT count(*) FROM events WHERE event_type='AUTOMATIC_PRODUCT_SEPARATED'").fetchone()[0],0)
        self.assertTrue(recovery.valid_context_close(self.j.db,identifier))
        with self.assertRaises(ValueError):recovery.record_context_close(self.j,identifier,self.proof,now=10)

    def test_stale_active_output_unconfirmed_and_missing_owners_rejected(self):
        identifier=self.prepare()
        for group,key,value in [('current','generated',8),('current','raw100','01000100'),
                ('owners','storage_pending',True),('owners','assembly_outstanding',1),
                ('owners','worker_alive',False),('owners','runtime_session','other')]:
            p=copy.deepcopy(self.proof);p[group][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):
                recovery.record_context_close(self.j,identifier,p,now=10)
        p=copy.deepcopy(self.proof);p['owners'].pop('active_inspection_id')
        with self.assertRaises(ValueError):recovery.record_context_close(self.j,identifier,p,now=10)
        p=copy.deepcopy(self.proof);p['confirmations']=[]
        with self.assertRaises(ValueError):recovery.record_context_close(self.j,identifier,p,now=10)

    def test_actual_unfinished_and_low_disk_not_exempted(self):
        identifier=self.prepare()
        self.j.admit(dict(cell_id='new',plc_session_id=9,request_id=1,cycle_id=1,attempt=1),{})
        with self.assertRaisesRegex(ValueError,'UNFINISHED'):recovery.record_context_close(self.j,identifier,self.proof,now=10)
        self.j.min_free_bytes=10**20
        with self.assertRaises(OSError):recovery.record_context_close(self.j,identifier,self.proof,now=10)

    def test_tamper_does_not_close_and_new_product_does_not_inherit_recovery(self):
        identifier=self.prepare()
        recovery.record_context_close(self.j,identifier,self.proof,now=10)
        with self.j.db:self.j.db.execute("UPDATE service_state SET value='{}' WHERE key=?",('product_context_closed:'+identifier,))
        self.assertFalse(recovery.valid_context_close(self.j.db,identifier))
        self.r._restore_previous_product_identity()
        self.assertIsNotNone(self.r.prior_product_identity_block)

    def test_live_change_rolls_back_both_receipt_and_event(self):
        identifier=self.prepare()
        def changed():raise ValueError('PLC_CHANGED')
        with self.assertRaisesRegex(ValueError,'PLC_CHANGED'):
            recovery.record_context_close(self.j,identifier,self.proof,now=10,recheck=changed)
        self.assertFalse(recovery.valid_context_close(self.j.db,identifier))
        self.assertEqual(self.j.db.execute('SELECT count(*) FROM events WHERE event_type=?',(recovery.EVENT,)).fetchone()[0],0)

    def test_runtime_maintenance_then_reinserted_model_uses_new_inspection(self):
        old=self.prepare()
        self.g.s.update(self.proof['current'])
        now=self.now+self.at+.03
        self.g.s.update(generated=now,received=now)
        self.service.health=lambda:dict(self.proof['owners'],state='IDLE',error=None)
        self.r.assembly.status=lambda:dict(ready=True,active_identifier=None,pending=0,outstanding=0)
        with patch('src.runtime.standalone.time.monotonic',return_value=now):
            self.r.close_previous_product_context(old,'fixture','removed',self.proof['confirmations'])
        self.frame()  # Same model and bbox, but a new tracking session/request.
        new=self.request_and_complete(2,'REVIEW')
        self.assertNotEqual(old,new)
        self.assertEqual(self.g.result.call_count,2)
        self.assertIsNone(self.r.initial_approval)
        self.r._restore_previous_product_identity()
        self.assertEqual(self.r.prior_product_identity_block,'PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN')

    def test_reset_route_same_origin_no_code_and_disabled_by_default(self):
        from fastapi import FastAPI
        from notebook.tests.supervised_asgi_fixture import LocalAsgiClient
        from src.runtime.standalone_web import configure_line_web
        app=FastAPI();configure_line_web(app,self.r,{})
        path='/api/v1/maintenance/product-context/close'
        with LocalAsgiClient(app) as c:self.assertEqual(c.post(path,json={}).status_code,403)
        self.r.line_profile['maintenance_recovery']=dict(enabled=True,allowed_hosts=['testserver'])
        app=FastAPI();configure_line_web(app,self.r,{})
        self.assertFalse((self.j.root/'maintenance/web_pairing.json').exists())
        headers={'Origin':'http://testserver','Content-Type':'application/json'}
        with LocalAsgiClient(app) as c:
            self.assertEqual(c.post(path,json={},headers={}).status_code,403)
            self.assertEqual(c.post('/api/v1/runtime/start',json={},headers=headers).status_code,403)
            self.assertEqual(c.post(path,json={},headers=headers).status_code,409)
            self.assertNotIn('recovery-token',c.get('/line').text)
            self.assertEqual(c.get('/api/v1/line/consumed-frames').status_code,200)
            self.assertEqual(c.get('/line_details.js').status_code,200)
            self.assertNotIn('token',c.get('/api/v1/maintenance/product-context/status').text)
            for bad in [{'Origin':'http://other'}, {'Origin':'http://testserver','Host':'other'},
                        {'Origin':'http://testserver','Sec-Fetch-Site':'cross-site'},
                        {'Origin':'http://testserver','Content-Type':'text/plain'}]:
                self.assertEqual(c.post(path,json={},headers={**headers,**bad}).status_code,403)

    def test_ui_preflight_is_readonly_and_rechecks_stop_on_commit(self):
        identifier=self.prepare()
        self.g.s.update(self.proof['current'])
        now=self.now+self.at+.03
        self.g.s.update(generated=now,received=now)
        self.service.health=lambda:dict(self.proof['owners'],state='IDLE',error=None)
        self.r.assembly.status=lambda:dict(ready=True,active_identifier=None,pending=0,outstanding=0)
        before=self.j.db.total_changes
        with patch('src.runtime.standalone.time.monotonic',return_value=now):
            preflight=self.r.previous_product_recovery_status()
            self.assertTrue(preflight['eligible'],preflight)
            self.assertEqual(preflight['inspection_id'],identifier)
            self.assertEqual(before,self.j.db.total_changes)
            self.g.s['controls']['Mc_Run']=True
            with self.assertRaisesRegex(ValueError,'STOPPED'):
                self.r.close_previous_product_context(identifier,'operator','removed',self.proof['confirmations'])
            self.assertFalse(self.r.previous_product_recovery_status()['eligible'])
            self.assertEqual(before,self.j.db.total_changes)

    def test_preflight_keeps_worker_fault_and_unfinished_blockers(self):
        self.prepare()
        self.g.s.update(self.proof['current'])
        now=self.now+self.at+.03;self.g.s.update(generated=now,received=now)
        self.service.health=lambda:dict(self.proof['owners'],state='IDLE',error=None)
        self.r.assembly.status=lambda:dict(ready=True,active_identifier=None,pending=0,outstanding=0)
        with patch('src.runtime.standalone.time.monotonic',return_value=now):
            self.r.error='CAMERA_FAILURE'
            self.assertEqual(self.r.previous_product_recovery_status()['reason'],'OWNER_ERROR_BLOCKS_CONTEXT_RECOVERY')
            self.r.error=None
            self.j.admit(dict(cell_id='new',plc_session_id=9,request_id=1,cycle_id=1,attempt=1),{})
            self.assertIn('UNFINISHED',self.r.previous_product_recovery_status()['reason'])

if __name__=='__main__':unittest.main()
