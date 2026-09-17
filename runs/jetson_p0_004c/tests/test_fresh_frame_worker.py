"""Exercise the actual Worker/Camera code with deterministic in-memory devices."""

from datetime import datetime, timezone
import queue
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np

from src.camera.gstreamer_camera import GStreamerCamera
from src.contracts import CameraError, CameraFrame, DetectionResult
from src.vision.inspection_worker import worker_main
from test_fresh_frame import frame, trigger
from test_product_package import write_package


class CameraClockTests(unittest.TestCase):
    def camera(self, pts=100, previous=-1):
        camera = GStreamerCamera.__new__(GStreamerCamera)
        camera.Gst = SimpleNamespace(MessageType=SimpleNamespace(ERROR=1, EOS=2, CLOCK_LOST=4),
                                     MapFlags=SimpleNamespace(READ=1),Format=SimpleNamespace(TIME=3),
                                     CLOCK_TIME_NONE=2**64-1,SECOND=1000,MSECOND=1)
        camera.np = np
        camera.open = True
        camera.sequence = 0
        camera.last_pts = previous
        camera.epoch = 'test-epoch'
        camera.width = camera.height = 2
        camera.bus = SimpleNamespace(timed_pop_filtered=lambda *args:None)
        buffer = SimpleNamespace(pts=pts,map=lambda *args:(True,SimpleNamespace(data=bytes(12))),unmap=lambda *args:None)
        segment = SimpleNamespace(format=3,rate=1.0,to_running_time=lambda fmt,value:value+50)
        sample = SimpleNamespace(get_buffer=lambda:buffer,
                    get_caps=lambda:SimpleNamespace(get_structure=lambda _:SimpleNamespace(get_value=lambda _:2)),
                    get_segment=lambda:segment)
        camera.sink = SimpleNamespace(emit=lambda *args:sample)
        camera.pipeline = SimpleNamespace(get_clock=lambda:SimpleNamespace(get_time=lambda:1200),get_base_time=lambda:1000)
        return camera

    def test_segment_conversion_and_copy_delay_do_not_advance_source(self):
        camera = self.camera()
        with patch('src.camera.gstreamer_camera.time',SimpleNamespace(monotonic=unittest.mock.Mock(side_effect=[10,10.002,10.2]))):
            captured = camera.capture()
        self.assertEqual(camera.frame_info['source_running_time_ns'],150)
        self.assertAlmostEqual(camera.frame_info['estimated_source_monotonic'],9.95)
        self.assertAlmostEqual(camera.frame_info['age_seconds'],.25)
        self.assertEqual(camera.frame_info['camera_epoch'],'test-epoch')
        self.assertEqual(camera.frame_info['frame_id'],captured.frame_id)

    def test_adapter_keeps_duplicate_and_regression_reasons_distinct(self):
        for pts,reason in ((100,'DUPLICATE_FRAME'),(99,'PTS_REGRESSION')):
            with self.subTest(pts=pts), self.assertRaisesRegex(CameraError,reason):
                self.camera(pts,100).capture()

    def test_clock_loss_invalidates_epoch_and_aborts(self):
        camera = self.camera()
        camera.bus = SimpleNamespace(timed_pop_filtered=lambda *args:SimpleNamespace(type=4))
        with self.assertRaisesRegex(CameraError, 'CAMERA_EPOCH_CHANGED'):
            camera.capture()
        self.assertNotEqual(camera.epoch, 'test-epoch')
        self.assertFalse(camera.open)


