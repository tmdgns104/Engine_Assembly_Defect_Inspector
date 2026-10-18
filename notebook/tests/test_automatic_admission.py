"""PLC-owned cycles: readiness checks never create application permissions."""
import unittest
from unittest.mock import Mock, patch
from notebook.tests import test_full_frame_request as base
from src.runtime.standalone import AUTO_POLICY as POLICY
from src.runtime.inspection_start import FULL_FRAME, start_policy
from src.runtime.standalone_web import configure_line_web, line_view

class AutomaticAdmissionTests(unittest.TestCase):
    def setUp(self):
        base.RuntimeFixture.setUp(self)
        self.r.line_profile['cycle_admission'] = POLICY
        self.r.plc_cycle = dict(policy=POLICY)
        self.g.set(self.now,'DISARMED',number=0,request=False,Mc_Run=False)
        self.g.s.update(result_count=0,done_count=0,completed_count=0)
        self.g.cancel=Mock()

    def poll(self,offset=0,ready=True):
        now=self.now+offset
        self.g.s.update(generated=now,received=now)
        return self.r._automatic_health(self.g.s,ready,now)

    def test_initial_healthy_state_creates_no_permission(self):
        self.assertTrue(self.poll())
        self.assertIsNone(self.r.initial_approval)
        self.assertFalse(hasattr(self.r,'automatic_admission'))
        self.assertFalse((self.j.root/'first-product-approval').exists())
        self.g.result.assert_not_called()

    def test_readiness_is_not_a_start_or_clearance_signal(self):
        for key in ('Inspection_Request','Mc_Run'):
            self.g.s['controls'][key]=True
            self.poll()
        self.g.result.assert_not_called()
        self.assertIsNone(self.r.product_separation)

    def test_unfinished_journal_blocks(self):
        with patch.object(self.r._journal_readiness,'count',return_value=1):
            self.assertFalse(self.poll())
        self.assertEqual(self.r.plc_cycle['reason'],'JOURNAL_UNFINISHED_INSPECTION')

    def test_storage_error_blocks(self):
        with patch.object(self.j,'capacity',side_effect=OSError('disk')):
            self.assertFalse(self.poll())
        self.assertIn('STORAGE_NOT_READY',self.r.plc_cycle['reason'])

    def test_db_integrity_error_blocks(self):
        with patch.object(self.r._journal_readiness,'count',side_effect=ValueError('integrity')):
            self.assertFalse(self.poll())
        self.g.result.assert_not_called()

    def test_health_or_stale_connection_blocks(self):
        self.assertFalse(self.poll(ready=False))
        for key in ('connected','fresh','bool_valid','run_idle'):
            self.g.s[key]=False
            self.assertFalse(self.poll())
            self.g.s[key]=True

    def test_unsettled_previous_result_blocks(self):
        with patch.object(self.r,'_supervised_settlement',return_value=dict(clean=False,reason='UNSETTLED')):
            self.assertFalse(self.poll())
        self.assertEqual(self.r.plc_cycle['reason'],'UNSETTLED')

    def test_unaccepted_residue_times_out_without_result(self):
        self.g.s['controls']['Inspection_Request']=True
        self.poll()
        self.assertFalse(self.poll(2.1))
        self.g.cancel.assert_called_once()
        self.g.result.assert_not_called()
        self.assertIn('PHYSICAL_STOP_REQUIRED',self.r.plc_cycle['reason'])

    def test_valid_busy_storage_is_healthy_without_SQL_wait(self):
        self.r.final_pending={'inspection_id':'busy'}
        self.g.s['phase']='REQUEST_RECEIVED'
        with patch.object(self.r._journal_readiness,'count',side_effect=AssertionError('must not lock')):
            self.assertTrue(self.poll(4))
        self.g.cancel.assert_not_called()

    def test_mode_does_not_require_initial_authorization(self):
        p=dict(inspection_start_policy=FULL_FRAME,cycle_admission=POLICY,
            request_start_qualification={'verified':False})
        self.assertEqual(start_policy(p,'OPENER_CYCLIC'),FULL_FRAME)
        self.assertNotIn('initial_authorization',p)
        p['initial_authorization']='SUPERVISED_REPEAT_TEST'
        with self.assertRaises(ValueError): start_policy(p,'OPENER_CYCLIC')

    def test_monitor_contains_no_pairing_checks_or_mutation_script(self):
        from fastapi import FastAPI
        from notebook.tests.supervised_asgi_fixture import LocalAsgiClient
        r=Mock(line_profile={})
        app=FastAPI();configure_line_web(app,r,{})
        with LocalAsgiClient(app) as c:
            html=c.get('/line').text
            for value in ('운영자 연결 코드', '이 탭에 연결', 'type="checkbox"', "method:'POST'", 'sessionStorage'):
                self.assertNotIn(value,html)
            self.assertEqual(c.get('/auto',follow_redirects=False).headers['location'], '/line')
            self.assertEqual(c.post('/api/v1/line/supervised/prepare',json={}).status_code,403)


    def test_previous_product_reason_is_not_a_current_inspection_ng(self):
        view=line_view(dict(latest_frame={'frame_id':'x'},inspection_service={'camera_ready':True},
            plc={'available':True},plc_cycle=dict(product_identity_reason='UNPROVEN')), {})
        # A previous-product observation is not a saved inspection or PLC NG.
        self.assertEqual(view['phase'],'WAIT_PRODUCT_MOVEMENT')
        self.assertEqual(view['verdict'],'NOT_RUN')
        self.assertIn('UNPROVEN',view['detail'])
        self.assertIsNone(view['current_inspection_id'])
        self.assertIsNone(view['last_result'])
        self.assertEqual(view['plc']['publication_status'],'NOT_STARTED')

if __name__=='__main__':unittest.main()
