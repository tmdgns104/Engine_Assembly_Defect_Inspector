"""Opt-in shadow fallback: reciprocal body matching after frozen recovery fails.

Successful frozen inputs are returned unchanged. No inspection part determines
pose, and no label, filename, guide angle or capture order is accepted as input.
"""
from dataclasses import replace
import cv2
import numpy as np
from recovery import RecoveryPreprocessor
from src.vision.engine_pose import transform_polygon, _expanded_mask
from src.vision.engine_rectification import rectify_image
from robustness import reciprocal_pairs, spatial_support


class ReciprocalMatcher:
    def __init__(self,matcher):
        self.matcher=matcher
        self.pairs=[]
    def knnMatch(self,reference,current,k):
        self.pairs=reciprocal_pairs(self.matcher.knnMatch(reference,current,k=k),
                                    self.matcher.match(current,reference))
        return self.pairs


class CachedFeatures:
    def __init__(self,keypoints,descriptors):
        self.keypoints,self.descriptors=keypoints,descriptors
    def detectAndCompute(self,*_):return self.keypoints,self.descriptors


class RobustShadowPreprocessor(RecoveryPreprocessor):
    version='shadow-reciprocal-body-v1'

    def process(self,image):
        output,canonical,crops=super().process(image)
        if output['status']!='FAILED' or not output.get('pose'):
            return output,canonical,crops
        estimator=self.estimator
        box=[output['products'][0]['bounding_box'][k] for k in ('x1','y1','x2','y2')]
        orb,matcher=estimator.orb,estimator.matcher
        kp,des=orb.detectAndCompute(estimator._gray(image),_expanded_mask(image.shape,box,.18))
        if des is None:return output,canonical,crops
        reciprocal=ReciprocalMatcher(matcher)
        estimator.orb=CachedFeatures(kp,des);estimator.matcher=reciprocal
        try:
            pose=estimator._estimate(image,box,bank=True)
        finally:
            estimator.orb,estimator.matcher=orb,matcher
        good=[pair[0] for pair in reciprocal.pairs if pair[0].distance<estimator.cfg['registration']['ratio_test']*pair[1].distance]
        unique={}
        for match in sorted(good,key=lambda m:m.distance):unique.setdefault(match.trainIdx,match)
        good=list(unique.values())
        src=np.float32([estimator.bank_points[m.queryIdx] for m in good]).reshape(-1,2)
        dst=np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1,2)
        errors=np.linalg.norm(transform_polygon(src,pose.matrix)-dst,axis=1) if pose.matrix is not None and len(src) else np.full(len(src),1e9)
        spatial=spatial_support(src,errors,self.cfg['fixed_body_feature_regions_xyxy'])
        attempt=dict(ok=False,reason=pose.reason,matrix=pose.matrix.tolist() if pose.matrix is not None else None,
            angle_deg=pose.angle_deg,scale=pose.scale,inliers=pose.inliers,good_matches=pose.good_matches,
            median_error_px=pose.median_error_px,diagnostics=pose.diagnostics,spatial_support=spatial,
            reference_points=src.tolist(),current_points=dst.tolist(),reprojection_errors=errors.tolist(),
            current_keypoints=[dict(x=k.pt[0],y=k.pt[1],size=k.size) for k in kp])
        output['reciprocal_attempt']=attempt
        if not pose.ok:return output,canonical,crops
        if not spatial['ok']:
            attempt['reason']='INSUFFICIENT_SPATIAL_BODY_SUPPORT'
            return output,canonical,crops
        candidate=rectify_image(image,pose.matrix,self.cfg)
        score=self.check_direction(candidate)
        attempt['orientation_anchor_correlation']=score
        if score<self.cfg['min_orientation_anchor_correlation']:
            attempt['reason']='BODY_DIRECTION_NOT_VERIFIED'
            return output,canonical,crops
        attempt.update(ok=True,reason='RECIPROCAL_TRAIN_BODY_BANK')
        output['frozen_recovery_pose']=output['pose']
        output['frozen_recovery_reason']=output['reason']
        output.update(pose=attempt,pose_route='RECIPROCAL_TRAIN_BODY_BANK',
                      orientation_anchor_correlation=score,preprocessing_version='shadow-reciprocal-body-v1')
        return self.extract(image,candidate,pose.matrix,output)
