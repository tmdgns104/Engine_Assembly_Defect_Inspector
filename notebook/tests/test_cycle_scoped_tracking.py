"""PLC cycle admission vs visual identity; synthetic IPC, real Runtime/Journal.

The two Attempt06 boxes and their 68.011ms source interval are recorded values.
No fixture result is physical product identity, camera or PLC qualification.
"""
import unittest
from unittest.mock import patch

from notebook.tests import test_automatic_runtime as automatic
from notebook.tests.test_full_frame_request import packet
from src.runtime.product_passage import ProductPassage


class CycleScopedTrackingTests(unittest.TestCase):
    setUp = automatic.AutomaticRuntimeTests.setUp
    observe = automatic.AutomaticRuntimeTests.observe
    trigger = automatic.AutomaticRuntimeTests.trigger
    complete = automatic.AutomaticRuntimeTests.complete
    frame = automatic.AutomaticRuntimeTests.frame
    poll = automatic.AutomaticRuntimeTests.poll
    request_and_complete = automatic.AutomaticRuntimeTests.request_and_complete
    next_request = automatic.AutomaticRuntimeTests.next_request

    def recorded_failure(self):
        first = self.request_and_complete(1, 'PASS')
        self.seq = 4831
        self.at += .1
        seed = packet(self.seq, self.now+self.at,
            dict(x1=.3014363288879395, y1=.23697367774115669,
                 x2=.6791168212890625, y2=.6894932005140516))
        seed.update(width=1280, height=720)
        self.r.product_passage = ProductPassage(
            dict(inspection_id=first, request_token=self.r._automatic_previous['request_token']),
            seed, 'left', tracker_config=self.r.tracker_config)
        self.seq += 1
        self.at += .068011121
        self.observe(self.seq, self.at,
            dict(x1=.3018519639968872, y1=.2323891109890408,
                 x2=.7316105604171753, y2=.6892332712809245))
        self.assertTrue(self.r.product_passage.invalid)
        self.assertEqual(self.r.product_passage.reason, 'PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY')
        self.assertIsNone(self.r.product_passage.proof)
        return first

    def fresh_second_inspection(self):
        self.next_request()
        self.assertIsNone(self.r.automatic_identity_block)
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 2)
        first, second = (req['runtime_binding'] for req in self.submitted)
        self.assertNotEqual(first['plc_request_token'], second['plc_request_token'])
        self.assertNotEqual(first['runtime_session_id'], second['runtime_session_id'])
        self.assertNotEqual(first['trigger_frame_id'], second['trigger_frame_id'])
        self.assertFalse(self.r._clear(self.now+self.at))
        self.assertIsNone(self.r.request_product_separation)

    def test_attempt06_invalid_passage_does_not_poison_new_settled_cycle(self):
        first = self.recorded_failure()
        saved = self.j.detail(first)
        self.fresh_second_inspection()
        self.assertEqual(self.j.detail(first), saved)
        events = [row[0] for row in self.j.db.execute('SELECT event_type FROM events')]
        self.assertIn('PLC_CYCLE_OBSERVATION_WINDOW_STARTED', events)
        self.assertNotIn('AUTOMATIC_PRODUCT_SEPARATED', events)

    def test_next_request_before_visual_exit_reassesses_current_frame(self):
        self.request_and_complete(1, 'PASS')
        self.assertIsNotNone(self.r.product_passage)
        self.fresh_second_inspection()

    def test_diagnostic_failures_do_not_cross_cycle_boundary(self):
        for reason in ('PRODUCT_PASSAGE_FRAME_CONTINUITY_INVALID',
                       'PRODUCT_PASSAGE_REOBSERVATION_LIMIT',
                       'PRODUCT_PASSAGE_OCCLUSION_OR_AMBIGUITY'):
            with self.subTest(reason=reason):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.request_and_complete(1, 'PASS')
                f.r.product_passage._fail(reason)
                f.fresh_second_inspection()

    def test_without_post_request_frame_no_second_submission(self):
        self.recorded_failure()
        self.next_request()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 1)

    def test_duplicate_request_does_not_reset_or_submit_again(self):
        self.recorded_failure()
        self.fresh_second_inspection()
        session = self.r.session_id
        for _ in range(4):
            self.poll()
            self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 2)
        self.assertEqual(self.r.session_id, session)

    def test_unsettled_done_or_changed_connection_cannot_start_next_cycle(self):
        for key, value in (('completed_count', 0), ('done_count', 0), ('connection', 2), ('boot', 2)):
            with self.subTest(key=key):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.recorded_failure()
                f.g.s[key] = value
                f.next_request()
                f.frame()
                f.trigger(f.at+.1)
                self.assertEqual(len(f.submitted), 1)
                self.assertEqual(f.g.result.call_count, 1)

    def test_STOP_and_ESTOP_block_current_cycle_without_false_publication(self):
        for key in ('Mc_Run', 'Stop_PB', 'EStop_OK'):
            with self.subTest(key=key):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.recorded_failure()
                f.g.s['controls'][key] = False
                f.next_request()
                f.frame()
                f.trigger(f.at+.1)
                self.assertEqual(len(f.submitted), 1)
                self.assertEqual(f.g.result.call_count, 1)

    def test_durable_result_missing_blocks_next_cycle(self):
        identifier = self.recorded_failure()
        with self.j.lock:
            self.j.db.execute('DELETE FROM service_state WHERE key=?', ('integrated_decision:'+identifier,))
            self.j.db.commit()
        self.next_request()
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 1)
        self.assertEqual(self.g.result.call_count, 1)

    def test_past_observation_fault_cannot_cancel_published_result(self):
        self.request_and_complete(1, 'PASS')
        self.r._observation_issue('PRODUCT_OBSERVATION_GAP')
        self.assertIsNone(self.r.cycle_issue)
        self.assertEqual(self.r.history[0]['decision'], 'PASS')
        self.assertEqual(self.g.result.call_count, 1)
        self.fresh_second_inspection()

    def test_recorded_gap_and_ambiguous_observations_remain_invalid_only_in_old_passage(self):
        for change in ('gap', 'jump', 'ambiguity', 'size_growth', 'size_shrink'):
            with self.subTest(change=change):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.request_and_complete(1, 'PASS')
                p = f.r.product_passage
                q = packet(p.last['sequence']+1, p.last['monotonic_s']+.1)
                if change == 'gap':
                    q['sequence'] += 5
                    q['monotonic_s'] = p.last['monotonic_s']+.540017384
                elif change == 'jump':
                    q['provider']['observations'][0]['bbox'] = dict(x1=.8,y1=.1,x2=.95,y2=.6)
                elif change == 'ambiguity':
                    q['provider']['status'] = 'AMBIGUOUS_FOREGROUND'
                elif change == 'size_growth':
                    q['provider']['observations'][0]['bbox']['x2'] = .99
                else:
                    q['provider']['observations'][0]['bbox']['x2'] = .3
                q['processed_monotonic'] = q['monotonic_s']+.01
                p.observe(q,q['processed_monotonic'])
                self.assertIsNone(p.proof)
                if change in ('gap','jump','ambiguity'):
                    self.assertTrue(p.invalid)
                f.fresh_second_inspection()

    def test_current_camera_epoch_or_generation_change_is_still_system_fault(self):
        for key in ('camera_epoch', 'generation'):
            with self.subTest(key=key):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.recorded_failure()
                f.next_request()
                q = packet(f.seq+1, f.now+f.at+.2)
                q[key] = 'replacement'
                with patch('src.runtime.production.time.monotonic',return_value=q['monotonic_s']+.02):
                    f.r._apply_packet(q)
                self.assertIsNotNone(f.r.error)
                self.assertEqual(len(f.submitted), 1)
                self.assertEqual(f.g.result.call_count, 1)

    def test_current_link_storage_or_stale_start_cannot_admit_new_cycle(self):
        for cause in ('link','storage','pre_runtime_request'):
            with self.subTest(cause=cause):
                f = CycleScopedTrackingTests()
                f.setUp()
                self.addCleanup(f.doCleanups)
                f.recorded_failure()
                if cause == 'link':
                    f.g.s['connected'] = False
                elif cause == 'storage':
                    f.service.storage_pending = {'inspection_id':'pending'}
                else:
                    f.r._automatic_started_at = f.now+f.at+10
                f.next_request()
                f.frame()
                f.trigger(f.at+.1)
                self.assertEqual(len(f.submitted), 1)
                self.assertEqual(f.g.result.call_count, 1)

    def test_no_image_ERROR_is_scoped_to_its_cycle_and_next_cycle_can_inspect(self):
        self.request_and_complete(1, 'PASS')
        self.next_request()
        self.at += 8.3
        with patch('src.runtime.standalone.time.monotonic',return_value=self.now+self.at):
            self.trigger(self.at)
        error = self.r.history[0]
        self.assertEqual(error['decision'], 'ERROR')
        self.assertEqual(error['source'], 'NO_ACTUAL_INSPECTION')
        self.assertEqual(len(self.submitted), 1)
        self.g.s.update(phase='READY_NEXT',transaction_settled=True,
                        result_count=2,done_count=2,completed_count=2)
        self.g.s['controls']['Inspection_Request'] = False
        self.poll()
        self.g.s.update(phase='IDLE')
        self.poll()
        self.g.s.update(phase='REQUEST_RECEIVED',transaction_settled=False,
                        request_id=3,accepted_at=self.now+self.at+.02)
        self.g.s['controls']['Inspection_Request'] = True
        self.poll()
        self.frame()
        self.trigger(self.at+.1)
        self.assertEqual(len(self.submitted), 2)
        self.assertTrue(self.submitted[-1]['runtime_binding']['plc_request_token'].endswith(':3'))
        self.assertEqual(self.g.result.call_count, 2)  # Third result is not fabricated.


if __name__ == '__main__':
    unittest.main()
