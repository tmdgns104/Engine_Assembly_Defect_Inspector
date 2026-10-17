"""A durable admission cannot select frames buffered while its commit waited."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.camera.fresh_frame import FreshFrameError, FreshFrameSelector, TriggerContext


def trigger():
    return TriggerContext('trigger', 'cell', 1, 1, 1, 10., 'LOCAL_TEST', 'camera', 15.)


CONFIG = dict(boundary_epsilon_ms=1, max_trigger_to_frame_ms=2000,
              inspection_window_ms=3000)


def frame(source, sequence=1):
    return dict(frame_id=f'frame-{sequence}', camera_epoch='camera', sequence=sequence,
                source_pts_ns=int(source * 1e9), estimated_source_monotonic=source,
                received_monotonic=source + .01, received_at='2026-10-16T00:00:00Z')


class AdmissionFrameFloorTests(unittest.TestCase):
    def selector(self, floor):
        try:
            return FreshFrameSelector(trigger(), CONFIG, 2., source_not_before=floor)
        except TypeError as error:
            self.fail(f'Post-durability frame floor is missing: {error}')

    def test_buffered_frame_after_request_but_before_commit_is_rejected(self):
        selector = self.selector(10.55)
        # The 550 ms commit completed, but capture returns an older buffered image.
        self.assertIsNone(selector.consider(frame(10.4), 10.6))
        self.assertEqual(selector.rejection_counts['PRE_SOURCE_NOT_BEFORE'], 1)
        selected = selector.consider(frame(10.56, 2), 10.6)
        self.assertEqual(selected['frame_id'], 'frame-2')
        evidence = selector.evidence()
        self.assertEqual(evidence['trigger'], trigger().to_dict())
        self.assertEqual(evidence['source_not_before_monotonic'], 10.55)
        self.assertEqual(evidence['effective_source_not_before_monotonic'], 10.55)
        self.assertEqual([item['frame_id'] for item in evidence['selected_frames']], ['frame-2'])

    def test_commit_boundary_and_epsilon_are_not_fresh_frames(self):
        selector = self.selector(10.55)
        for sequence, source in enumerate((10.55, 10.5505), 1):
            self.assertIsNone(selector.consider(frame(source, sequence), 10.6))
        self.assertEqual(selector.rejection_counts['PRE_SOURCE_NOT_BEFORE'], 2)

    def test_earlier_floor_cannot_relax_original_trigger_boundary(self):
        selector = self.selector(9.)
        self.assertIsNone(selector.consider(frame(10.), 10.1))
        self.assertEqual(selector.rejection_counts['PRE_TRIGGER'], 1)
        self.assertEqual(selector.evidence()['effective_source_not_before_monotonic'], 10.)
        self.assertIsNotNone(selector.consider(frame(10.02, 2), 10.1))

    def test_slow_admission_does_not_restart_or_extend_deadline(self):
        selector = self.selector(11.9)
        self.assertEqual(selector.deadline, 12.)
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            selector.consider(frame(11.95), 12.)
        self.assertEqual(selector.evidence()['selected_frames'], [])

    def test_admission_later_than_deadline_never_selects_a_frame(self):
        selector = self.selector(12.5)
        with self.assertRaisesRegex(FreshFrameError, 'DEADLINE_EXCEEDED'):
            selector.consider(frame(12.6), 12.7)
        self.assertEqual(selector.deadline, 12.)

    def test_invalid_floor_fails_closed(self):
        for floor in (True, False, '10.5', float('nan'), float('inf'), -1.):
            with self.subTest(floor=repr(floor)):
                with self.assertRaisesRegex(ValueError, 'SOURCE_NOT_BEFORE_INVALID'):
                    self.selector(floor)

    def test_no_floor_preserves_original_selection_and_evidence(self):
        omitted = FreshFrameSelector(trigger(), CONFIG, 2.)
        explicit_none = FreshFrameSelector(trigger(), CONFIG, 2., source_not_before=None)
        for selector in (omitted, explicit_none):
            self.assertIsNone(selector.consider(frame(10.), 10.1))
            self.assertIsNotNone(selector.consider(frame(10.02, 2), 10.1))
        self.assertEqual(omitted.evidence(), explicit_none.evidence())
        self.assertNotIn('source_not_before_monotonic', omitted.evidence())

    def test_cancellation_still_prevents_post_commit_selection(self):
        selector = self.selector(10.55)
        with self.assertRaisesRegex(FreshFrameError, 'CANCELLED'):
            selector.consider(frame(10.6), 10.7, cancelled=True)
        self.assertEqual(selector.evidence()['selected_frames'], [])


class AdmissionFrameFloorWorkerTests(unittest.TestCase):
    def test_existing_worker_does_not_infer_buffered_pre_commit_frame(self):
        from datetime import datetime, timezone
        import queue
        import threading
        import time
        from types import SimpleNamespace
        from unittest.mock import patch
        import numpy as np
        from src.contracts import CameraFrame
        from src.vision.inspection_worker import worker_main

        started = time.monotonic()
        durable = started - .3
        saved_trigger = TriggerContext('trigger', 'cell', 1, 1, 1, started - 1.,
                                       'LOCAL_TEST', 'camera', started + 3.).to_dict()
        stopping, cancellation = threading.Event(), threading.Event()
        commands, previews = queue.Queue(), queue.Queue(maxsize=1)
        detected_ids = []

        class Camera:
            def __init__(self, config):
                self.sequence = 0
                self.pipeline_text = 'SYNTHETIC_ADMISSION_FLOOR'

            def capture(self):
                self.sequence += 1
                # First two frames initialize camera/preview. Inspection sees
                # an older buffered frame, then a genuinely post-commit frame.
                source = durable - .1 if self.sequence <= 3 else durable + .1
                self.frame_info = dict(frame(source, self.sequence), age_seconds=.4)
                image = np.full((16, 16, 3), self.sequence, np.uint8)
                return CameraFrame(image, f'frame-{self.sequence}',
                    datetime.now(timezone.utc), 16, 16, 'synthetic')

            def close(self):
                pass

        class Detector:
            def runtime_metadata(self):
                return {'backend': 'synthetic'}

            def detect(self, image):
                detected_ids.append(image.frame_id)
                return SimpleNamespace(to_dict=lambda: dict(frame_id=image.frame_id,
                    detections=[], inference_ms=0., model_version='synthetic'))

            def close(self):
                pass

        class Results(queue.Queue):
            def put(self, item, *args, **kwargs):
                super().put(item, *args, **kwargs)
                if item['type'] in ('result', 'fault'):
                    stopping.set()

        results = Results()
        package = SimpleNamespace(manifest={'files': {}, 'model_version': 'synthetic'},
            manifest_hash='synthetic', capture={}, recipe={'observation_count': 1})
        station = dict(camera_device='SYNTHETIC', fresh_frame=CONFIG,
            max_frame_age_seconds=2., frame_spacing_seconds=0.,
            quality=dict(min_blur_variance=0, min_mean_brightness=0, max_mean_brightness=255))
        commands.put(dict(inspection_id='inspection', request=dict(kind='inspect', view_assessment={}),
            accepted_monotonic=started - 1., deadline=started + 3., trigger=saved_trigger,
            durable_admission_monotonic=durable))
        with patch('src.vision.inspection_worker.load_package', return_value=package), \
                patch('src.camera.gstreamer_camera.GStreamerCamera', Camera), \
                patch('src.vision.detector_factory.create_detector', return_value=Detector()), \
                patch('src.vision.inspection_worker.assess', return_value=dict(decision='REVIEW', reason='fixture')), \
                patch('src.vision.inspection_worker.encode_evidence', return_value=[]):
            worker_main('synthetic', station, 'generation', commands, results,
                previews, stopping, cancellation, SimpleNamespace(value=0.))
        messages = []
        while not results.empty():
            messages.append(results.get_nowait())
        self.assertEqual([item for item in messages if item['type'] == 'fault'], [])
        result = next(item['result'] for item in messages if item['type'] == 'result')
        self.assertEqual(result['decision'], 'REVIEW', result)
        self.assertEqual(detected_ids, ['frame-4'])
        self.assertEqual(result['fresh_frame']['source_not_before_monotonic'], durable)
        self.assertEqual(result['fresh_frame']['trigger'], saved_trigger)
        self.assertEqual(result['fresh_frame']['rejection_counts']['PRE_SOURCE_NOT_BEFORE'], 1)


if __name__ == '__main__':
    unittest.main()
