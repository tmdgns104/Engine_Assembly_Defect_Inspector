"""Local recovery adapter. Frozen classifiers and runtime code remain unchanged.

The complete old crop rectangle is retained. Only its optional corner margin may
be padded; every pixel of the TRAIN-defined essential polygon must have source
support. A TRAIN descriptor bank is tried only after the original pose/direction
gate rejects. It must pass the same numeric pose and direction gates.
"""
import json
from pathlib import Path
import sys

import cv2
import numpy as np

PROJECT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT/'notebook/training/engine_baseline'))
from preprocess import BodyPreprocessor, PARTS, padded_224, normalized_correlation
from src.vision.engine_rectification import rectify_image
from src.vision.engine_pose import transform_polygon


def essential_support(support,polygon):
    mask=np.zeros(support.shape,np.uint8)
    cv2.fillPoly(mask,[np.asarray(polygon,np.int32)],1)
    values=support[mask.astype(bool)]
    missing=int(np.count_nonzero(values<1.0-1e-6))
    return dict(ok=bool(len(values) and missing==0),pixels=int(len(values)),
                unsupported_pixels=missing,coverage=float(np.mean(values)) if len(values) else 0.)


def direction_score(reference,aligned):
    return normalized_correlation(reference,aligned)


class RecoveryPreprocessor(BodyPreprocessor):
    def __init__(self,config_path):
        super().__init__(config_path)
        self.version='essential-support-train-bank-v1'

    def check_direction(self,canonical):
        x1,y1,x2,y2=self.cfg['orientation_anchor_xyxy']
        gray=cv2.cvtColor(canonical,cv2.COLOR_BGR2GRAY)
        return direction_score(self.reference_gray[y1:y2,x1:x2],gray[y1:y2,x1:x2])

    def extract(self,image,canonical,matrix,output):
        # INTER_LINEAR support verifies the footprint of the actual image warp.
        coverage=cv2.warpAffine(np.ones(image.shape[:2],np.float32),cv2.invertAffineTransform(matrix),
            (self.cfg['frame_width'],self.cfg['frame_height']),flags=cv2.INTER_LINEAR)
        output['parts']={};crops={}
        for part,(x1,y1,x2,y2) in self.cfg['crop_regions_xyxy'].items():
            region=canonical[y1:y2,x1:x2]
            essential=self.cfg['essential_polygons'][part]
            check=essential_support(coverage,essential)
            reason='ESSENTIAL_REGION_OUT_OF_SOURCE' if not check['ok'] else 'EMPTY_OR_FLAT_CROP' if region.size==0 or region.std()<4 else None
            output['parts'][part]=dict(status='FAILED' if reason else 'VALID',reason=reason,
                canonical_xyxy=[x1,y1,x2,y2],essential_polygon=essential,essential_support=check,
                source_coverage=float(coverage[y1:y2,x1:x2].mean()),
                source_polygon=transform_polygon([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],matrix).tolist(),
                optional_margin_padded=bool(np.any(coverage[y1:y2,x1:x2]<1)))
            if not reason:crops[part]=padded_224(region)
        output['status']='VALID' if len(crops)==4 else 'PARTIAL'
        output['reason']=None if len(crops)==4 else 'ONE_OR_MORE_CROPS_FAILED'
        return output,canonical,crops

    def process(self,image):
        # Explicitly keep the original estimator first. Bank fallback also needs
        # to run when the original estimate is geometrically plausible but upside down.
        bank_points,bank_des=self.estimator.bank_points,self.estimator.bank_des
        self.estimator.bank_points=self.estimator.bank_des=None
        try:output,canonical,_=super().process(image)
        finally:self.estimator.bank_points,self.estimator.bank_des=bank_points,bank_des
        output['preprocessing_version']=self.version
        output['pose_route']='BASELINE'
        output['baseline_status']=output['status'];output['baseline_reason']=output['reason']
        if output['status']=='FAILED' and output.get('pose') and bank_des is not None:
            output['baseline_pose']=output['pose']
            output['baseline_direction_score']=output.get('orientation_anchor_correlation')
            box=next(p['bounding_box'] for p in output['products'] if p['confidence']>=self.cfg['decision_policy']['product_confidence'])
            pose=self.estimator._estimate(image,[box[k] for k in ('x1','y1','x2','y2')],bank=True)
            attempt=dict(ok=pose.ok,reason=pose.reason,matrix=pose.matrix.tolist() if pose.matrix is not None else None,
                angle_deg=pose.angle_deg,scale=pose.scale,inliers=pose.inliers,good_matches=pose.good_matches,
                median_error_px=pose.median_error_px,diagnostics=pose.diagnostics)
            output['bank_attempt']=attempt
            if pose.ok:
                candidate=rectify_image(image,pose.matrix,self.cfg)
                score=self.check_direction(candidate)
                output['bank_direction_score']=score
                if score>=self.cfg['min_orientation_anchor_correlation']:
                    output['pose']=attempt;output['orientation_anchor_correlation']=score
                    output['pose_route']='TRAIN_BODY_BANK';canonical=candidate
                    output['status']='POSE_ACCEPTED'
        if output['status']=='FAILED':return output,canonical,{}
        return self.extract(image,canonical,np.asarray(output['pose']['matrix']),output)
