import unittest
import numpy as np
from src.contracts import DetectorError
from src.vision.tensorrt_preprocess import ImageTransform
from test_trt_schema import output_contract

NAMES=['bolt','nut','washer','cap']


def raw(rows):
    value=np.zeros((1,8,8400),np.float32)
    for i,(box,cls,score) in enumerate(rows):
        value[0,:4,i]=box
        value[0,4+cls,i]=score
    return {'output0':value}


class PostprocessTests(unittest.TestCase):
    def process(self, outputs, transform=None, conf=.5, iou=.5):
        from src.vision.tensorrt_postprocess import postprocess
        return postprocess(outputs,output_contract(),NAMES,conf,iou,
                           transform or ImageTransform((640,640),(640,640),1.,(0,0,0,0)))

    def test_decode_and_class_mapping(self):
        detections=self.process(raw([([100,200,20,40],2,.9)]))
        self.assertEqual(len(detections),1)
        self.assertEqual(detections[0].class_name,'washer')
        self.assertEqual(detections[0].bounding_box.to_dict(),dict(x1=90.,y1=180.,x2=110.,y2=220.))

    def test_confidence_strict_boundary_and_single_label(self):
        outputs=raw([([10,10,8,8],0,.5),([30,30,8,8],1,.75)])
        outputs['output0'][0,4,1]=.75
        result=self.process(outputs)
        self.assertEqual([x.class_id for x in result],[0])
        self.assertEqual(result[0].confidence,.75)

    def test_class_aware_nms(self):
        result=self.process(raw([([100,100,40,40],0,.9),([100,100,40,40],0,.8),
                                 ([100,100,40,40],1,.7)]))
        self.assertEqual([x.class_id for x in result],[0,1])

    def test_iou_equal_retained_greater_suppressed(self):
        # Contained 10x5 and 10x10 boxes have IoU exactly 0.5.
        outputs=raw([([10,10,10,10],0,.9),([10,10,10,5],0,.8)])
        self.assertEqual(len(self.process(outputs,iou=.5)),2)
        self.assertEqual(len(self.process(outputs,iou=.49)),1)

    def test_max_det_300(self):
        rows=[([2+(i%30)*20,2+(i//30)*20,2,2],0,.8) for i in range(301)]
        self.assertEqual(len(self.process(raw(rows))),300)

    def test_restore_padding_gain_then_clip(self):
        transform=ImageTransform((720,1280),(360,640),.5,(0,140,0,140))
        result=self.process(raw([([320,320,660,360],0,.9)]),transform)
        self.assertEqual(result[0].bounding_box.to_dict(),dict(x1=0.,y1=0.,x2=1280.,y2=720.))

    def test_nms_happens_before_clipping(self):
        # Original boxes have IoU .1; clipping would make them identical.
        rows=[([-40,10,100,20],0,.9),([5,10,10,20],0,.8)]
        self.assertEqual(len(self.process(raw(rows))),2)

    def test_deterministic_ties_score_class_then_raw_index(self):
        rows=[([40,40,10,10],1,.8),([20,20,10,10],0,.8),([60,60,10,10],0,.8)]
        result=self.process(raw(rows))
        self.assertEqual([x.class_id for x in result],[0,0,1])
        self.assertEqual([x.bounding_box.x1 for x in result],[15,55,35])

    def test_empty_is_valid(self):self.assertEqual(self.process(raw([])),())

    def test_reject_name_shape_dtype_nonfinite_score_and_bad_box(self):
        for mode in ('name','shape','dtype','nan','score','negative_width','collapsed_after_clip'):
            with self.subTest(mode=mode):
                outputs=raw([([10,10,4,4],0,.9)])
                if mode=='name':outputs={'wrong':outputs['output0']}
                if mode=='shape':outputs['output0']=outputs['output0'][:,:,:10]
                if mode=='dtype':outputs['output0']=outputs['output0'].astype(np.float64)
                if mode=='nan':outputs['output0'][0,0,0]=np.nan
                if mode=='score':outputs['output0'][0,4,0]=1.1
                if mode=='negative_width':outputs['output0'][0,2,0]=-1
                if mode=='collapsed_after_clip':outputs['output0'][0,0,0]=-10
                with self.assertRaisesRegex(DetectorError,'OUTPUT_CONTRACT_MISMATCH'):
                    self.process(outputs)
