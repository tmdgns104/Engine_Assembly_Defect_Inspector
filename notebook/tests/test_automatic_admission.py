"""Automatic transport admission is independent of global image clearance."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.journal.sqlite import Journal
from src.runtime.automatic_admission import AutomaticAdmission, POLICY
from src.runtime.inspection_start import FULL_FRAME, start_policy
from src.runtime.standalone_web import configure_line_web, line_view


class AutomaticAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.j = Journal(Path(self.temp.name), min_free_bytes=0)
        self.addCleanup(self.j.close)
        self.g = Mock()
        self.g.runtime_session = 'a'*32
        self.a = AutomaticAdmission(self.g.runtime_session)
        self.prepare = Mock()
        self.s = dict(boot=1, connection=1, request_id=0, generated=1., received=1.,
            connected=True, fresh=True, run_idle=True, bool_valid=True,
            controls=dict(Inspection_Request=False, Mc_Run=False, EStop_OK=True, Stop_PB=True),
            phase='DISARMED', raw100='00000000', result_count=0, done_count=0,
            completed_count=0, approval_id='')
        self.settlement = dict(clean=True, previous=None)

    def poll(self, now=1., ready=True, evidence=None):
        self.s.update(generated=now, received=now)
        return self.a.poll(self.s, ready, 'epoch', 'worker', now, self.g, self.j,
            settlement=self.settlement, clearance=evidence, prepare=self.prepare)

    def test_first_stopped_baseline_without_web_or_empty_image(self):
        self.poll()
        self.g.automatic_arm.assert_called_once()
        self.assertEqual(self.a.state, 'WAIT_ADAPTER_ADMISSION')
        self.assertIsNone(self.prepare.call_args.args[0]['clearance'])
        self.poll(1.1)
        self.assertEqual(self.g.automatic_arm.call_count, 1)

    def test_boot_residue_and_running_state_cannot_arm(self):
        for key in ('Inspection_Request', 'Mc_Run'):
            self.s['controls'][key] = True
            self.poll()
            self.g.automatic_arm.assert_not_called()
            self.s['controls'][key] = False
        self.s['raw100'] = '00000100'
        self.poll()
        self.g.automatic_arm.assert_not_called()

    def test_transport_rearms_without_area_clear_but_requires_durable_reset(self):
        self.poll()
        grant = self.a.admission_id
        self.s.update(approval_id=grant, phase='IDLE')
        self.s['controls']['Mc_Run'] = True
        self.poll(1.1)
        self.s.update(phase='REQUEST_RECEIVED', request_id=1)
        self.poll(1.2)
        self.s.update(phase='READY_NEXT', result_count=1, done_count=1, completed_count=1)
        self.settlement['previous'] = dict(inspection_id='b'*32, request_token='0000000000000001:1:1', durable=True)
        self.s['controls']['Inspection_Request'] = True
        self.poll(1.3)
        self.assertEqual(self.g.automatic_arm.call_count, 1)
        self.s['controls']['Inspection_Request'] = False
        self.assertFalse(self.poll(1.4))
        self.assertEqual(self.g.automatic_arm.call_count, 2)
        self.assertNotEqual(self.a.admission_id, grant)
        self.assertIsNone(self.prepare.call_args.args[0]['clearance'])
        self.assertTrue(self.prepare.call_args.args[0]['transaction_admission_only'])

    def test_fault_or_connection_change_requires_stopped_baseline_again(self):
        self.poll()
        self.s.update(phase='DISARMED', connection=2)
        self.s['controls']['Mc_Run'] = True
        self.poll(1.1)
        self.assertEqual(self.g.automatic_arm.call_count, 1)
        self.s['controls']['Mc_Run'] = False
        self.poll(1.2)
        self.assertEqual(self.g.automatic_arm.call_count, 2)

    def test_unfinished_db_space_health_and_unsettled_block(self):
        self.poll(ready=False)
        self.g.automatic_arm.assert_not_called()
        self.settlement['clean'] = False
        self.poll()
        self.g.automatic_arm.assert_not_called()
        self.settlement['clean'] = True
        self.j.capacity = Mock(side_effect=OSError('disk'))
        self.poll()
        self.g.automatic_arm.assert_not_called()
        self.assertIn('JOURNAL', self.a.reason)

    def test_ambiguous_admission_is_not_retried(self):
        self.poll()
        self.poll(4.)
        self.poll(5.)
        self.assertEqual(self.g.automatic_arm.call_count, 1)
        self.assertEqual(self.a.reason, 'AUTOMATIC_ADMISSION_NOT_ACKNOWLEDGED')

    def test_unaccepted_HIGH_is_bounded_fault_not_fake_done(self):
        self.s['controls']['Inspection_Request']=True
        self.poll(1.)
        self.poll(3.1)
        self.assertTrue(self.a.failed)
        self.assertIn('PHYSICAL_STOP_REQUIRED',self.a.reason)
        self.g.automatic_arm.assert_not_called()
        self.g.result.assert_not_called()

    def test_admitted_sync_low_HIGH_is_bounded_with_fresh_heartbeat(self):
        self.poll(1.)
        self.s.update(approval_id=self.a.admission_id, phase='SYNC_LOW')
        self.s['controls'].update(Mc_Run=True, Inspection_Request=True)
        self.poll(1.1)
        self.assertFalse(self.a.failed)
        self.poll(3.2)
        self.assertTrue(self.a.failed)
        self.assertIn('PHYSICAL_STOP_REQUIRED', self.a.reason)
        self.g.cancel.assert_called_once()
        self.g.result.assert_not_called()
        self.assertEqual(self.g.automatic_arm.call_count, 1)

    def test_accepted_request_does_not_use_unaccepted_residue_timeout(self):
        self.poll(1.)
        self.s.update(approval_id=self.a.admission_id, phase='REQUEST_RECEIVED', request_id=1)
        self.s['controls'].update(Mc_Run=True, Inspection_Request=True)
        self.poll(1.1)
        self.poll(4.)
        self.assertFalse(self.a.failed)
        self.assertTrue(self.a.accepts(self.s))

    def test_mode_validation_requires_matching_authorization(self):
        p=dict(inspection_start_policy=FULL_FRAME, cycle_admission=POLICY,
            initial_authorization=POLICY, request_start_qualification={'verified':False})
        self.assertEqual(start_policy(p, 'OPENER_CYCLIC'), FULL_FRAME)
        p['initial_authorization']='SUPERVISED_REPEAT_TEST'
        with self.assertRaises(ValueError): start_policy(p, 'OPENER_CYCLIC')

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

    def test_admission_failure_overrides_product_wait_with_STOP_recovery(self):
        view=line_view(dict(automatic_admission=dict(failed=True,
            reason='UNACCEPTED_REQUEST_RESIDUE_TIMEOUT_PHYSICAL_STOP_REQUIRED',
            product_identity_reason='WAIT_OUTBOUND_PRODUCT_TRAJECTORY')), {})
        self.assertEqual(view['phase'],'ERROR')
        self.assertIn('현장 STOP',view['title'])
        self.assertIn('재송신을 차단',view['detail'])

if __name__ == '__main__': unittest.main()
