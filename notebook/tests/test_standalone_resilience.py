"""Request-local failures must not kill acquisition or fabricate PLC results."""
from collections import deque
from pathlib import Path
from types import SimpleNamespace as NS
import sys
import tempfile
import queue
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'jetson'))
from src.runtime.standalone import StandaloneRuntime
from src.runtime.standalone_web import line_view
from src.journal.sqlite import Journal
from notebook.tests import test_legacy_standalone as fixtures
from notebook.tests.test_line_presentation import status


class RequestContinuityTests(unittest.TestCase):
    def test_review_and_error_wait_for_clear_without_global_transport_fault(self):
        for decision in ('REVIEW', 'ERROR'):
            g,h,events = fixtures.ExistingPlcCompatibilityTests().start_request()
            token = h.token
            h.publish('actual-inspection', decision, True, 2)
            self.assertEqual(h.state, 'WAIT_PRODUCT_CLEAR')
            self.assertEqual(h.publication, 'NOT_SENT')
            self.assertFalse(any(e['event']=='PLC_FAULT' for e in events))
            self.assertEqual(g.writes, [])
            for t,level in enumerate([False,True,False],3):
                g.request=level;h.poll(t)
            self.assertEqual(h.token, token)
            self.assertFalse(h.release_cleared_cycle(product_clear=False))
            self.assertTrue(h.release_cleared_cycle(product_clear=True))
            g.request=True;h.poll(6);h.bind('new-actual-inspection')
            h.publish('new-actual-inspection','FAIL',True,7)
            self.assertNotEqual(h.token,token)
            self.assertEqual(g.writes,[('Jetson_Result',True),('Jetson_Done',True)])

    def test_error_identity_durability_and_shutdown_still_gate_publication(self):
        g,h,_ = fixtures.ExistingPlcCompatibilityTests().start_request()
        with self.assertRaises(ValueError):h.publish('other','ERROR',True,2)
        with self.assertRaises(ValueError):h.publish('actual-inspection','ERROR',False,2)
        h.shutdown()
        h.publish('actual-inspection','ERROR',True,3)
        self.assertEqual(h.state,'RESYNC_REQUIRED')
        self.assertEqual(g.writes,[])


