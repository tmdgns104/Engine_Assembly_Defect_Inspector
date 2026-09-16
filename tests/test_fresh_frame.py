"""Deterministic contract checks. No camera, CUDA, or physical product claims."""

import math
import json
import unittest

from src.camera.fresh_frame import FreshFrameError, FreshFrameSelector, TriggerContext


def trigger(**changes):
    values = dict(trigger_id='T1', cell_id='test-cell', plc_session_id=1, cycle_id=101,
                  request_id=1, trigger_received_monotonic=10.0, trigger_source='LOCAL_TEST',
                  capture_epoch='camera-A', deadline_monotonic=12.0)
    return TriggerContext(**dict(values, **changes))


def frame(sequence=1, source=10.01, received=10.02, **changes):
    values = dict(frame_id=f'camera-A-{sequence}', sequence=sequence, source_pts_ns=sequence*33_000_000,
                  received_monotonic=received, estimated_source_monotonic=source,
                  received_at='2026-09-16T00:00:00+00:00', camera_epoch='camera-A')
    return dict(values, **changes)


def selector(**kwargs):
    return FreshFrameSelector(trigger(), {'boundary_epsilon_ms':0, 'max_trigger_to_frame_ms':2000,
                                         'inspection_window_ms':2000}, max_age_seconds=.35, **kwargs)


class FreshFrameTests(unittest.TestCase):
    def test_pre_trigger_and_exact_boundary_rejected(self):
        for source in (9.9, 10.0):
            choose = selector()
            self.assertIsNone(choose.consider(frame(source=source), 10.03))
            self.assertEqual(choose.rejected[-1]['reason'], 'PRE_TRIGGER')

    def test_immediately_after_trigger_accepted_with_truthful_metadata(self):
        chosen = selector().consider(frame(source=10.000001), 10.03)
        self.assertEqual(chosen['trigger_id'], 'T1')
        self.assertGreater(chosen['trigger_to_frame_ms'], 0)
        self.assertAlmostEqual(chosen['frame_age_at_select_ms'], 29.999)
        self.assertFalse(chosen['exposure_time_verified'])

    def test_same_sequence_and_equal_pts_rejected(self):
        for repeated in (frame(), frame(2, source_pts_ns=33_000_000)):
            choose = selector()
            choose.consider(frame(), 10.03)
            self.assertIsNone(choose.consider(repeated, 10.04))
            self.assertEqual(choose.rejected[-1]['reason'], 'DUPLICATE_FRAME')

    def test_pts_regression_aborts(self):
        choose = selector()
        choose.consider(frame(), 10.03)
        with self.assertRaisesRegex(FreshFrameError, 'PTS_REGRESSION'):
            choose.consider(frame(2, source_pts_ns=1), 10.04)

    def test_stale_uses_selection_age_not_capture_cached_age(self):
        choose = selector()
        self.assertIsNone(choose.consider(frame(age_seconds=0), 10.5))
        self.assertEqual(choose.rejected[-1]['reason'], 'STALE')

    def test_camera_epoch_change_aborts_even_with_fresh_timestamp(self):
        with self.assertRaisesRegex(FreshFrameError, 'CAMERA_EPOCH_CHANGED'):
            selector().consider(frame(camera_epoch='camera-B'), 10.03)

    def test_deadline_is_exclusive(self):
        for now in (12.0, 12.1):
            with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
                selector().consider(frame(source=11.9, received=11.95), now)

    def test_timeout_never_falls_back_or_revives(self):
        choose = selector()
        self.assertIsNone(choose.consider(frame(source=9.9), 10.03))
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            choose.check_active(12.0)
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            choose.consider(frame(2, source=12.1, received=12.11), 12.12)
        self.assertEqual(choose.selected, [])

    def test_cancel_before_late_frame_never_revives(self):
        choose = selector()
        with self.assertRaisesRegex(FreshFrameError, 'CANCELLED'):
            choose.consider(frame(), 10.03, cancelled=True)
        with self.assertRaisesRegex(FreshFrameError, 'CANCELLED'):
            choose.consider(frame(2), 10.04)
        self.assertEqual(choose.selected, [])

    def test_invalid_metadata_is_not_eligible(self):
        for changes in ({'sequence':True}, {'source_pts_ns':None}, {'camera_epoch':None},
                        {'estimated_source_monotonic':math.nan}, {'received_monotonic':11},
                        {'estimated_source_monotonic':10.5}, {'frame_id':''}):
            with self.subTest(changes=changes), self.assertRaisesRegex(FreshFrameError, 'FRAME_METADATA_INVALID'):
                selector().consider(frame(**changes), 10.03)

    def test_invalid_metadata_evidence_remains_json_safe(self):
        choose = selector()
        with self.assertRaises(FreshFrameError):
            choose.consider(frame(estimated_source_monotonic=math.nan), 10.03)
        json.dumps(choose.evidence(),allow_nan=False)

    def test_all_observations_must_fit_window_and_spacing(self):
        choose = selector(spacing_seconds=.15)
        choose.consider(frame(), 10.03)
        self.assertIsNone(choose.consider(frame(2, source=10.1, received=10.11),10.12))
        self.assertEqual(choose.rejected[-1]['reason'], 'OBSERVATION_SPACING')
        self.assertIsNotNone(choose.consider(frame(3, source=10.2, received=10.21),10.22))
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            choose.check_active(12.0)

    def test_no_unbounded_rejection_log(self):
        choose = selector()
        for seq in range(50):
            choose.consider(frame(seq,source=9.9),10.03)
        self.assertEqual(len(choose.rejected),32)
        self.assertEqual(choose.evidence()['rejection_metadata_truncated'],18)
        self.assertEqual(choose.rejection_counts['PRE_TRIGGER'],50)

    def test_explicit_epsilon_and_shortest_window(self):
        choose = FreshFrameSelector(trigger(), {'boundary_epsilon_ms':1,'max_trigger_to_frame_ms':100,
                                                'inspection_window_ms':50}, .35)
        self.assertIsNone(choose.consider(frame(source=10.0005),10.03))
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            choose.check_active(10.05)

    def test_external_clock_and_plc_source_not_supported(self):
        for changes in ({'trigger_source':'OMRON_PLC'}, {'request_id':True},
                        {'deadline_monotonic':math.inf}, {'capture_epoch':''}):
            with self.assertRaises(ValueError):
                trigger(**changes)


if __name__ == '__main__':
    unittest.main()
