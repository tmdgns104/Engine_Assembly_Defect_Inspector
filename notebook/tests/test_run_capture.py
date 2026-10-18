"""Operating diagnostics must not encode/write before a fresh safe-flush lease."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.vision.diagnostic_capture import DiagnosticCapture

# Before the approved mode exists, exercise the real current recorder: its
# immediate RECORDING/encoding is precisely the behavior this change must fix.
if importlib.util.find_spec('src.vision.run_capture'):
    from src.vision.run_capture import RunCapture
else:
    RunCapture = DiagnosticCapture


def signals():
    return NS(started_at=NS(value=0.), stop_code=NS(value=0), flush_until=NS(value=0.))


def meta(index, epoch='e'):
    now = time.monotonic()
    return dict(sequence=index, camera_epoch=epoch, source_pts_ns=index*100000000,
                estimated_source_monotonic=now, received_monotonic=now)


class RunCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'clip'
        self.signals = signals()
        self.capture = RunCapture()
        self.image = np.arange(64*64*3, dtype=np.uint8).reshape(64, 64, 3)
        self.request = dict(clip_id='one', duration_seconds=20, max_frames=240,
                            max_bytes=64*1024*1024, condition='SYNTHETIC')
        self.context = dict(worker_generation='g', camera_epoch='e', run_capture_approved=True,
                            raw_shape=list(self.image.shape))

    def tearDown(self):
        self.capture.stop('TEST_END')
        self.signals.flush_until.value = time.monotonic()+5
        if hasattr(self.capture, 'permit_flush'):
            self.capture.permit_flush()
        self.capture.wait(5)
        self.temp.cleanup()

    def start(self, **options):
        if RunCapture is DiagnosticCapture:
            self.capture.start(self.folder, self.request, self.context, **options)
        else:
            self.capture.start(self.folder, self.request, self.context, signals=self.signals, **options)

    def begin(self):
        self.signals.started_at.value = time.monotonic()
        self.capture.tick()

    def test_existing_capture_must_wait_for_start_and_safe_stop_to_encode(self):
        encoded = []
        def encoder(image):
            encoded.append(True)
            return cv2.imencode('.png', image)
        self.start(encoder=encoder)
        self.assertEqual(self.capture.status()['state'], 'ARMED')
        self.capture.capture('e-0', self.image, meta(0))
        self.assertEqual(len(self.capture.rows), 0)
        self.begin()
        self.capture.capture('e-1', self.image, meta(1))
        self.image[:] = 0
        self.capture.stop('WINDOW_END')
        self.assertEqual(self.capture.status()['state'], 'WAIT_SAFE_FLUSH')
        self.assertEqual(encoded, [])
        self.assertEqual(list((self.folder/'raw').iterdir()), [])
        self.signals.flush_until.value = time.monotonic()+5
        self.capture.permit_flush()
        self.assertTrue(self.capture.wait(4))
        row = next(iter(self.capture.rows.values()))
        saved = cv2.imread(str(self.folder/row['raw_path']))
        np.testing.assert_array_equal(saved, np.arange(64*64*3,dtype=np.uint8).reshape(64,64,3))
        self.assertEqual(self.capture.status()['state'], 'SAVED')
        self.assertEqual(len(encoded), 1)

    def test_frame_limit_keeps_first_raws_and_exposes_truncation(self):
        self.request['max_frames'] = 2
        self.start(); self.begin()
        for n in range(1, 4): self.capture.capture(f'e-{n}', self.image, meta(n))
        self.assertEqual(list(self.capture.rows), ['e-1', 'e-2'])
        self.assertEqual(self.capture.status()['stop_reason'], 'FRAME_LIMIT')
        self.assertFalse(self.capture.recording)

    def test_epoch_change_is_diagnostic_only_and_old_pixels_are_retained(self):
        self.start(); self.begin()
        self.capture.capture('e-1', self.image, meta(1))
        self.capture.capture('other-2', self.image, meta(2,'other'))
        self.assertEqual(list(self.capture.rows), ['e-1'])
        self.assertIn('EPOCH', self.capture.status()['error'])

    def test_original_metadata_and_parts_follow_frame_id_without_tensor_copy(self):
        self.start(); self.begin()
        self.capture.capture('e-1', self.image, meta(1))
        obs = dict(frame_id='e-1', generation='g', mode='FULL_INSPECTION_PATH',
                   detections=[dict(class_name='fixture_part', confidence=.91)],
                   engine={'stable':True, 'reason_code':'FIXTURE'})
        tensor = np.ones((100,100),np.float32)
        self.capture.observe('e-1',obs,tensor)
        obs['engine']['stable'] = False
        tensor[:] = 0
        self.capture.stop()
        self.signals.flush_until.value = time.monotonic()+5
        self.capture.permit_flush(); self.assertTrue(self.capture.wait(4))
        row=json.loads((self.folder/'frames.jsonl').read_text(encoding='utf-8').splitlines()[0])
        self.assertTrue(row['observation']['engine']['stable'])
        self.assertEqual(row['observation']['detections'][0]['confidence'], .91)
        self.assertEqual(row['tensor_status'], 'NOT_REQUESTED')
        self.assertFalse(list((self.folder/'outputs').iterdir()))

    def test_expired_flush_lease_prevents_next_file_write(self):
        self.start(); self.begin(); self.capture.capture('e-1',self.image,meta(1)); self.capture.stop()
        self.signals.flush_until.value = time.monotonic()-1
        self.capture.permit_flush()
        self.assertFalse(self.capture.wait(.05))
        self.assertFalse(list((self.folder/'raw').iterdir()))
        self.signals.flush_until.value = time.monotonic()+5
        self.assertTrue(self.capture.wait(4))
        self.assertEqual(self.capture.status()['state'], 'SAVED')

    def test_raw_budget_failure_does_not_lose_previous_frames(self):
        self.start(); self.begin()
        self.capture.capture('e-1',self.image,meta(1))
        huge = np.zeros((4096,4096,3),np.uint8)
        self.capture.capture('e-2',huge,meta(2))
        self.assertEqual(list(self.capture.rows), ['e-1'])
        self.assertFalse(self.capture.recording)
        self.assertIn(self.capture.stop_reason,('IMAGE_BYTES_LIMIT','RAW_SHAPE_CHANGED'))

    def test_deadline_stops_without_reusing_last_frame(self):
        self.start(); self.begin(); self.capture.capture('e-1',self.image,meta(1))
        self.capture.tick(self.signals.started_at.value+21)
        self.assertFalse(self.capture.recording)
        self.assertEqual(list(self.capture.rows), ['e-1'])
        self.assertEqual(self.capture.stop_reason, 'TIME_LIMIT')

    def test_encoder_failure_is_explicit_and_never_success(self):
        self.start(encoder=lambda image:(False,None)); self.begin()
        self.capture.capture('e-1',self.image,meta(1)); self.capture.stop()
        self.signals.flush_until.value=time.monotonic()+5
        self.capture.permit_flush(); self.assertTrue(self.capture.wait(4))
        self.assertEqual(self.capture.status()['state'],'ERROR')
        self.assertEqual(self.capture.saved_frames,0)

    def test_saved_metadata_is_released_without_expanding_entire_clip(self):
        self.start(); self.begin()
        for n in range(1, 4):
            self.capture.capture(f'e-{n}',self.image,meta(n))
            self.capture.observe(f'e-{n}',dict(frame_id=f'e-{n}',generation='g',details='x'*60000))
        self.capture.stop()
        self.signals.flush_until.value=time.monotonic()+5
        self.capture.permit_flush();self.assertTrue(self.capture.wait(4))
        self.assertEqual(self.capture.status()['memory_metadata_bytes'],0)
        rows=[json.loads(line) for line in (self.folder/'frames.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),3)
        self.assertTrue(all(len(row['observation']['details'])==60000 for row in rows))

    def test_arm_timeout_has_no_frames_and_low_resources_refuse_start(self):
        with self.assertRaisesRegex(OSError,'MEMORY_RESERVE'):
            self.start(memory_available=1024)
        with self.assertRaisesRegex(OSError,'DISK_RESERVE'):
            self.start(free_bytes=1024)
        self.start();self.capture.tick(self.capture.armed_at+61)
        self.assertEqual(self.capture.stop_reason,'ARM_TIMEOUT')
        self.assertEqual(len(self.capture.rows),0)

    def test_memory_reserve_includes_runtime_trace_budget(self):
        self.context['conditions']={'total_memory_limit_bytes':self.request['max_bytes']+8*1024**2}
        with self.assertRaisesRegex(OSError,'MEMORY_RESERVE'):
            self.start(memory_available=self.request['max_bytes']+1024**3+1)

    def test_pre_start_and_duplicate_sources_do_not_manufacture_new_frames(self):
        self.start();self.begin()
        old=meta(1);old['estimated_source_monotonic']=self.capture.armed_at-1
        self.capture.capture('e-1',self.image,old)
        self.assertEqual(self.capture.pre_start_frames,1)
        self.capture.capture('e-2',self.image,meta(2))
        self.capture.capture('e-3',self.image,meta(2))
        self.assertEqual(self.capture.error,'SOURCE_PTS_NOT_INCREASING')
        self.assertEqual(list(self.capture.rows),['e-2'])

    def test_raw_storage_is_allocated_before_start_within_total_memory_budget(self):
        self.start()
        self.assertGreater(self.capture.status().get('preallocated_raw_bytes',0),0)
        with patch('numpy.empty',side_effect=AssertionError('allocation during RUN')):
            self.begin();self.capture.capture('e-1',self.image,meta(1))
        self.assertIsNone(self.capture.error)
        self.assertEqual(len(self.capture.rows),1)
        self.assertLessEqual(self.capture.status()['preallocated_raw_bytes']+40*1024**2,self.request['max_bytes'])

    def test_part_inference_provenance_distinguishes_skipped_from_zero_detections(self):
        from src.vision.run_capture import part_inference_provenance
        skipped=dict(part_inference_input='NOT_RUN_WITHOUT_RELIABLE_PRODUCT_POSE',
            engine_dynamic={'stage_timings_ms':{'part_detection_ms':None}})
        self.assertEqual(part_inference_provenance(skipped)['parts_computation'],'NOT_COMPUTED')
        computed=dict(part_inference_input='ENGINE_POSE_RECTIFIED',part_input_transform=[[1,0,2],[0,1,3]],
            engine_dynamic={'stage_timings_ms':{'part_detection_ms':4.2}},detections=[])
        result=part_inference_provenance(computed)
        self.assertEqual(result['parts_computation'],'COMPUTED')
        self.assertEqual(result['part_input_transform'],computed['part_input_transform'])
        self.assertEqual(part_inference_provenance({})['parts_computation'],'NOT_COMPUTED')


if __name__ == '__main__': unittest.main()
