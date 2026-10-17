"""Synthetic camera packets through actual Tracking/Runtime/Journal, no hardware."""
import unittest
from unittest.mock import Mock, patch

from notebook.tests import test_full_frame_request as base
from src.runtime.standalone import AUTO_POLICY as POLICY
from src.runtime.production_profile import calibration_sha


class AutomaticRuntimeTests(unittest.TestCase):
    observe = base.RuntimeFixture.observe
    trigger = base.RuntimeFixture.trigger
    complete = base.RuntimeFixture.complete

    def setUp(self):
        base.RuntimeFixture.setUp(self)
        sha = calibration_sha(self.service.calibration)
        self.r.line_profile.update(cycle_admission=POLICY, initial_authorization=POLICY,
            field_profile_verified=True, automatic_operation_qualification=dict(verified=True,
                policy=POLICY, calibration_sha=sha, evidence='SYNTHETIC_ONLY', exit_edge='right',
                passage_policy='PRODUCT_TRAJECTORY_AND_EXIT_STRIP', unoccluded_exit_verified=True,
                sensor_cycle_source='QUALIFIED_PLC_REQUEST_LATCH', plc_logic_sha256='a'*64,
                plc_online_equivalence_verified=True, plc_timeout_stop_recovery_verified=True),
            clearance_qualification=dict(verified=False))
        self.r.plc_cycle = dict(policy=POLICY, software_permission_required=False)
        self.g.automatic_arm = Mock()
        self.g.set(self.now,'DISARMED',number=0,request=False,Mc_Run=False)
        self.g.s.update(result_count=0,done_count=0,completed_count=0,approval_id='')
        self.seq = 0
        self.at = 0
        self.frame()

    def frame(self, **kwargs):
        self.seq += 1
        self.at += .2
        kwargs.setdefault('area_class','UNKNOWN')
        return self.observe(self.seq,self.at,**kwargs)

    def poll(self):
        at=self.now+self.at+.03
        self.g.s.update(generated=at,received=at)
        with patch('src.runtime.standalone.time.monotonic',return_value=at):
            # This fixture drives steps instead of running the Runtime thread.
            # Join the actual bounded audit worker at both step boundaries.
            if getattr(self.r,'audit_pending',None):
                saved=self.service.storage.audit_completed.get(timeout=2)
                self.service.storage.audit_completed.put_nowait(saved)
                self.assertFalse(self.r._poll_completion_audit(at))
            self.r._poll_cyclic_plc(at)
            if getattr(self.r,'audit_pending',None):
                saved=self.service.storage.audit_completed.get(timeout=2)
                self.service.storage.audit_completed.put_nowait(saved)
                self.assertFalse(self.r._poll_completion_audit(at))
                self.r._poll_cyclic_plc(at)

    def request_and_complete(self, number, decision):
        self.poll()
        self.g.s.update(phase='IDLE')
        self.g.s['controls']['Mc_Run']=True
        self.poll()
        self.frame()
        self.g.s.update(phase='REQUEST_RECEIVED',transaction_settled=False,request_id=number,accepted_at=self.now+self.at+.02)
        self.g.s['controls']['Inspection_Request']=True
        self.poll()
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted),number,(self.r.issue,self.r.automatic_identity_block))
        with patch('src.runtime.standalone.time.monotonic',return_value=self.now+self.at+.1):
            identifier=self.complete(decision,offset=self.at+.1)
        self.g.s.update(phase='READY_NEXT',result_count=number,done_count=number,completed_count=number,transaction_settled=True)
        self.g.s['controls']['Inspection_Request']=False
        self.poll()
        return identifier

    def depart(self):
        for left,right in ((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.),(.8,1.),(.9,1.)):
            self.frame(box=dict(x1=left,y1=.1,x2=right,y2=.6))
            self.poll()
        for _ in range(20):
            # A different upstream engine is visible throughout the exit proof.
            self.frame(box=base.BOX)
            self.poll()
            if self.r.product_separation:
                self.frame()
                return
        self.fail(str((self.r.last_retirement,self.r.area_observation,self.r.plc_cycle)))

    def test_four_cycles_one_START_no_web_and_unique_products(self):
        identities=[]
        for number,decision in enumerate(('PASS','FAIL','REVIEW','ERROR'),1):
            identifier=self.request_and_complete(number,decision)
            row=self.j.detail(identifier)
            binding=row['request']['runtime_binding']
            identities.append((identifier,binding['cycle_id'],binding['plc_request_token']))
            self.assertEqual(self.r.history[0]['decision'],decision)
            self.assertEqual(self.r.history[0]['plc_result_value'],int(decision!='PASS'))
            if number<4:self.depart()
        for index in range(3):self.assertEqual(len({x[index] for x in identities}),4)
        self.assertEqual(self.g.result.call_count,4)
        self.assertEqual(self.g.automatic_arm.call_count,0)  # Ready to receive the next transaction.
        self.assertIsNone(self.r.initial_approval)

    def test_publication_during_short_detection_loss_keeps_bound_history(self):
        original = self.complete
        def complete_after_empty_frame(decision, **unused):
            for _ in range(3):
                self.frame(count=0)
            return original(decision, offset=self.at+.1)
        with patch.object(self, 'complete', side_effect=complete_after_empty_frame):
            identifier = self.request_and_complete(1, 'REVIEW')
        passage = self.r.product_passage
        self.assertEqual(passage.identity['inspection_id'], identifier)
        self.assertFalse(passage.invalid, passage.status())
        self.assertIsNone(passage.proof)
        self.assertEqual(len(self.r._passage_history), 0)
        self.depart()
        self.assertIsNotNone(self.r.product_separation)
        self.request_and_complete(2, 'REVIEW')
        self.assertEqual(self.g.result.call_count, 2)
        self.g.automatic_arm.assert_not_called()

    def test_foreign_box_during_inspection_cannot_prove_bound_product_exit(self):
        original = self.complete
        foreign = dict(x1=.1, y1=.65, x2=.7, y2=.95)
        def complete_after_foreign_box(decision, **unused):
            self.frame(box=foreign)
            for _ in range(3):
                self.frame(count=0)
            return original(decision, offset=self.at+.1)
        with patch.object(self, 'complete', side_effect=complete_after_foreign_box):
            self.request_and_complete(1, 'REVIEW')
        # REVIEW still returns NG. Invalid association only blocks exit proof.
        self.assertEqual(self.g.result.call_count, 1)
        self.assertEqual(self.r.history[0]['plc_result_value'], 1)
        self.assertTrue(self.r.product_passage.invalid)
        for left, right in ((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.),(.8,1.),(.9,1.)):
            self.frame(box=dict(x1=left, y1=.65, x2=right, y2=.95))
            self.poll()
        for _ in range(8):
            self.frame(count=0)
            self.poll()
        self.assertIsNone(self.r.product_separation)
        self.assertIsNone(self.r.product_passage.proof)

    def test_missing_bound_history_cannot_adopt_latest_box(self):
        original = self.complete
        def complete_without_history(decision, **unused):
            self.r._passage_history.clear()
            return original(decision, offset=self.at+.1)
        with patch.object(self, 'complete', side_effect=complete_without_history):
            self.request_and_complete(1, 'REVIEW')
        self.assertEqual(self.g.result.call_count, 1)
        self.assertTrue(self.r.product_passage.invalid)
        self.assertEqual(self.r.product_passage.reason,
                         'PRODUCT_PASSAGE_BOUND_HISTORY_UNAVAILABLE')

    def test_no_detection_or_global_match_is_not_product_exit(self):
        self.request_and_complete(1,'REVIEW')
        for classification in ('UNKNOWN','MATCH'):
            for _ in range(20):
                self.frame(count=0,area_class=classification)
                self.poll()
        # Transport rearmed, but AI admission remains blocked for that product.
        self.assertEqual(self.g.automatic_arm.call_count,0)
        self.assertIsNone(self.r.last_retirement)
        self.assertIsNone(self.r.product_separation)
        self.assertFalse(self.g.health[1])

    def test_qualification_is_not_inferred_from_policy_name(self):
        self.r.line_profile['automatic_operation_qualification']['verified']=False
        self.poll()
        self.g.automatic_arm.assert_not_called()
        self.assertTrue(self.r._profile_ready())
        self.assertFalse(self.r._automatic_readiness()['unattended_recovery_verified'])

    def test_retirement_from_other_identity_is_rejected(self):
        self.request_and_complete(1,'PASS')
        prior=self.r._supervised_settlement()
        self.r.last_retirement=dict(reason='EXIT_CONFIRMED',inspection_id='other',track_id=1,
            source_monotonic=self.now+self.at,cycle_id='other',tracking_session='other',
            camera_epoch='e',generation='g')
        with patch.object(self.r,'_clear',return_value=True):
            self.assertIsNone(self.r._automatic_exit_evidence(self.now+self.at+.1,prior))

    def next_request(self):
        self.g.s.update(phase='IDLE')
        self.poll()
        self.g.s.update(phase='REQUEST_RECEIVED',transaction_settled=False,request_id=2,accepted_at=self.now+self.at+.02)
        self.g.s['controls']['Inspection_Request']=True
        self.poll()

    def test_second_request_without_new_observation_gets_one_durable_ERROR_no_old_AI(self):
        first=self.request_and_complete(1,'PASS')
        self.next_request()
        self.assertIsNone(self.r.automatic_identity_block)
        self.trigger(self.at+1)
        self.assertEqual(len(self.submitted),1)
        with patch('src.runtime.standalone.time.monotonic',return_value=self.now+self.at+8.2):
            self.trigger(self.at+8.2)
            self.trigger(self.at+8.3)
        last=self.r.history[0]
        self.assertNotEqual(last['inspection_id'],first)
        self.assertEqual(last['decision'],'ERROR')
        self.assertEqual(last['plc_result_value'],1)
        self.assertEqual(last['source'],'NO_ACTUAL_INSPECTION')
        self.assertEqual(self.j.detail(last['inspection_id'])['state'],'COMPLETE')
        self.assertEqual(self.g.result.call_count,2)
        self.assertEqual(len(self.submitted),1)
        self.assertIsNone(self.r.product_passage)
        self.assertIsNotNone(self.r.previous_tracking_diagnostic['passage'])

    def test_STOP_blocks_late_ambiguous_result(self):
        self.request_and_complete(1,'PASS')
        self.next_request()
        self.g.s.update(phase='DISARMED',reason='PLC_CONTROL_INHIBIT')
        self.g.s['controls']['Mc_Run']=False
        self.poll()
        self.trigger(self.at+9)
        self.assertEqual(self.g.result.call_count,1)

    def test_separation_proof_spent_by_request_even_without_new_track(self):
        self.request_and_complete(1,'PASS')
        self.depart()
        self.assertIsNotNone(self.r.product_separation)
        self.next_request()
        self.assertIsNone(self.r.product_separation)
        self.assertIsNotNone(self.r.request_product_separation)
        self.assertIsNone(self.r.automatic_identity_block)

    def test_completed_cycle_STOP_release_keeps_exact_durable_settlement(self):
        identifier = self.request_and_complete(1, 'PASS')
        self.depart()
        self.poll()
        self.g.s.update(phase='DISARMED')
        self.g.s['controls'].update(Mc_Run=False, Stop_PB=False)
        self.poll()
        self.assertEqual(self.g.automatic_arm.call_count, 0)
        self.g.s['controls']['Stop_PB'] = True
        self.at += .2
        self.poll()
        self.assertEqual(self.g.automatic_arm.call_count, 0)
        self.assertEqual(self.r._automatic_previous['inspection_id'], identifier)
        self.assertIsNotNone(self.r.product_separation)
        self.g.automatic_arm.assert_not_called()
        self.assertEqual(self.g.result.call_count, 1)  # No replay on STOP/release.

    def test_retired_settlement_is_revalidated_from_journal(self):
        identifier = self.request_and_complete(1, 'PASS')
        self.depart()
        self.g.s.update(phase='DISARMED')
        self.g.s['controls']['Mc_Run'] = False
        # Test-only corruption must not turn cached completion into authority.
        with self.j.lock:
            self.j.db.execute('DELETE FROM service_state WHERE key=?',
                              ('integrated_decision:'+identifier,))
            self.j.db.commit()
        self.poll()
        self.assertEqual(self.g.automatic_arm.call_count, 0)
        self.assertFalse(self.r._supervised_settlement()['clean'])

    def test_prior_reversal_is_diagnostic_new_cycle_requires_new_observation(self):
        self.request_and_complete(1, 'PASS')
        boxes=((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.),(.8,1.),(.9,1.),
               (.8,1.),(.7,1.),(.6,1.),(.5,1.),(.4,1.),(.3,.9),(.2,.8),(.1,.7))
        for left,right in boxes:
            self.frame(box=dict(x1=left,y1=.1,x2=right,y2=.6))
            self.poll()
        for _ in range(9):
            self.frame()
            self.poll()
        self.assertIsNone(self.r.product_separation)
        self.assertTrue(self.r.product_passage.invalid)
        self.next_request()
        self.trigger(self.at+1)
        self.assertEqual(len(self.submitted),1)
        self.assertEqual(self.g.result.call_count,1)
        self.assertIsNone(self.r.automatic_identity_block)
        self.assertTrue(self.r.previous_tracking_diagnostic['passage']['invalid'])
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted),2)
        self.assertIsNone(self.r.request_product_separation)

    def test_restart_does_not_erase_unproven_product_identity(self):
        self.request_and_complete(1,'REVIEW')
        self.r._restore_previous_product_identity()
        self.assertEqual(self.r.prior_product_identity_block,'PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN')
        self.depart()
        self.r._restore_previous_product_identity()
        self.assertIsNone(self.r.prior_product_identity_block)

if __name__=='__main__':unittest.main()