class RuntimeContinuityTests(unittest.TestCase):
    def runtime(self):
        r=fixtures.ExistingPlcRuntimeTests().runtime()
        del r._fault
        r.bridge=NS(inspection_id=None)
        r.area_window=NS(reset=Mock())
        r.area_observation=None
        r._clear=Mock(return_value=False)
        r.issue=None;r.cycle_issue=None;r.inspected_tracks=set()
        r._replace_tracking_session=Mock()
        r._reset_departure_candidate=Mock()
        r.history=deque();r.published_ids=set()
        r.service.cancel=Mock();r.service.error=None;r.service.state='IDLE'
        r._poll_plc(0)
        return r

    def test_unbound_preview_loss_reacquires_without_faulting_plc(self):
        r=self.runtime()
        r._fault('TRACK_ASSOCIATION_OR_GAP_LOST')
        self.assertTrue(r.operating)
        self.assertIsNone(r.error)
        self.assertEqual(r.handshake.state,'ARMED')
        r._replace_tracking_session.assert_called_once()
        self.assertEqual(r.issue['scope'],'UNBOUND_PREVIEW')
        r.gateway.request=True;r._poll_plc(1)
        self.assertEqual(r.handshake.state,'REQUEST_LATCHED')
        self.assertEqual(r.gateway.writes,[])

    def test_bound_track_loss_cancels_current_worker_without_reusing_pose(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r.handshake.bind('same-request')
        r.bridge.inspection_id='same-request'
        r.service.active={'inspection_id':'same-request'}
        r._fault('TRACK_ASSOCIATION_OR_GAP_LOST')
        r._fault('TRACK_ASSOCIATION_OR_GAP_LOST')
        self.assertTrue(r.operating)
        self.assertIsNone(r.error)
        r._replace_tracking_session.assert_not_called()
        r.service.cancel.assert_called_once_with('same-request')
        self.assertNotIn('same-request',r.published_ids)
        self.assertEqual(r.cycle_issue['request_token'],r.handshake.token)
        self.assertEqual(r.gateway.writes,[])

    def test_configuration_and_explicit_stop_are_not_auto_reset(self):
        for reason in ('PACKAGE_CHANGED','LOCAL_MAINTENANCE_HOLD','JOURNAL_UNAVAILABLE'):
            r=self.runtime();r._fault(reason)
            self.assertFalse(r.operating)
            self.assertEqual(r.error,reason)
            r._replace_tracking_session.assert_not_called()

    def test_request_withdrawal_then_track_loss_keeps_polling(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r.gateway.request=False;r._poll_plc(2)
        self.assertEqual(r.handshake.state,'WAIT_PRODUCT_CLEAR')
        r._fault('TRACK_ASSOCIATION_OR_GAP_LOST')
        for t in range(3,23):r._poll_plc(t)
        self.assertTrue(r.operating)
        self.assertIsNone(r.error)
        self.assertEqual(r.handshake.state,'WAIT_PRODUCT_CLEAR')
        r._replace_tracking_session.assert_not_called()
        self.assertEqual(r.gateway.writes,[])

    def test_real_runtime_loop_continues_after_unbound_observation_failure(self):
        r=self.runtime()
        r.configured=threading.Event();r.configured.set()
        r.stop=threading.Event();r.lock=threading.RLock();r.closing=False
        r.service.lock=threading.RLock();r.service.products=queue.Queue()
        r.service.health_diagnostics=Mock()
        r.service.journal=Mock(lock=threading.RLock())
        r.service.products.put({'fixture':'one failing observation'})
        r._packet=lambda packet:r._fault('TRACK_ASSOCIATION_OR_GAP_LOST')
        r._acquisition=Mock();r._poll_result=Mock();r._trigger=Mock()
        r.observation_started_at=None;r.logger=Mock()
        attempts=[]
        def poll(now):
            attempts.append(r.operating)
            if len(attempts)==5:r.stop.set()
        r._poll_plc=poll
        worker=threading.Thread(target=r._run)
        worker.start();worker.join(2)
        try:
            self.assertFalse(worker.is_alive())
            self.assertEqual(attempts,[True]*5)
            self.assertEqual(r._trigger.call_count,5)
            self.assertIsNone(r.error)
            r.logger.exception.assert_not_called()
        finally:r.stop.set();worker.join(1)

    def test_unready_request_gets_bounded_error_instead_of_waiting_forever(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r._profile_ready=lambda:False
        r._finish_without_frames=Mock()
        r._trigger(30)
        r._finish_without_frames.assert_not_called()
        r._trigger(31)
        r._finish_without_frames.assert_called_once_with('ERROR','FIELD_PROFILE_NOT_VERIFIED',31)

    def test_assembly_exception_yields_error_without_killing_acquisition(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r.handshake.bind('actual')
        r.bridge=NS(inspection_id='actual',poll=lambda:None,error=None,phase='INSPECTION_DURABLE')
        r.service.journal=NS(detail=lambda i:{'decision':'PASS'})
        r.assembly=NS(submit=Mock(side_effect=RuntimeError('classification worker failure')),
                      result=lambda i:None,evidence_path=lambda i:'fixture')
        r.assembly_submitted={};r.line_profile['assembly_deadline_s']=30
        r._commit_and_publish=Mock()
        r._poll_result(2)
        self.assertEqual(r._commit_and_publish.call_args.args[1]['decision'],'ERROR')
        self.assertTrue(r.operating)
        self.assertIsNone(r.error)

    def test_ui_separates_process_alive_from_cycle_hold(self):
        s=status();s['runtime_issue']={'scope':'REQUEST','reason':'TRACK_LOST','active':True}
        s['runtime_loop_alive']=True
        v=line_view(s,{})
        self.assertTrue(v['runtime_loop_alive'])
        self.assertEqual(v['issue']['reason'],'TRACK_LOST')
        self.assertEqual(v['verdict'],'NOT_RUN')

    def test_hold_never_clears_on_sensor_off_or_unverified_absence(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r.cycle_issue={'monotonic_s':2,'request_token':r.handshake.token}
        r.area_config_version='frozen';r.area_observation={'state':'UNKNOWN'}
        r._absence_ready=lambda:True;r._area_approval_current=lambda a:False
        self.assertTrue(r._observation_hold({'frame_id':'new'},None))
        r._replace_tracking_session.assert_not_called()
        self.assertEqual(r.handshake.state,'REQUEST_LATCHED')

    def test_cleared_fault_retires_only_after_fresh_area_and_idle_tags(self):
        r=self.runtime();r.gateway.request=True;r._poll_plc(1)
        r.handshake.bind('failed');r.handshake.publish('failed','ERROR',True,2)
        r.cycle_issue={'monotonic_s':2,'request_token':r.handshake.token}
        r.area_config_version='frozen'
        r.area_observation={'state':'CLEAR','first_clear_monotonic':3}
        r._absence_ready=lambda:True;r._area_approval_current=lambda a:True
        r._observation_hold({'frame_id':'fresh-clear'},None)
        r._replace_tracking_session.assert_not_called()  # Request still HIGH.
        r.gateway.request=False
        r._observation_hold({'frame_id':'fresh-clear'},None)
        r._replace_tracking_session.assert_called_once()
        self.assertIsNone(r.cycle_issue)
        self.assertFalse(r.issue['active'])
        self.assertEqual(r.handshake.state,'ARMED')
        self.assertEqual(r.gateway.writes,[])


class DurableRequestOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal=Journal(Path(self.temp.name),min_free_bytes=0)
        self.addCleanup(self.journal.close)
        self.r=RuntimeContinuityTests().runtime()
        r=self.r
        r.service.journal=self.journal
        r.service.allocate_request=lambda:dict(cell_id='fixture',plc_session_id=1,request_id=1,cycle_id=1,attempt=1)
        r.service.package=NS(snapshot=lambda:{'manifest':{'product_id':'engine','release_id':'fixture'}})
        r.session_id='fixture-session';r.assembly_submitted={}
        r.gateway.request=True;r._poll_plc(1)

    def test_unready_request_records_exactly_one_error_and_no_plc_write(self):
        r=self.r;r._profile_ready=lambda:False
        r._trigger(31);r._trigger(32)
        self.assertEqual(len(r.history),1)
        result=r.history[0]
        self.assertEqual(result['decision'],'ERROR')
        self.assertEqual(result['reason'],'FIELD_PROFILE_NOT_VERIFIED')
        self.assertEqual(result['publication_status'],'NOT_SENT')
        self.assertTrue(self.journal.detail(result['inspection_id'])['result']['storage_success'])
        self.assertEqual(r.gateway.writes,[])
        self.assertTrue(r.operating)

    def test_late_saved_result_after_track_fault_is_request_error_only(self):
        r=self.r
        request=r.service.allocate_request()
        request['runtime_binding']={'plc_request_token':r.handshake.token}
        identifier,_=self.journal.admit(request,r.service.package.snapshot())
        self.journal.finish(identifier,{'decision':'ERROR','reason':'worker cancelled'})
        r.handshake.bind(identifier)
        r.bridge=NS(inspection_id=identifier)
        r.cycle_issue={'request_token':r.handshake.token,'reason':'TRACK_ASSOCIATION_OR_GAP_LOST'}
        r._poll_result(2);r._poll_result(3)
        self.assertEqual(len(r.history),1)
        self.assertEqual(r.history[0]['decision'],'ERROR')
        self.assertEqual(r.gateway.writes,[])
        self.assertTrue(r.operating)

    def test_actual_component_fields_are_visible_without_changing_truth(self):
        s=status()
        s['history']=[dict(source='INTEGRATED_ACTUAL_INSPECTION',synthetic=False,
            decision='FAIL',existing_decision='PASS',assembly_decision='FAIL')]
        v=line_view(s,{})
        self.assertEqual(v['last_result']['existing_inspector'],'PASS')
        self.assertEqual(v['last_result']['assembly_inspector'],'FAIL')
        self.assertEqual(s['history'][0]['decision'],'FAIL')

    def test_cancelled_journal_record_becomes_visible_error_not_infinite_wait(self):
        r=self.r
        request=r.service.allocate_request()
        request['runtime_binding']={'plc_request_token':r.handshake.token}
        identifier,_=self.journal.admit(request,r.service.package.snapshot())
        self.journal.cancel(identifier,'CANCELLED_OR_EXPIRED')
        r.handshake.bind(identifier)
        r.bridge=NS(inspection_id=identifier)
        r.cycle_issue={'request_token':r.handshake.token,'reason':'TRACK_ASSOCIATION_OR_GAP_LOST'}
        r._poll_result(2)
        self.assertEqual(len(r.history),1)
        self.assertEqual(r.history[0]['decision'],'ERROR')
        self.assertEqual(self.journal.detail(identifier)['state'],'CANCELLED')
        self.assertEqual(r.gateway.writes,[])
        with self.assertRaises(ValueError):
            r._commit_and_publish(identifier,{'decision':'PASS'},3)


if __name__=='__main__':unittest.main()
