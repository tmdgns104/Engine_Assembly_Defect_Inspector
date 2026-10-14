"""Deterministic camera/model boundary for the REAL worker loop, never field AI.

No production call site imports this file. Source bytes, three-frame policy,
encoding, service monitor, Journal and AssemblyInspector run unchanged.
"""
from types import SimpleNamespace as NS
from unittest.mock import patch
from src.runtime.diagnostic_devices import DiagnosticCamera
from src.decision.engine_dynamic import SLOTS
from src.contracts import DetectionResult

class Camera(DiagnosticCamera):
    def capture(self):
        frame=super().capture()
        self.frame_info['integrity']={'valid':True,'scope':'ISOLATED_GENERATED_IMAGE'}
        # Three distinct fixture images exercise the frozen duplicate guard.
        frame.image[0,0,0]=self.sequence%255
        return frame

class PartsDetector:
    def __init__(self,package): pass
    def detect(self,frame): return DetectionResult(frame.frame_id,(), 'fixture',0)
    def runtime_metadata(self): return dict(backend='mock',device='cpu',source='ISOLATED_FIXTURE')
    def close(self): pass

class Engine:
    def __init__(self,package):
        self.detector=PartsDetector(package)
        self.estimator=NS(cfg={'decision_policy':{'product_confidence':.5}})
    def detect(self,frame,detected,parts_detector=None):
        fresh=detected['freshness']
        product=dict(class_name='product_envelope',confidence=.99,
            bounding_box=dict(x1=10,y1=20,x2=90,y2=100))
        detected['detections']=[product]
        detected['engine_dynamic']=dict(frame_id=frame.frame_id,source_pts_ns=fresh['source_pts_ns'],
            camera_epoch=fresh['camera_epoch'],decision='PASS',reason_code='ALL_REQUIRED_PARTS_PRESENT',
            product=product,product_selection={'valid_count':1},quality_valid=True,stable=True,
            pose={'reliable':True},assignment_reliable=True,slot_states=dict.fromkeys(SLOTS,'PRESENT'),
            stage_timings_ms={'product_detection_ms':0})
    def observe_product(self,frame,detected):
        self.detect(frame,detected); return detected['engine_dynamic']
    def close(self): pass

def worker(*args):
    from src.vision.inspection_worker import worker_main
    # Replay/fake devices are explicit test boundaries; do not patch decisions.
    with patch('src.camera.gstreamer_camera.GStreamerCamera',Camera), \
         patch('src.vision.detector_factory.create_detector',PartsDetector), \
         patch('src.vision.engine_inspector.EngineInspector',Engine), \
         patch('src.observation.area_occupancy.load_area_occupancy',lambda path:None):
        worker_main(*args)

class AssemblyModels:
    def __init__(self,decision):
        self.decision=decision; self.resets=0
        self.processor=NS(guard=NS(reset=self.reset))
    def reset(self): self.resets+=1
    def process(self,image,context):
        names=('pipe_left','pipe_right','exhaust','symbol')
        record=dict(shadow_state=self.decision, parts={name:dict(predicted_state='CORRECT',
            class_scores={'CORRECT':1.0}) for name in names})
        if self.decision=='FAIL_CANDIDATE':
            record['parts']['exhaust']=dict(predicted_state='REVERSED',class_scores={'REVERSED':1.0})
        return record,image,{name:image.copy() for name in names}


class PassageCamera(Camera):
    """5 Hz synthetic source keeps real sequence gaps visible, never renumbers."""
    mode_path = None
    def capture(self):
        import time
        import json
        time.sleep(.14)
        frame=super().capture()
        command=json.loads(self.mode_path.read_text())
        # Encode the scripted box in the image itself; detector reads this exact
        # frame, not an independently sampled control file or a cached bbox.
        values=command.get('box',[10,20,90,100])
        frame.image[0,1:5,0]=values
        return frame

class PassageEngine(Engine):
    def detect(self,frame,detected,parts_detector=None):
        super().detect(frame,detected,parts_detector)
        box=dict(zip(('x1','y1','x2','y2'),map(int,frame.image[0,1:5,0])))
        detected['detections'][0]['bounding_box']=box
        detected['engine_dynamic']['product']=detected['detections'][0]


def passage_worker(*args):
    from pathlib import Path
    from src.vision.inspection_worker import worker_main
    PassageCamera.mode_path=Path(args[1]['fixture_passage_path'])
    with patch('src.camera.gstreamer_camera.GStreamerCamera',PassageCamera), \
         patch('src.vision.detector_factory.create_detector',PartsDetector), \
         patch('src.vision.engine_inspector.EngineInspector',PassageEngine), \
         patch('src.observation.area_occupancy.load_area_occupancy',lambda path:None):
        worker_main(*args)
