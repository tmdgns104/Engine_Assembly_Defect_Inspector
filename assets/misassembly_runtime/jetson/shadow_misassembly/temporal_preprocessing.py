"""Explicit sequence adapter around the unchanged independent-image pipeline."""
from copy import deepcopy
import numpy as np

from pose_stability import TemporalPoseGuard
from src.vision.engine_rectification import rectify_image


class TemporalShadowPreprocessor:
    def __init__(self, base):
        self.base = base
        self.cfg = base.cfg
        self.guard = TemporalPoseGuard(self.cfg)
        self.context = None

    def process(self, image):
        context, self.context = self.context, None
        if context is None:
            self.guard.reset()
            return self.base.process(image)
        if self.guard.requires_seed(context):
            output,canonical,crops=self.base.process(image)
        else:
            # Same frozen envelope call; current body correspondences already
            # produce a fresh pose. Re-running all absolute ORB banks here adds
            # latency but does not select the motion matrix. Cold starts retain
            # the full absolute path and independent still images are unchanged.
            prediction=self.base.detector.predict(image,imgsz=[640,640],rect=False,device=0,quantize=32,
                conf=.25,iou=.45,augment=False,verbose=False)[0]
            detected=[dict(class_name='product_envelope',confidence=float(conf),
                           bounding_box=dict(zip(('x1','y1','x2','y2'),map(float,box))))
                      for box,conf in zip(prediction.boxes.xyxy.cpu().numpy(),prediction.boxes.conf.cpu().numpy())]
            output=dict(status='FAILED',reason='ABSOLUTE_DIAGNOSTIC_NOT_REQUESTED',products=detected,parts={},
                        absolute_diagnostic_scope='Cold start only; fresh current body flow is the ongoing pose estimator')
            canonical,crops=None,{}
        absolute = deepcopy(output)
        products=[p for p in output.get('products',[]) if p['confidence']>=self.cfg['decision_policy']['product_confidence']]
        if len(products)!=1:
            self.guard.reset()
            output.update(status='FAILED', reason='TEMPORAL_SINGLE_PRODUCT_REQUIRED',pose=dict(ok=False,matrix=None))
            return output, None, {}
        if self.guard.requires_seed(context) and context.quality_valid:
            from absolute_body_seed import estimate_body_seed
            seed,canonical,crops=estimate_body_seed(self.base,image,output)
            output['sequence_seed_attempt']=seed
            if not seed['ok']:
                self.guard.reset()
                output.update(status='FAILED',reason=seed['reason'],pose=dict(ok=False,matrix=None),
                              absolute_preprocessing=absolute)
                return output,canonical,crops
            output.update(seed['crop_evidence'])
            output.update(pose=seed,pose_route='MULTI_REGION_RECIPROCAL_BODY_SEED',
                          orientation_anchor_correlation=seed['orientation_anchor_correlation'])
        selected = self.guard.choose(image, output, context)
        output['absolute_preprocessing'] = absolute
        output['temporal_pose'] = selected
        output['preprocessing_version'] = self.guard.version
        if not selected['ok']:
            output.update(status='FAILED', reason=selected['reason'], pose=dict(ok=False,matrix=None))
            return output, None, {}
        if selected['route'] == 'ABSOLUTE_SEED':
            return output, canonical, crops
        matrix = np.asarray(selected['matrix'])
        canonical = rectify_image(image,matrix,self.cfg)
        score = self.base.check_direction(canonical)
        output['orientation_anchor_correlation'] = score
        if score < self.cfg['min_orientation_anchor_correlation']:
            self.guard.reset()
            output.update(status='FAILED',reason='TEMPORAL_BODY_DIRECTION_NOT_VERIFIED',pose=dict(ok=False,matrix=None))
            return output, canonical, {}
        motion = selected['motion_evidence']
        output.update(pose=dict(ok=True,matrix=matrix.tolist(),angle_deg=motion['angle_deg'],scale=motion['scale'],
                               good_matches=motion['forward_backward_kept'],inliers=motion['inliers'],
                               median_error_px=motion['median_error_px'],spatial_support=motion['spatial_support'],
                               reason='CURRENT_BODY_CORRESPONDENCES'),pose_route=selected['route'])
        output,canonical,crops = self.base.extract(image,canonical,matrix,output)
        if output['status'] != 'VALID':
            self.guard.reset()
        return output,canonical,crops
