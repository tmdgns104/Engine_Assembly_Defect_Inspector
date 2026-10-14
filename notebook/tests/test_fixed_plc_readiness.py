"""No PLC response timer or per-product permission is added by readiness."""
import unittest
from notebook.tests.test_automatic_runtime import AutomaticRuntimeTests


class FixedPlcReadinessTests(unittest.TestCase):
    setUp = AutomaticRuntimeTests.setUp
    frame = AutomaticRuntimeTests.frame
    observe = AutomaticRuntimeTests.observe

    def test_unattended_recovery_is_not_normal_inspection_permission(self):
        q = self.r.line_profile['automatic_operation_qualification']
        q.update(verified=False, plc_timeout_stop_recovery_verified=False,
                 plc_online_equivalence_verified=False, unoccluded_exit_verified=False)
        self.r.line_profile['field_profile_verified'] = False
        self.assertTrue(self.r._profile_ready())
        readiness = self.r._automatic_readiness()
        self.assertFalse(readiness['unattended_recovery_verified'])
        self.assertIn('PLC_TIMEOUT_STOP_RECOVERY_UNVERIFIED', readiness['field_limits'])
        self.assertFalse(readiness['software_permission_required'])

    def test_geometry_or_calibration_mismatch_still_blocks(self):
        q = self.r.line_profile['automatic_operation_qualification']
        q['exit_edge'] = 'unknown'
        self.assertFalse(self.r._profile_ready())
        q['exit_edge'] = 'right'
        q['calibration_sha'] = '0'*64
        self.assertFalse(self.r._profile_ready())

    def test_trace_is_actual_consumption_bounded_and_does_not_change_packet(self):
        import copy
        from notebook.tests.test_full_frame_request import packet
        from unittest.mock import patch
        p = packet(3, self.now+.5)
        before = copy.deepcopy(p)
        with patch('src.runtime.production.time.monotonic', return_value=self.now+.51):
            self.r._packet(p)
        self.assertEqual(p, before)
        trace = self.r.consumed_frames.snapshot()
        self.assertEqual(trace['frames'][-1]['frame_id'], p['frame_id'])
        self.assertEqual(trace['frames'][-1]['sequence'], 3)
        for _ in range(1100): self.r.consumed_frames.record(p, consumed_at=self.now+.51)
        self.assertEqual(len(self.r.consumed_frames.snapshot()['frames']), 1024)

if __name__ == '__main__': unittest.main()