class WorkerContractTests(unittest.TestCase):
    def run_worker(self, mode):
        clock = SimpleNamespace(now=10.03)
        stopping, cancellation = threading.Event(), threading.Event()
        calls = []
        frames = [frame(1,source=9.0,received=9.01),frame(2,source=9.9,received=9.91),
                  frame(3,source=9.99,received=10.0),frame(4,source=10.01,received=10.02),
                  frame(5,source=10.04,received=10.05),frame(6,source=10.07,received=10.08)]
        if mode == 'epoch':
            frames[3]['camera_epoch'] = 'camera-B'
        class Camera:
            frame_info = {}
            pipeline_text = 'SYNTHETIC'
            def __init__(self, config):
                self.iterator = iter(frames)
            def capture(self):
                self.frame_info = next(self.iterator)
                if mode == 'camera_error' and self.frame_info['sequence'] == 4:
                    raise CameraError('PTS_REGRESSION')
                clock.now = max(10.03,self.frame_info['received_monotonic']+.01)
                if mode == 'timeout' and self.frame_info['sequence'] == 4:
                    clock.now = 12.1
                return CameraFrame(np.zeros((8,8,3),dtype=np.uint8),self.frame_info['frame_id'],
                                   datetime.now(timezone.utc),8,8,'replay')
            def close(self):
                pass
        class Detector:
            device = 'mock'
            input_shape = [1,3,8,8]
            torch = SimpleNamespace(cuda=SimpleNamespace(get_device_name=lambda _:'SYNTHETIC'))
            def __init__(self,*args,**kwargs):
                pass
            def runtime_metadata(self):
                return {'backend':'synthetic','device':self.device,'gpu':'SYNTHETIC','input_shape':list(self.input_shape)}
            def detect(self,captured):
                calls.append(captured.frame_id)
                if mode == 'cancel_during_inference':
                    cancellation.set()
                return DetectionResult(captured.frame_id,(), 'mock',1.0)
        class Results(queue.Queue):
            def put(self,message,*args,**kwargs):
                super().put(message,*args,**kwargs)
                if message['type'] in ('result','fault'):
                    stopping.set()
        with tempfile.TemporaryDirectory() as folder:
            write_package(Path(folder))
            commands,results,previews = queue.Queue(),Results(),queue.Queue(maxsize=1)
            station = {'camera_device':'synthetic','frame_spacing_seconds':0,'max_frame_age_seconds':.35,
                       'fresh_frame':{'boundary_epsilon_ms':0,'max_trigger_to_frame_ms':2000,'inspection_window_ms':2000},
                       'quality':{'min_blur_variance':0,'min_mean_brightness':0,'max_mean_brightness':255}}
            commands.put({'inspection_id':'I1','trigger':trigger().to_dict(),'accepted_monotonic':10,'deadline':12,
                          'request':{'kind':'inspect','view_assessment':{}},'calibration':None})
            with patch('src.camera.gstreamer_camera.GStreamerCamera',Camera), \
                 patch('src.vision.pytorch_detector.PyTorchDetector',Detector), \
                 patch('src.vision.inspection_worker.time',SimpleNamespace(monotonic=lambda:clock.now)):
                worker_main(folder,station,'generation',commands,results,previews,stopping,cancellation,SimpleNamespace(value=10))
            messages = []
            while not results.empty():
                messages.append(results.get_nowait())
            self.assertEqual(messages[0]['type'],'ready')
            self.assertEqual(messages[-1]['type'],'result',messages[-1])
            return messages[-1],calls

    def test_worker_rejects_buffered_then_runs_three_distinct_observations(self):
        message,calls = self.run_worker('normal')
        self.assertEqual(calls,['camera-A-4','camera-A-5','camera-A-6'])
        self.assertEqual(message['result']['decision'],'REVIEW')
        self.assertEqual(message['result']['fresh_frame']['rejection_counts'],{'PRE_TRIGGER':1})
        self.assertEqual(len(message['images']),4)
        self.assertEqual([item['frame_id'] for item in message['images'][:3]],calls)
        self.assertEqual(len(message['result']['fresh_frame']['selected_frames']),3)

    def test_epoch_timeout_cancel_never_emit_inspection_images(self):
        for mode,reason in (('epoch','CAMERA_EPOCH_CHANGED'),('timeout','DEADLINE_EXCEEDED'),
                            ('cancel_during_inference','CANCELLED'),('camera_error','PTS_REGRESSION')):
            with self.subTest(mode=mode):
                message,calls = self.run_worker(mode)
                self.assertEqual(message['result']['reason_code'],reason)
                self.assertEqual(message['images'],[])
                self.assertEqual(message['result']['decision'],'ERROR')
                self.assertLessEqual(len(calls),1)


if __name__ == '__main__':
    unittest.main()
