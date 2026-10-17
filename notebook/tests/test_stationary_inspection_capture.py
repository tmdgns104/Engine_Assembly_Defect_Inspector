"""Real Worker/decision/PNG path with an explicit synthetic camera/model boundary."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import queue
import sys
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.contracts import CameraFrame
from src.decision.engine_dynamic import SLOTS
from src.runtime.inspection_start import FULL_FRAME
from src.vision.engine_inspector import EngineInspector
from src.vision.inspection_worker import worker_main


class StationaryCaptureTests(unittest.TestCase):
    def run_worker(self, *, settle=True, timeout=2.5, binding=True, missing=False,
                   stable_pattern=None, cancel_at=None, epoch_change_at=None,
                   invalid_quality=False, processing_timeout=None,
                   inference_delay=0, encoding_delay=0, cancel_after_inference=False):
        stop, cancel = threading.Event(), threading.Event()
        commands, results, previews = queue.Queue(), queue.Queue(128), queue.Queue(1)
        camera_counts = dict(opened=0, closed=0)

        class Camera:
            def __init__(self, config):
                camera_counts['opened'] += 1
                self.sequence = 0
                self.pipeline_text = 'SYNTHETIC_ONLY'

            def capture(self):
                time.sleep(.04)
                self.sequence += 1
                now = time.monotonic()
                # The product coasts, then remains still. The real motion method
                # must observe its unchanged 0.6 s stability period.
                position = min(self.sequence, 6) if settle else self.sequence % 7
                image = np.full((128, 128, 3), 40, np.uint8)
                image[35:95, 10 + position * 7:45 + position * 7] = 200
                epoch = 'changed' if epoch_change_at and self.sequence >= epoch_change_at else 'e'
                identifier = f'{epoch}-{self.sequence}'
                self.frame_info = dict(frame_id=identifier, sequence=self.sequence,
                    camera_epoch=epoch, source_pts_ns=int(now * 1e9),
                    estimated_source_monotonic=now, received_monotonic=now,
                    received_at=datetime.now(timezone.utc).isoformat(), age_seconds=0.)
                if cancel_at and self.sequence >= cancel_at:
                    cancel.set()
                return CameraFrame(image, identifier, datetime.now(timezone.utc), 128, 128, 'synthetic')

            def close(self):
                camera_counts['closed'] += 1

        class Parts:
            def runtime_metadata(self): return {'backend': 'synthetic'}
            def close(self): pass

        class Engine(EngineInspector):
            def __init__(self, package):
                self.detector = Parts()
                self.previous_gray = None
                self.stable_since = None

            def detect(self, frame, detected, parts_detector=None):
                product = dict(class_name='product_envelope', confidence=.99,
                    bounding_box=dict(x1=20, y1=20, x2=110, y2=110))
                changed, stable = self.motion(frame.image, product=product,
                    freshness=detected['freshness'], visible=detected['quality']['valid'])
                sequence = detected['freshness']['sequence']
                if sequence == 5 and inference_delay:
                    time.sleep(inference_delay)
                    if cancel_after_inference:
                        cancel.set()
                if stable_pattern is not None:
                    stable = stable_pattern.get(sequence, False)
                slots = dict.fromkeys(SLOTS, 'PRESENT')
                if missing:
                    slots[missing if isinstance(missing,str) else 'pipe_left'] = 'MISSING'
                detected['detections'] = [product]
                detected['engine_dynamic'] = dict(frame_id=frame.frame_id,
                    source_pts_ns=detected['freshness']['source_pts_ns'], camera_epoch=detected['freshness']['camera_epoch'],
                    decision='REVIEW' if missing else 'PASS',
                    reason_code='AWAITING_THREE_FRAME_CONFIRMATION' if missing else 'ALL_REQUIRED_PARTS_PRESENT',
                    product=product, product_selection={'valid_count': 1},
                    pose={'reliable': True}, assignment_reliable=True, slot_states=slots,
                    stable=stable, motion_fraction=changed, quality_valid=detected['quality']['valid'],
                    stage_timings_ms={'product_detection_ms': 0})

            def close(self): pass

        package = NS(manifest={'files': {}, 'model_version': 'synthetic'}, manifest_hash='sha',
            recipe={'alignment_mode': 'engine_affine', 'observation_count': 3,
                    'slots': [{'id': slot} for slot in SLOTS]}, capture={})
        station = dict(camera_device='/dev/SYNTHETIC',
            quality=dict(min_mean_brightness=255 if invalid_quality else 0,
                         max_mean_brightness=255, min_blur_variance=0),
            frame_spacing_seconds=0, max_frame_age_seconds=.5,
            fresh_frame=dict(boundary_epsilon_ms=0, max_trigger_to_frame_ms=timeout * 1000,
                             inspection_window_ms=timeout * 1000))
        start = time.monotonic()
        total = processing_timeout if processing_timeout is not None else timeout
        job = dict(inspection_id='synthetic-inspection', accepted_monotonic=start, deadline=start + total,
            request=dict(kind='inspect', view_assessment={}), calibration={'confirmed': True},
            experiment_policy=dict(source_mode='PRODUCTION_AUTO', session_id='s',
                inspection_motion_mode='STATIONARY', physical_output_enabled=False, human_acceptance='PENDING'),
            trigger=dict(trigger_id='trigger', cell_id='cell', plc_session_id=1, cycle_id=1, request_id=1,
                trigger_received_monotonic=start, trigger_source='LOCAL_TEST', capture_epoch='e',
                deadline_monotonic=start + total))
        if processing_timeout is not None:
            job['capture_deadline'] = start + timeout
        if binding:
            job['production_binding'] = dict(plc_contract='OPENER_CYCLIC',
                inspection_start_policy=FULL_FRAME, inspection_motion_mode='STATIONARY',
                worker_generation='g', camera_epoch='e', package_manifest_sha='sha', track_id='track',
                sequence=0, monotonic_s=start, product_box=None,
                inspection_zone={'polygon_normalized': [[0,0], [1,0], [1,1], [0,1]]})
        commands.put(job)
        from src.vision.inspection_worker import encode_evidence
        def delayed_encoding(*args, **kwargs):
            time.sleep(encoding_delay)
            return encode_evidence(*args, **kwargs)
        with patch('src.vision.inspection_worker.load_package', return_value=package), \
             patch('src.vision.inspection_worker.encode_evidence', side_effect=delayed_encoding), \
             patch('src.camera.gstreamer_camera.GStreamerCamera', Camera), \
             patch('src.vision.detector_factory.create_detector', return_value=Parts()), \
             patch('src.vision.engine_inspector.EngineInspector', Engine), \
             patch('src.vision.engine_inspector.draw_engine_overlay', side_effect=lambda image, *a, **kw: image.copy()):
            thread = threading.Thread(target=worker_main,
                args=('synthetic', station, 'g', commands, results, previews, stop, cancel, NS(value=0)), daemon=True)
            thread.start()
            messages = []
            final = None
            deadline = time.monotonic() + timeout + 3
            try:
                while time.monotonic() < deadline:
                    message = results.get(timeout=timeout + 3)
                    messages.append(message)
                    if message['type'] in ('result', 'fault'):
                        final = message
                        break
            finally:
                stop.set()
                thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(camera_counts, dict(opened=1, closed=1))
        self.assertIsNotNone(final, messages)
        self.assertEqual(final['type'], 'result', final)
        return final

    def test_last_valid_capture_survives_inference_crossing_capture_deadline(self):
        result = self.run_worker(timeout=.6, processing_timeout=2., inference_delay=.65,
            stable_pattern={3: True, 4: True, 5: True})['result']
        self.assertEqual(result['decision'], 'PASS', result.get('reason_code'))
        evidence = result['fresh_frame']
        self.assertTrue(all(f['selected_at_monotonic'] < evidence['selection_deadline_monotonic']
                            for f in evidence['selected_frames']))

    def test_encoding_crossing_capture_deadline_preserves_three_originals(self):
        message = self.run_worker(timeout=.6, processing_timeout=2., encoding_delay=.65,
            stable_pattern={3: True, 4: True, 5: True})
        self.assertEqual(message['result']['decision'], 'PASS', message['result'].get('reason_code'))
        self.assertEqual(len([i for i in message['images'] if i['kind'] == 'raw']), 3)

    def test_processing_cannot_extend_original_total_deadline(self):
        result = self.run_worker(timeout=.6, processing_timeout=.8, inference_delay=.9,
            stable_pattern={3: True, 4: True, 5: True})['result']
        self.assertEqual(result['decision'], 'ERROR')

    def test_stop_during_last_inference_still_rejects_result(self):
        result = self.run_worker(timeout=.6, processing_timeout=2., inference_delay=.65,
            cancel_after_inference=True, stable_pattern={3: True, 4: True, 5: True})['result']
        self.assertEqual(result['decision'], 'ERROR')
        self.assertEqual(result['reason_code'], 'CANCELLED')

    def test_coasting_frames_are_not_final_three_stationary_frames(self):
        message = self.run_worker()
        result = message['result']
        self.assertEqual(result['decision'], 'PASS', result.get('reason_code'))
        self.assertTrue(all(o['engine_dynamic']['stable'] for o in result['observations']))
        self.assertEqual(len(result['observations']), 3)
        self.assertGreater(result['stationary_capture']['rejected_count'], 0)
        selected = result['fresh_frame']['selected_frames']
        self.assertEqual([o['frame_id'] for o in result['observations']], [f['frame_id'] for f in selected])
        self.assertEqual([o['frame_id'] for o in result['observations']],
                         [i['frame_id'] for i in message['images'] if i['kind'] == 'raw'])
        originals = [i for i in message['images'] if i['kind'] == 'raw']
        for observation, original in zip(result['observations'], originals):
            pixels = cv2.imdecode(np.frombuffer(original['data'], np.uint8), cv2.IMREAD_COLOR)
            self.assertEqual(hashlib.sha256(pixels.tobytes()).hexdigest(), observation['input_pixel_sha256'])
            self.assertEqual(observation['worker_generation'], 'g')
            self.assertEqual(observation['freshness']['camera_epoch'], 'e')
            self.assertEqual(observation['freshness']['source_pts_ns'],
                             observation['engine_dynamic']['source_pts_ns'])

    def test_motion_after_two_stable_frames_starts_new_three_frame_window(self):
        message = self.run_worker(stable_pattern={3: True, 4: True, 5: False, 6: True, 7: True, 8: True})
        self.assertEqual([o['frame_id'] for o in message['result']['observations']], ['e-6', 'e-7', 'e-8'])
        self.assertEqual(message['result']['decision'], 'PASS')
        self.assertEqual(message['result']['stationary_capture']['continuity_reset_count'], 1)
        self.assertEqual(message['result']['stationary_capture']['discarded_stable_frames'], 2)

    def test_stationary_missing_part_keeps_actual_fail(self):
        from src.decision.engine_dynamic import MISSING_CODES
        for slot,code in MISSING_CODES.items():
            with self.subTest(slot=slot):
                result = self.run_worker(missing=slot)['result']
                self.assertEqual(result['decision'], 'FAIL')
                self.assertEqual(result['reason_code'], code)

    def test_never_stable_expires_with_actual_evidence(self):
        message = self.run_worker(settle=False, timeout=.45)
        self.assertEqual(message['result']['decision'], 'ERROR')
        self.assertEqual(message['result']['reason_code'], 'DEADLINE_EXCEEDED')
        self.assertGreater(len(message['images']), 0)
        self.assertLessEqual(len(message['result']['observations']), 3)

    def test_wait_diagnostics_keep_bounded_recent_metadata(self):
        result = self.run_worker(settle=False, timeout=2.1)['result']
        evidence = result['stationary_capture']
        self.assertGreater(evidence['rejected_count'], 32)
        self.assertEqual(len(evidence['rejected_frames']), 32)
        self.assertEqual(evidence['rejected_metadata_truncated'], evidence['rejected_count']-32)
        self.assertLessEqual(len(result['fresh_frame']['acquisition_candidates']), 32)

    def test_cancel_during_coasting_never_becomes_final_pass(self):
        result = self.run_worker(cancel_at=6)['result']
        self.assertEqual(result['decision'], 'ERROR')
        self.assertEqual(result['reason_code'], 'CANCELLED')

    def test_camera_epoch_change_remains_fatal(self):
        result = self.run_worker(epoch_change_at=6)['result']
        self.assertEqual(result['decision'], 'ERROR')
        self.assertEqual(result['reason_code'], 'CAMERA_EPOCH_CHANGED')

    def test_invalid_quality_is_not_promoted(self):
        # The existing non-stationary path still reports its quality REVIEW.
        result = self.run_worker(binding=False, invalid_quality=True)['result']
        self.assertEqual(result['decision'], 'REVIEW')
        self.assertEqual(result['reason_code'], 'IMAGE_QUALITY_INSUFFICIENT')

    def test_invalid_quality_cannot_earn_stationary_capture(self):
        result = self.run_worker(invalid_quality=True, timeout=.45)['result']
        self.assertEqual(result['decision'], 'ERROR')
        self.assertEqual(result['reason_code'], 'DEADLINE_EXCEEDED')
        self.assertTrue(all(not o['engine_dynamic']['stable'] for o in result['observations']))
        self.assertTrue(all(not o['quality']['valid'] for o in result['observations']))

    def test_other_job_policy_still_uses_existing_first_three_frames(self):
        result = self.run_worker(binding=False)['result']
        self.assertEqual([o['frame_id'] for o in result['observations']], ['e-3', 'e-4', 'e-5'])
        self.assertEqual(result['reason_code'], 'ENGINE_OR_HAND_MOTION')


if __name__ == '__main__':
    unittest.main()
