"""Shadow-only geometry guidance and explicit fresh-identity track recovery.

Neither utility changes production tracking or classifier thresholds. Re-acquisition
never claims that a reappearing object is the old product, even in a one-engine bench.
"""
import math
import numpy as np
from src.tracking.single_active import SingleActiveTracker


def reciprocal_pairs(forward, reverse):
    reverse_index={m.queryIdx:m.trainIdx for m in reverse}
    return [pair for pair in forward if len(pair)==2 and
            reverse_index.get(pair[0].trainIdx)==pair[0].queryIdx]


def spatial_support(points, errors, regions):
    """Require three geometrically agreeing points in each of two body areas.

    This is an additional extrapolation safeguard, never a relaxed RANSAC gate.
    The 3px error is the existing RANSAC radius; body regions are TRAIN-frozen.
    """
    points=np.asarray(points,float).reshape(-1,2)
    errors=np.asarray(errors,float)
    counts=[]
    for x1,y1,x2,y2 in regions:
        counts.append(int(((points[:,0]>=x1)&(points[:,0]<x2)&(points[:,1]>=y1)&
                           (points[:,1]<y2)&(errors<=3)).sum()))
    return dict(ok=sum(n>=3 for n in counts)>=2,counts=counts,
                rule='At least 3 residual<=3px correspondences in each of 2 frozen body regions')


def safe_inspection_zone(config, matrix, frame_size):
    """Allowed source position of the transformed canonical product center.

    All frozen essential vertices are retained. This affine geometric guide is not
    an image-quality approval; the existing full bilinear-support gate still applies.
    """
    if matrix is None:
        return dict(inside=False,guidance=['POSE_REQUIRED'],center_bounds_xyxy=None)
    matrix=np.asarray(matrix,dtype=float)
    if matrix.shape!=(2,3) or not np.isfinite(matrix).all():
        return dict(inside=False,guidance=['POSE_REQUIRED'],center_bounds_xyxy=None)
    width,height=frame_size
    x1,y1,x2,y2=config['canonical_product_box_xyxy']
    canonical_center=np.array([(x1+x2)/2,(y1+y2)/2])
    vertices=np.concatenate([np.asarray(p,float) for p in config['essential_polygons'].values()])
    offsets=(vertices-canonical_center) @ matrix[:,:2].T
    lower=-offsets.min(axis=0)
    upper=np.array([width-1,height-1])-offsets.max(axis=0)
    center=matrix[:,:2] @ canonical_center+matrix[:,2]
    guidance=[]
    if np.any(lower>upper):
        guidance=['INSUFFICIENT_MARGIN']
    else:
        if center[0]<lower[0]:guidance.append('MOVE_RIGHT')
        if center[0]>upper[0]:guidance.append('MOVE_LEFT')
        if center[1]<lower[1]:guidance.append('MOVE_DOWN')
        if center[1]>upper[1]:guidance.append('MOVE_UP')
    return dict(inside=not guidance,guidance=guidance or ['IN_ZONE'],
                center_bounds_xyxy=[float(lower[0]),float(lower[1]),float(upper[0]),float(upper[1])],
                center_xy=center.tolist(),basis='FROZEN_ESSENTIAL_GEOMETRY_AT_MEASURED_POSE',
                limitation='Geometry only; not a guarantee of visibility, glare, pose or classification')


class ShadowTrackRecovery:
    """After LOST, require three fresh, stable, single-product observations.

    The existing reset_lost API retires identity and keeps its monotonic counter.
    A new identity resets downstream three-frame history by its existing key. This
    intentionally favors fragmented IDs over an unproved same-product association.
    """
    def __init__(self,config):
        self.tracker=SingleActiveTracker(config)
        self.config=config
        self.last_update=None
        self.previous_candidate=None
        self.stable_count=0
        self.last_sequence=-1
        self.last_event=None

    def step(self,frame,*,quality_valid=True):
        self.last_event=None
        if frame.sequence<=self.last_sequence:
            return self.tracker.step(frame)  # Existing ordering/replay contract.
        self.last_sequence=frame.sequence
        recovering=self.last_update is not None and self.last_update.state.value=='LOST'
        if recovering:
            if not quality_valid or len(frame.observations)!=1:
                self.previous_candidate=None;self.stable_count=0
            else:
                current=frame.observations[0]
                prior=self.previous_candidate
                coherent=False
                evidence={}
                if prior is not None:
                    previous,prior_time=prior
                    a,b=previous.bbox,current.bbox
                    elapsed=frame.monotonic_s-prior_time
                    distance=math.hypot(a.center_x-b.center_x,a.center_y-b.center_y)
                    intersection=max(0,min(a.x2,b.x2)-max(a.x1,b.x1))*max(0,min(a.y2,b.y2)-max(a.y1,b.y1))
                    union=a.width*a.height+b.width*b.height-intersection
                    iou=intersection/union if union else 0
                    ratio=b.width*b.height/(a.width*a.height) if a.width*a.height else 0
                    limit=self.config.max_center_step_norm+(self.config.max_center_speed_norm_s or 0)*elapsed
                    coherent=(current.source==previous.source and 0<elapsed<=1.0 and distance<=limit
                              and (iou>=.02 or distance<=.12) and .5<=ratio<=2)
                    evidence=dict(elapsed_s=elapsed,center_distance=distance,iou=iou,area_ratio=ratio,
                                  product_source=current.source)
                self.stable_count=self.stable_count+1 if coherent else 1
                self.previous_candidate=(current,frame.monotonic_s)
                if self.stable_count>=3:
                    old_id=self.last_update.active_track_id
                    reason=self.last_update.reason_code.value if self.last_update.reason_code else None
                    self.tracker.reset_lost()
                    self.last_event=dict(event='SHADOW_REACQUIRED',old_track_id=old_id,
                        prior_loss_reason=reason,identity_relation='NEW_IDENTITY_NOT_SAME_PRODUCT_CLAIM',
                        stable_fresh_observations=self.stable_count,association=evidence)
                    self.previous_candidate=None;self.stable_count=0
        self.last_update=self.tracker.step(frame)
        if self.last_event:self.last_event['new_track_id']=self.last_update.active_track_id
        return self.last_update
