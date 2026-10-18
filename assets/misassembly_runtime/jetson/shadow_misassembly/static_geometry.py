"""Reject mutually inconsistent current body regions before classification.

The one-pixel budget matches the existing LK forward/backward correspondence budget.
It is frozen before new LIVE observations. No class, label, history average or confidence
enters this check. A retained image reference is not an accepted pose for a rejected frame.
"""
import numpy as np
from body_motion import BodyMotionEstimator
from pose_stability import TemporalPoseGuard

BODY_REGION_BUDGET_PX = 1.0

def region_agreement(reference, current, matrix, regions):
    reference=np.asarray(reference,dtype=np.float64)
    current=np.asarray(current,dtype=np.float64)
    matrix=np.asarray(matrix,dtype=np.float64)
    if (reference.ndim!=2 or reference.shape[1]!=2 or reference.shape!=current.shape
            or matrix.shape!=(2,3) or not all(np.isfinite(x).all() for x in [reference,current,matrix])):
        return dict(ok=False,reason='INVALID_BODY_CORRESPONDENCES')
    residual=reference@matrix[:,:2].T+matrix[:,2]-current
    within_frozen_fit=np.linalg.norm(residual,axis=1)<=3.0
    groups=[]
    for index,(x1,y1,x2,y2) in enumerate(regions):
        inside=((reference[:,0]>=x1)&(reference[:,0]<=x2)
                &(reference[:,1]>=y1)&(reference[:,1]<=y2)&within_frozen_fit)
        if inside.sum()>=3:
            groups.append(dict(region=index,points=int(inside.sum()),median_residual_xy=np.median(residual[inside],axis=0).tolist()))
    if len(groups)<2:
        return dict(ok=False,reason='BODY_REGIONS_INSUFFICIENT',regions=groups)
    medians=np.asarray([group['median_residual_xy'] for group in groups])
    disagreement=float(np.linalg.norm(medians[:,None]-medians[None,:],axis=2).max())
    return dict(ok=disagreement<=BODY_REGION_BUDGET_PX,
        reason='BODY_REGIONS_AGREE' if disagreement<=BODY_REGION_BUDGET_PX else 'CURRENT_BODY_REGIONS_DISAGREE',
        maximum_region_disagreement_px=disagreement,budget_px=BODY_REGION_BUDGET_PX,
        budget_origin='Existing one-pixel LK correspondence cycle budget; frozen before LIVE300',regions=groups)

class StaticBodyMotionEstimator(BodyMotionEstimator):
    def estimate(self,image):
        measured=super().estimate(image)
        if not measured['ok']:
            return measured
        check=region_agreement(measured['reference_points'],measured['current_points'],
            measured['matrix'],self.config['fixed_body_feature_regions_xyxy'])
        measured['body_region_agreement']=check
        if not check['ok']:
            # Preserve the rejected geometry as diagnostics only, never as matrix.
            measured.update(rejected_matrix=measured['matrix'],matrix=None,ok=False,reason=check['reason'])
        return measured

class StaticPoseGuard(TemporalPoseGuard):
    version='shadow-static-current-body-region-consistency-v1'

    def __init__(self,config):
        super().__init__(config)
        self.motion=StaticBodyMotionEstimator(config)

    def reset(self):
        super().reset()
        self.motion=StaticBodyMotionEstimator(self.config)

    def reject(self,reason,**evidence):
        if reason=='CURRENT_BODY_REGIONS_DISAGREE':
            # Do not contaminate/reseed a reference from one inconsistent image.
            # This frame has no matrix or crops; the next frame must independently
            # establish current-image correspondences. Track/time/quality guards remain.
            return dict(ok=False,reason=reason,matrix=None,reference_retained=True,
                current_pose_reused=False,**evidence)
        return super().reject(reason,**evidence)
