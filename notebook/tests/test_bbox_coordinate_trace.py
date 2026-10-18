"""Literal 640 letterbox cases: instrumentation must not change detector decisions."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.vision.tensorrt_postprocess import postprocess
from src.vision.tensorrt_preprocess import preprocess
from src.observation.engine_envelope import envelope_provider
from src.runtime.standalone import arrival_evidence
CONTRACT=dict(layout='BCN',box_format='xywh',coordinate_space='letterbox_pixels',
 class_score_semantics='sigmoid_probabilities',objectness_semantics='absent',number_of_classes=1,
 tensor_shape_contract=dict(name='output0',dtype='float32',shape=[1,5,8400],
 batch_axis=0,feature_axis=1,candidate_axis=2))
class BboxTraceTests(unittest.TestCase):
 def run_box(self,xywh):
  raw=np.zeros((1,5,8400),np.float32);raw[0,:4,17]=xywh;raw[0,4,17]=.75
  _,transform=preprocess(np.zeros((720,1280,3),np.uint8))
  diag={}
  output=postprocess({'output0':raw},CONTRACT,['product_envelope'],.25,.45,transform,diagnostics=diag)
  plain=postprocess({'output0':raw},CONTRACT,['product_envelope'],.25,.45,transform)
  self.assertEqual(output,plain)
  return output,diag
 def test_trace_distinguishes_model_overflow_from_final_clip(self):
  out,diag=self.run_box([320,380,400,280])
  trace=diag.get('bbox_coordinate_trace')
  self.assertIsNotNone(trace)
  self.assertEqual(trace[0]['raw_index'],17)
  self.assertEqual(trace[0]['raw_xywh'],[320.,380.,400.,280.])
  self.assertEqual(trace[0]['restored_before_clip'],[240.,200.,1040.,760.])
  self.assertEqual(trace[0]['restored_after_clip'],[240.,200.,1040.,720.])
  self.assertEqual(trace[0]['clipped_edges'],['bottom'])
  self.assertEqual(trace[0]['confidence'],.75)
 def test_valid_box_is_not_extended_and_border_not_silently_accepted(self):
  from dataclasses import asdict
  for raw,bottom,allowed in [([320,350,400,200],620.,True),([320,380,400,280],720.,False)]:
   out,diag=self.run_box(raw)
   detections=[d.to_dict() if hasattr(d,'to_dict') else asdict(d) for d in out]
   provider=envelope_provider(detections,1280,720,.5)
   packet=dict(monotonic_s=11,camera_epoch='e',generation='g',integrity={'valid':True},
    provider=asdict(provider))
   self.assertEqual(out[0].bounding_box.y2,bottom)
   zone={'polygon_normalized':[[0,0],[1,0],[1,1],[0,1]]}
   self.assertEqual(arrival_evidence(packet,10,'e','g',zone),allowed)
   for accepted,epoch,gen in [(12,'e','g'),(10,'other','g'),(10,'e','other')]:
    self.assertFalse(arrival_evidence(packet,accepted,epoch,gen,zone))

if __name__=='__main__':unittest.main(verbosity=2)

