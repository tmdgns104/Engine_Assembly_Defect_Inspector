"""Persist one nonexecuted ERROR without relaxing actual owner/fault checks."""
import threading
import time
import unittest
from unittest.mock import patch

from notebook.tests import test_request_start_runtime as fixture


class AdmissionObservationTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.RequestStartRuntimeTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.wait_for_admission_receipt_with_preview_miss()
        self.controller = self.case.controller
        self.context = self.controller.pending
        self.identifier = self.context['activation_receipt']['result']['inspection_id']
        self.original_trigger = self.context['reservation'].payload()['trigger']
        durable = self.context['activation_receipt']['durable_monotonic']
        self.context['deadline'] = (durable + time.monotonic()) / 2

    def assert_not_dispatched(self):
        self.assertTrue(self.case.service.commands.empty())
        self.assertIsNone(self.case.service.active)

    def test_observation_timeout_finishes_same_row_once_before_publication(self):
        c = self.case
        with patch.object(c.journal, 'admit', side_effect=AssertionError('second admission')):
            c.drain_pending()
        row = c.journal.detail(self.identifier)
        self.assertEqual(row['state'], 'COMPLETE')
        self.assertEqual(row['result']['decision'], 'ERROR')
        self.assertEqual(row['result']['reason_code'], 'ADMISSION_OBSERVATION_DEADLINE_EXCEEDED')
        self.assertEqual(row['result']['execution']['source'], 'not_executed')
        self.assertEqual(row['result']['observations'], [])
        self.assertEqual(row['result']['assets'], [])
        self.assertEqual(row['request']['runtime_binding']['plc_request_token'], c.r.handshake.token)
        self.assertEqual(c.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0], 1)
        c.r._commit_and_publish.assert_called_once()
        args, kwargs = c.r._commit_and_publish.call_args
        self.assertEqual(args[0], self.identifier)
        self.assertEqual(kwargs['durable_row']['state'], 'COMPLETE')
        self.assertIsNone(c.r.error)
        self.assert_not_dispatched()
        self.assertEqual(self.context['reservation'].payload()['trigger'], self.original_trigger)

    def test_STOP_at_observation_deadline_cancels_without_publication(self):
        c = self.case
        c.controls['Mc_Run'] = False
        c.drain_pending()
        self.assertEqual(c.r.error, 'REQUEST_STORAGE_CONTROL_CANCELLED')
        self.assertEqual(c.journal.detail(self.identifier)['state'], 'CANCELLED')
        c.r._commit_and_publish.assert_not_called()
        self.assert_not_dispatched()

    def test_slow_terminal_storage_does_not_renew_capture_or_publish_early(self):
        c = self.case
        entered, release = threading.Event(), threading.Event()
        original = c.journal.finish
        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('fixture terminal storage')
            return original(*args, **kwargs)
        try:
            with patch.object(c.journal, 'finish', side_effect=delayed):
                c.tick()
                self.assertTrue(entered.wait(1), 'terminal persistence was not submitted')
                terminal = self.controller.pending
                self.assertEqual(terminal['kind'], 'finish_no_input')
                self.assertGreater(terminal['deadline'], time.monotonic())
                self.assertLessEqual(terminal['deadline'] - terminal['started'],
                                     c.service.station['inspection_timeout_seconds'])
                for _ in range(25):
                    c.tick()
                    c.r._commit_and_publish.assert_not_called()
                    self.assertIsNone(c.r.error)
                    self.assertTrue(c.health_updates[-1][1])
                    self.assert_not_dispatched()
                    time.sleep(.02)
                gaps = [b[0]-a[0] for a, b in zip(c.health_updates, c.health_updates[1:])]
                self.assertLess(max(gaps), .4)
                release.set()
                c.drain_pending()
        finally:
            release.set()
        c.r._commit_and_publish.assert_called_once()

    def test_terminal_storage_failure_blocks_result_and_retains_original_id(self):
        c = self.case
        with patch.object(c.journal, 'finish', side_effect=OSError('fixture disk failure')) as finish:
            c.drain_pending()
            finish.assert_called_once()
        self.assertIsNotNone(c.r.error)
        c.r._commit_and_publish.assert_not_called()
        self.assertEqual(c.journal.db.execute('SELECT count(*) FROM inspections').fetchone()[0], 1)
        self.assertEqual(c.journal.detail(self.identifier)['state'], 'CANCELLED')
        self.assert_not_dispatched()

    def test_terminal_persistence_deadline_blocks_late_receipt(self):
        c = self.case
        entered, release = threading.Event(), threading.Event()
        original = c.journal.finish
        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('fixture terminal storage')
            return original(*args, **kwargs)
        try:
            with patch.object(c.journal, 'finish', side_effect=delayed):
                c.tick()
                self.assertTrue(entered.wait(1))
                self.controller.pending['deadline'] = time.monotonic() - .001
                c.tick()
                self.assertEqual(c.r.error, 'UNEXECUTED_COMPLETION_STORAGE_DEADLINE_EXCEEDED')
                release.set()
                c.drain_pending()
        finally:
            release.set()
        # Preserve the late durable ERROR, but never publish it after cancellation.
        self.assertEqual(c.journal.detail(self.identifier)['state'], 'COMPLETE')
        c.r._commit_and_publish.assert_not_called()
        self.assertEqual(c.r.aborted_inspection['inspection_id'], self.identifier)
        self.assert_not_dispatched()

    def test_terminal_STOP_blocks_late_durable_ERROR(self):
        c = self.case
        entered, release = threading.Event(), threading.Event()
        original = c.journal.finish
        def delayed(*args, **kwargs):
            entered.set()
            if not release.wait(2):
                raise TimeoutError('fixture terminal storage')
            return original(*args, **kwargs)
        try:
            with patch.object(c.journal, 'finish', side_effect=delayed):
                c.tick()
                self.assertTrue(entered.wait(1))
                c.controls['Stop_PB'] = False
                c.tick()
                self.assertEqual(c.r.error, 'REQUEST_STORAGE_CONTROL_CANCELLED')
                release.set()
                c.drain_pending()
        finally:
            release.set()
        c.r._commit_and_publish.assert_not_called()
        self.assert_not_dispatched()

    def test_changed_track_at_deadline_is_not_observation_error(self):
        c = self.case
        c.r.coordinator._tracker._track_id += 1
        c.drain_pending()
        self.assertEqual(c.r.error, 'ADMISSION_CURRENT_TRACK_OR_REQUEST_CHANGED')
        c.r._commit_and_publish.assert_not_called()
        self.assertEqual(c.journal.detail(self.identifier)['state'], 'CANCELLED')
        self.assert_not_dispatched()

    def test_admission_saved_after_original_deadline_remains_storage_failure(self):
        c = self.case
        self.context['deadline'] = self.context['activation_receipt']['durable_monotonic'] - .001
        c.drain_pending()
        self.assertEqual(c.r.error, 'REQUEST_STORAGE_DEADLINE_EXCEEDED')
        self.assertEqual(c.journal.detail(self.identifier)['state'], 'CANCELLED')
        c.r._commit_and_publish.assert_not_called()
        self.assert_not_dispatched()


if __name__ == '__main__':
    unittest.main()
