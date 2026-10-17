"""Original trigger clocks, actual admission/health; no hardware or wall sleeps."""
import queue
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from notebook.tests import test_production_admission as fixtures


class CaptureProcessingDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProductionAdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.service = self.fixture.service
        self.service.station.update(inspection_timeout_seconds=15)
        self.service.station['fresh_frame'].update(max_trigger_to_frame_ms=3000, inspection_window_ms=3000)
        self.service.production_owner.inspection_motion_mode = 'STATIONARY'
        self.now = 100.
        clock = patch('time.monotonic', side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.renew(100.)

    def renew(self, now):
        self.now = now
        self.service.heartbeat.value = now
        self.service.preview_received = now

    def admit(self, delay):
        context = self.fixture.prepare()
        self.renew(100. + delay)
        saved = self.fixture.persist(context)
        self.service.activate_production_admission(context, saved)
        return self.service.commands.get_nowait()

    def test_durable_admission_never_restarts_capture_or_total_clock(self):
        active = self.admit(.6)
        self.assertEqual(active.get('capture_deadline'), 103.)
        self.assertEqual(active['deadline'], 115.)
        self.assertEqual(active['trigger']['trigger_received_monotonic'], 100.)

    def test_raw_storage_delays_across_capture_limit_keep_health(self):
        active = self.admit(.45)
        self.service.storage_pending = dict(active=active, generation=self.service.generation,
            camera_epoch='camera', started=102.95)
        self.service.storage = NS(thread=NS(is_alive=lambda: True), completed=queue.Queue())
        for delay in (.350, .450, .600, 1.):
            with self.subTest(storage_delay=delay):
                self.renew(102.95 + delay)
                self.assertIsNone(self.service.health()['error'])
        self.renew(115.001)
        self.assertEqual(self.service.health()['error'], 'STORAGE_DEADLINE_EXCEEDED')

    def storage_context(self):
        active = self.admit(.45)
        context = dict(active=active, generation=self.service.generation, camera_epoch='camera',
                       started=102.95, inspection_id=active['inspection_id'])
        self.service.storage_pending = context
        self.service.storage = NS(thread=NS(is_alive=lambda: True), completed=queue.Queue())
        self.service._fault = Mock()
        return context

    def test_durable_before_deadline_waiting_in_receipt_queue_is_not_expired(self):
        context = self.storage_context()
        context['durable_monotonic'] = 114.999
        self.service.storage.completed.put(dict(context=context, error=None, timing={}))
        self.renew(115.001)
        self.assertIsNone(self.service.health()['error'])
        self.service._storage_completions()
        self.service._fault.assert_not_called()
        self.assertEqual(self.service.state, 'IDLE')

    def test_late_storage_receipt_cannot_win_race_against_timeout(self):
        context = self.storage_context()
        context['durable_monotonic'] = 115.001
        self.service.storage.completed.put(dict(context=context, error=None, timing={}))
        self.renew(115.002)
        self.service._storage_completions()
        self.service._fault.assert_called_once_with('STORAGE_DEADLINE_EXCEEDED')

    def test_exact_total_boundary_is_expired(self):
        context = self.storage_context()
        context['durable_monotonic'] = 115.
        self.renew(115.)
        self.assertEqual(self.service.health()['error'], 'STORAGE_DEADLINE_EXCEEDED')

    def test_completed_receipt_cannot_mask_camera_or_writer_death(self):
        context = self.storage_context()
        context['durable_monotonic'] = 114.999
        self.renew(115.001)
        self.service.storage.thread.is_alive = lambda: False
        self.assertEqual(self.service.health()['error'], 'STORAGE_WORKER_EXITED')
        self.service.storage.thread.is_alive = lambda: True
        self.service.preview_received -= 3
        self.assertEqual(self.service.health()['error'], 'CAMERA_NOT_READY')

    def test_service_rejects_late_frame_despite_matching_request_and_durable_floor(self):
        active = self.admit(.45)
        self.renew(104.)
        floor = active['durable_admission_monotonic']
        def result(selected_at):
            frame = dict(frame_id='f1', sequence=1, camera_epoch='camera',
                estimated_source_monotonic=102.99, selected_at_monotonic=selected_at)
            return dict(decision='ERROR', observations=[dict(frame_id='f1', freshness=dict(frame))],
                fresh_frame=dict(trigger=active['trigger'], source_not_before_monotonic=floor,
                    effective_source_not_before_monotonic=floor, selected_frames=[dict(frame)]))
        self.assertIsNone(self.service._result_context_error(result(102.999)))
        for stamp in (103., 103.001, None, float('nan')):
            with self.subTest(selected=stamp):
                self.assertEqual(self.service._result_context_error(result(stamp)),
                                 'ADMISSION_FRAME_OUTSIDE_CAPTURE_WINDOW')


if __name__ == '__main__':
    unittest.main()
