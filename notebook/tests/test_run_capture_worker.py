"""Real Worker loop, synthetic device/model; not a hardware acceptance claim."""
import json
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[2]/'jetson'),str(Path(__file__).resolve().parent)]
from test_field_worker import FakeCamera, StubParts, EnvelopeEngine
from src.vision.inspection_worker import worker_main


class RunWorkerTests(unittest.TestCase):
    def test_same_camera_records_only_after_start_and_saves_after_safe_stop(self):
        FakeCamera.opened=FakeCamera.closed=0
        package=NS(manifest={'files':{},'model_version':'synthetic'},manifest_hash='fixture-package',
            recipe={'alignment_mode':'engine_affine'},capture={'width':1280,'height':720,'fps':30})
        station={'camera_device':'/dev/SYNTHETIC','quality':{'min_blur_variance':0,'min_mean_brightness':0,'max_mean_brightness':255}}
        commands,results,previews,products=(queue.Queue(maxsize=n) for n in (1,8,1,16))
        stopping,cancel,tracking=threading.Event(),threading.Event(),threading.Event();tracking.set()
        signals=NS(started_at=NS(value=0.),stop_code=NS(value=0),flush_until=NS(value=0.))
        area=NS(evaluate=lambda image:{'classification':'UNKNOWN','reason':'SYNTHETIC'})
        window=NS(update=lambda *args:{'state':'UNKNOWN','reason':'SYNTHETIC'})
        with tempfile.TemporaryDirectory() as folder, \
             patch('src.vision.inspection_worker.load_package',return_value=package), \
             patch('src.camera.gstreamer_camera.GStreamerCamera',FakeCamera), \
             patch('src.vision.detector_factory.create_detector',return_value=StubParts()), \
             patch('src.vision.engine_inspector.EngineInspector',EnvelopeEngine), \
             patch('src.vision.engine_inspector.draw_engine_overlay',side_effect=lambda image,*a,**k:image.copy()), \
             patch('src.observation.area_occupancy.load_area_occupancy',return_value=area), \
             patch('src.observation.area_occupancy.ClearWindow',return_value=window):
            commands.put(dict(type='run_capture',action='arm',folder=folder,
                request={'clip_id':'worker','duration_seconds':20,'max_frames':240,'max_bytes':64*1024*1024},
                context={'run_capture_approved':True,'camera_epoch':'fixture'}))
            failures=[]
            def run():
                try:
                    worker_main('fixture',station,'g-worker',commands,results,previews,
                        stopping,cancel,NS(value=0),products,tracking,run_capture_signals=signals)
                except Exception as error: failures.append(repr(error))
            thread=threading.Thread(target=run,daemon=True);thread.start()
            messages=[]
            try:
                limit=time.monotonic()+4
                while time.monotonic()<limit and thread.is_alive():
                    try: message=results.get(timeout=.05);messages.append(message)
                    except queue.Empty:continue
                    if message.get('status',{}).get('state')=='ARMED':break
                self.assertTrue(any(m.get('status',{}).get('state')=='ARMED' for m in messages),failures or messages)
                self.assertFalse(list((Path(folder)/'raw').iterdir()))
                signals.started_at.value=time.monotonic()
                time.sleep(.4)
                signals.stop_code.value=1
                time.sleep(.1)
                self.assertFalse(list((Path(folder)/'raw').iterdir()))
                signals.flush_until.value=time.monotonic()+4
                receipt=Path(folder)/'receipt.json'
                limit=time.monotonic()+4
                while not receipt.exists() and time.monotonic()<limit:time.sleep(.02)
                self.assertTrue(receipt.exists(),failures)
                rows=[json.loads(line) for line in (Path(folder)/'frames.jsonl').read_text(encoding='utf-8').splitlines()]
                self.assertGreater(len(rows),0)
                self.assertTrue(all(row['freshness']['estimated_source_monotonic']>=signals.started_at.value for row in rows))
                self.assertTrue(all(row['tensor_status']=='NOT_REQUESTED' for row in rows))
                self.assertTrue(all(row['observation']['mode']=='PRODUCTION_TRACKING' for row in rows if row['observation']))
            finally:
                stopping.set();signals.flush_until.value=time.monotonic()+4;thread.join(4)
            self.assertFalse(thread.is_alive())
            self.assertEqual(FakeCamera.opened,1);self.assertEqual(FakeCamera.closed,1)
            while not results.empty():messages.append(results.get_nowait())
            self.assertFalse([m for m in messages if m['type'] in ('result','fault')],messages)


if __name__=='__main__':unittest.main()
