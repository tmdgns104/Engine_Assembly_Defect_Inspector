"""Literal edge/letterbox expectations plus original postprocess parity."""
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]/'jetson'
sys.path.insert(0,str(ROOT))
from src.contracts import CameraFrame
from src.vision.tensorrt_detector import TensorRTDetector
from src.vision.tensorrt_preprocess import preprocess
from src.vision.tensorrt_postprocess import postprocess

CONTRACT=dict(layout='BCN',box_format='xywh',coordinate_space='letterbox_pixels',
 class_score_semantics='sigmoid_probabilities',objectness_semantics='absent',number_of_classes=1,
 tensor_shape_contract=dict(name='output0',dtype='float32',shape=[1,5,8400],
 batch_axis=0,feature_axis=1,candidate_axis=2))


class Package:
    names=['product_envelope']
    def snapshot(self):return {'manifest':{'detector':{'input':{'dtype':'float32'},'output':CONTRACT,
        'source_model_sha256':'synthetic'}},'preprocessing':{'confidence':.25,'nms_iou':.45}}


class Executor:
    def __init__(self,raw):self.raw=raw
    def execute(self,tensor):return {'output0':self.raw}
    def close(self):pass


class BboxTests(unittest.TestCase):
    def test_same_frame_input_identity_and_clipped_coordinate(self):
        raw=np.zeros((1,5,8400),np.float32)
        raw[0,:,0]=[300,400,400,320,.9]
        raw[0,:,1]=[300,400,400,320,.8] # Must be suppressed by NMS.
        image=np.full((720,1280,3),100,np.uint8)
        frame=CameraFrame(image,'epoch-8',datetime.now(timezone.utc),1280,720,'fixture')
        detector=TensorRTDetector(Package(),Executor(raw))
        baseline=detector.detect(frame)
        detector.capture_diagnostics=True
        traced=detector.detect(frame)
        self.assertEqual(baseline.detections,traced.detections)
        self.assertEqual(detector.diagnostic_frame_id,frame.frame_id)
        diag=detector.last_diagnostics
        trace=diag['bbox_coordinate_trace'][0]
        self.assertEqual(trace['restored_before_clip'],[200,200,1000,840])
        self.assertEqual(trace['restored_after_clip'],[200,200,1000,720])
        self.assertEqual(trace['clipped_edges'],['bottom'])
        self.assertEqual(diag['kept_raw_indices'],[0])
        self.assertEqual(diag['nms_suppressed_raw_indices'],[1])
        tensor,_=preprocess(image)
        self.assertEqual(diag['input_tensor_sha256'],hashlib.sha256(tensor.tobytes()).hexdigest())
        detector.capture_diagnostics=False;detector.detect(frame)
        self.assertIsNone(detector.diagnostic_output)
        self.assertIsNone(detector.diagnostic_frame_id)

    def test_100_outputs_equal_original_results(self):
        source=Path(__file__).parent/'fixtures/postprocess_before_diagnostics.py'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
            '7916cd337d81ba43ba831413b3413b01eed8733f40a1f6ed61f3b8de19c68b73')
        spec=importlib.util.spec_from_file_location('original_postprocess',source)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        rng=np.random.default_rng(140014)
        _,transform=preprocess(np.zeros((720,1280,3),np.uint8))
        for _ in range(100):
            raw=np.zeros((1,5,8400),np.float32)
            raw[0,0,:20]=rng.uniform(100,540,20)
            raw[0,1,:20]=rng.uniform(180,510,20)
            raw[0,2:4,:20]=rng.uniform(20,150,(2,20))
            raw[0,4,:20]=rng.uniform(0,1,20)
            args=({'output0':raw},CONTRACT,['product_envelope'],.25,.45,transform)
            self.assertEqual(old.postprocess(*args),postprocess(*args,diagnostics={},candidate_trace=True))


if __name__=='__main__':unittest.main()
