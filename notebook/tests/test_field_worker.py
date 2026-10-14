"""Existing Worker loop with synthetic camera/executor boundaries, never devices."""
from datetime import datetime,timezone
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[2]/'jetson';sys.path.insert(0,str(ROOT))
from src.contracts import CameraFrame
from src.vision.inspection_worker import worker_main
from src.vision.tensorrt_detector import TensorRTDetector
from src.vision.engine_inspector import EngineInspector
from test_field_bbox import Package,Executor


class FakeCamera:
    opened=0;closed=0
    def __init__(self,config):
        type(self).opened+=1
        self.sequence=0;self.pipeline_text='SYNTHETIC_CAMERA';self.image=np.full((720,1280,3),100,np.uint8)
    def capture(self):
        time.sleep(.025);self.sequence+=1;now=time.monotonic()
        frame_id=f'fixture-{self.sequence}'
        self.frame_info=dict(frame_id=frame_id,sequence=self.sequence,camera_epoch='fixture',
            source_pts_ns=int(now*1e9),estimated_source_monotonic=now,received_monotonic=now,age_seconds=0.)
        return CameraFrame(self.image,frame_id,datetime.now(timezone.utc),1280,720,'synthetic')
    def close(self):type(self).closed+=1


class StubParts:
    def runtime_metadata(self):return {'backend':'synthetic'}
    def close(self):pass


class EnvelopeEngine(EngineInspector):
    def __init__(self,package):
        self.estimator=SimpleNamespace(cfg={'decision_policy':{'product_confidence':.55}})
        raw=np.zeros((1,5,8400),np.float32);raw[0,:,0]=[300,400,400,320,.9]
        executor=Executor(raw);executor.runtime_metadata=lambda:{}
        self.detector=TensorRTDetector(Package(),executor)
        self.detector.runtime_metadata=lambda:{'backend':'synthetic-envelope'}
        self.previous_gray=None;self.stable_since=None


class WorkerTests(unittest.TestCase):
    def test_existing_worker_lossless_trace_without_inspection(self):
        FakeCamera.opened=FakeCamera.closed=0
        package=SimpleNamespace(manifest={'files':{},'model_version':'synthetic'},manifest_hash='fixture-package',
            recipe={'alignment_mode':'engine_affine'},capture={'width':1280,'height':720,'fps':30})
        station={'camera_device':'/dev/SYNTHETIC','quality':{'min_blur_variance':0,'min_mean_brightness':0,'max_mean_brightness':255}}
        commands,results,previews,products=(queue.Queue(maxsize=n) for n in (1,8,1,2))
        stopping,cancel,tracking=threading.Event(),threading.Event(),threading.Event();tracking.set()
        heartbeat=SimpleNamespace(value=0)
        area=SimpleNamespace(evaluate=lambda image:{'classification':'UNKNOWN','reason':'SYNTHETIC'})
        window=SimpleNamespace(update=lambda *args:{'state':'UNKNOWN','reason':'SYNTHETIC'})
        with tempfile.TemporaryDirectory() as folder, \
             patch('src.vision.inspection_worker.load_package',return_value=package), \
             patch('src.camera.gstreamer_camera.GStreamerCamera',FakeCamera), \
             patch('src.vision.detector_factory.create_detector',return_value=StubParts()), \
             patch('src.vision.engine_inspector.EngineInspector',EnvelopeEngine), \
             patch('src.vision.engine_inspector.draw_engine_overlay',side_effect=lambda image,*a,**k:image.copy()), \
             patch('src.observation.area_occupancy.load_area_occupancy',return_value=area), \
             patch('src.observation.area_occupancy.ClearWindow',return_value=window):
            commands.put(dict(type='field_raw_capture',action='start',folder=folder,
                request={'clip_id':'worker','duration_seconds':1,'max_frames':160,'max_bytes':16*1024*1024,'condition':'SYNTHETIC'},
                context={'field_raw_approval':True,'publication_disabled':True}))
            thread=threading.Thread(target=worker_main,args=('fixture',station,'g-worker',commands,results,previews,
                stopping,cancel,heartbeat,products,tracking),daemon=True)
            thread.start()
            deadline=time.monotonic()+6
            receipt=Path(folder)/'field_summary.json'
            while time.monotonic()<deadline and not receipt.exists() and thread.is_alive():time.sleep(.03)
            stopping.set();thread.join(4)
            self.assertFalse(thread.is_alive())
            messages=[]
            while not results.empty():messages.append(results.get_nowait())
            self.assertFalse([m for m in messages if m['type'] in ('result','fault')],messages)
            self.assertEqual(FakeCamera.opened,1);self.assertEqual(FakeCamera.closed,1)
            self.assertTrue(receipt.exists())
            import json
            rows=[json.loads(line) for line in (Path(folder)/'frames.jsonl').read_text().splitlines()]
            self.assertGreater(len(rows),6)
            processed=[r for r in rows if r.get('observation')]
            self.assertTrue(processed)
            for row in processed:
                obs=row['observation']
                self.assertEqual(row['frame_id'],obs['detector_frame_id'])
                self.assertEqual(obs['mode'],'PRODUCTION_TRACKING')
                self.assertEqual(obs['provider']['status'],'PRODUCT_OBSERVED')
                self.assertIn('bbox_coordinate_trace',obs['engine']['detector_stages'])
            from analyze_field_capture import analyze
            analysis=analyze(Path(folder),Path(folder)/'analysis')
            self.assertTrue(analysis['frames'])
            self.assertTrue(analysis['frames'][0]['mathematical_clipping_observed'])
            self.assertFalse(analysis['new_inference_executed'])


if __name__=='__main__':unittest.main()
