"""No device access: exercise raw/tensor association and hard capture limits."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
import hashlib
import threading
from unittest.mock import patch
import numpy as np
import cv2

ROOT = Path(__file__).resolve().parents[2]/'jetson'
sys.path.insert(0, str(ROOT))
from src.vision.field_raw_capture import FieldRawCapture, validate_field_request
from src.vision.diagnostic_capture import DiagnosticCapture


def request(**updates):
    value = dict(clip_id='isolated', duration_seconds=1, max_frames=160,
                 max_bytes=8*1024*1024, condition='SYNTHETIC_TEST')
    value.update(updates)
    return value


CONTEXT = dict(field_raw_approval=True, publication_disabled=True,
               worker_generation='g1', camera_owner_pid=123, conditions={'human_state':'SYNTHETIC'})


def freshness(n):
    now = time.monotonic()
    return dict(frame_id=f'epoch-{n}', sequence=n, camera_epoch='epoch',
                source_pts_ns=n*33333333, estimated_source_monotonic=now,
                received_monotonic=now)


def observation(n, boundary=True):
    return dict(frame_id=f'epoch-{n}', detector_frame_id=f'epoch-{n}', generation='g1',
                engine={'detector_stages':{'bbox_coordinate_trace':[
                    {'restored_after_clip':[10,10,200,720 if boundary else 400]}]}},
                inference_ms=12.0)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.image = np.full((720,1280,3),100,np.uint8)
        self.capture = FieldRawCapture()

    def tearDown(self):
        self.capture.stop('TEST_END')
        self.capture.wait(5)
        self.temp.cleanup()

    def start(self, **options):
        self.capture.start(self.temp.name, request(), CONTEXT, **options)

    def test_strict_request_and_approval(self):
        for updates in ({'duration_seconds':5.01},{'max_frames':161}, {'max_bytes':129*1024*1024}):
            with self.assertRaises(ValueError): validate_field_request(request(**updates))
        with self.assertRaises(ValueError):
            self.capture.start(self.temp.name,request(),dict(CONTEXT,publication_disabled=False))

    def test_exact_pixels_tensor_copy_and_manifest(self):
        self.start()
        tensor = np.arange(50,dtype=np.float32).reshape(1,5,10)
        self.capture.capture('epoch-1',self.image,freshness(1))
        self.capture.observe('epoch-1',observation(1),tensor)
        tensor[:] = -1
        self.capture.stop()
        self.assertTrue(self.capture.wait(5))
        row = next(iter(self.capture.rows.values()))
        png = cv2.imread(str(Path(self.temp.name)/row['raw_path']))
        np.testing.assert_array_equal(png,self.image)
        self.assertEqual(row['pixel_sha256'],hashlib.sha256(self.image.tobytes()).hexdigest())
        saved = np.load(Path(self.temp.name)/row['tensor_path'],allow_pickle=False)
        np.testing.assert_array_equal(saved,np.arange(50,dtype=np.float32).reshape(1,5,10))
        summary = json.loads((Path(self.temp.name)/'field_summary.json').read_text())
        self.assertEqual(summary['state'],'SAVED')
        self.assertEqual(summary['plc_writes'],0)
        for item in summary['files']:
            self.assertEqual(hashlib.sha256((Path(self.temp.name)/item['path']).read_bytes()).hexdigest(),item['sha256'])

    def test_timer_stops_even_with_no_new_frame(self):
        self.start()
        time.sleep(1.15)
        self.assertFalse(self.capture.recording)
        self.assertTrue(self.capture.wait(4))
        self.assertEqual(self.capture.stop_reason,'TIME_LIMIT')

    def test_frame_mismatch_disables_capture(self):
        self.start()
        self.capture.capture('epoch-1',self.image,freshness(1))
        value=observation(1); value['detector_frame_id']='epoch-2'
        self.capture.observe('epoch-1',value,np.zeros((1,5,10),np.float32))
        self.assertFalse(self.capture.recording)
        self.assertIn('FRAME_ID_MISMATCH',self.capture.error)

    def test_epoch_or_generation_change_disables(self):
        self.start()
        self.capture.capture('epoch-1',self.image,freshness(1))
        value=observation(1); value['generation']='g2'
        self.capture.observe('epoch-1',value,None)
        self.assertFalse(self.capture.recording)

    def test_disk_preflight(self):
        with self.assertRaises(OSError): self.start(free_bytes=0)
        self.assertFalse(self.capture.recording)

    def test_encoder_failure_disables_without_next_frame(self):
        self.start(encoder=lambda image: (False,None))
        self.capture.capture('epoch-1',self.image,freshness(1))
        deadline=time.monotonic()+2
        while self.capture.recording and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.capture.recording)
        self.assertTrue(self.capture.wait(4))
        self.assertEqual(self.capture.phase,'ERROR')
        self.assertEqual(self.capture.stop_reason,'WRITE_ERROR')

    def test_tensor_selection_is_bounded(self):
        self.start()
        for n in range(1,16):
            self.capture.capture(f'epoch-{n}',self.image,freshness(n))
            self.capture.observe(f'epoch-{n}',observation(n),np.zeros((1,5,10),np.float32))
        self.assertLessEqual(self.capture.selected_tensors,12)
        self.capture.stop(); self.capture.wait(5)
        self.assertTrue(any(row.get('tensor_status')=='SELECTION_LIMIT' for row in self.capture.rows.values()))

    def test_no_overlay_mutation(self):
        self.start()
        original=self.image.copy()
        self.capture.capture('epoch-1',self.image,freshness(1))
        self.capture.observe('epoch-1',observation(1),None)
        np.testing.assert_array_equal(original,self.image)

    def test_gap_is_preserved_not_renumbered(self):
        self.start()
        for n in (1,3):self.capture.capture(f'epoch-{n}',self.image,freshness(n))
        self.capture.stop();self.capture.wait(5)
        summary=json.loads((Path(self.temp.name)/'field_summary.json').read_text())
        self.assertEqual(summary['worker_sequence_gaps'],[{'after':1,'before':3,'missing':1}])
        self.assertFalse(summary['continuous_clear_evidence_eligible'])

    def test_memory_reserve_refuses_start(self):
        with patch('pathlib.Path.exists',return_value=True), patch('pathlib.Path.read_text',return_value='MemAvailable: 1 kB\n'):
            with self.assertRaisesRegex(OSError,'MEMORY_RESERVE'):self.start()
        self.assertFalse(self.capture.recording)

    def test_byte_limit_closes_and_no_payload_exceeds_bound(self):
        self.capture.start(self.temp.name,request(max_bytes=1024),CONTEXT)
        self.capture.capture('epoch-1',self.image,freshness(1))
        self.assertTrue(self.capture.wait(3))
        self.assertEqual(self.capture.stop_reason,'BYTE_LIMIT')
        self.assertLessEqual(self.capture.bytes_reserved,1024)

    def test_queue_overload_counts_missing_raw(self):
        release=threading.Event()
        def blocked_encoder(image):
            release.wait(3)
            return cv2.imencode('.png',image)
        self.start(encoder=blocked_encoder)
        try:
            for n in range(1,20):self.capture.capture(f'epoch-{n}',self.image,freshness(n))
            self.assertGreater(self.capture.dropped_raw_frames,0)
            self.assertLessEqual(self.capture.queue.qsize(),8)
        finally:release.set()

    def test_metadata_limit_disables(self):
        self.start();self.capture.capture('epoch-1',self.image,freshness(1))
        value=observation(1);value['oversize']='x'*(1024*1024+1)
        self.capture.observe('epoch-1',value)
        self.assertEqual(self.capture.error,'METADATA_LIMIT')
        self.assertFalse(self.capture.recording)

    def test_disk_write_error_is_not_saved(self):
        self.start()
        self.capture._persist_payload=lambda *args: (_ for _ in ()).throw(OSError('SIMULATED_DISK_FAILURE'))
        self.capture.capture('epoch-1',self.image,freshness(1))
        self.capture.stop();self.assertTrue(self.capture.wait(5))
        self.assertEqual(self.capture.phase,'ERROR')
        self.assertIn('SIMULATED_DISK_FAILURE',self.capture.error)

    def test_existing_generic_recorder_remains_unchanged(self):
        generic=DiagnosticCapture()
        try:
            generic.start(self.temp.name,request(duration_seconds=10),{})
            generic.capture('epoch-1',self.image,freshness(1))
            generic.observe('epoch-1',{'frame_id':'epoch-1'})
            generic.stop();self.assertTrue(generic.wait(4))
            self.assertEqual(generic.phase,'SAVED')
        finally:generic.stop();generic.wait(4)


if __name__=='__main__':unittest.main()
