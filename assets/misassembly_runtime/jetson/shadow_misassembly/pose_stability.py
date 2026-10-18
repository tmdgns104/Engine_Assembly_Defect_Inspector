"""Sequence-only pose consistency; independent still images have no temporal state.

The absolute seed supplies canonical identity. Subsequent matrices are fitted to
current body pixels. A rejected observation never returns the previous matrix.
"""
from dataclasses import dataclass
import numpy as np

from body_motion import BodyMotionEstimator, transform


@dataclass(frozen=True)
class FrameContext:
    frame_id: str
    source_pts_ns: int
    track_id: int
    camera_epoch: str
    quality_valid: bool
    tracking_continuity_verified: bool = False


class TemporalPoseGuard:
    version = 'shadow-current-body-motion-v1'

    def __init__(self, config):
        self.config = config
        self.motion = BodyMotionEstimator(config)
        self.last = None
        self.has_seed = False
        self.last_matrix = None

    def reset(self):
        self.motion = BodyMotionEstimator(self.config)
        self.has_seed = False
        self.last = None
        self.last_matrix = None

    def reject(self, reason, **evidence):
        self.has_seed = False
        return dict(ok=False, reason=reason, matrix=None, **evidence)

    def requires_seed(self, context):
        return (not self.has_seed or self.last is None
                or context.track_id != self.last.track_id
                or context.camera_epoch != self.last.camera_epoch
                or (context.source_pts_ns-self.last.source_pts_ns > 2_000_000_000
                    and not context.tracking_continuity_verified))

    def choose(self, image, absolute, context):
        if self.last is not None:
            same_sequence = (context.track_id == self.last.track_id
                             and context.camera_epoch == self.last.camera_epoch)
            if not same_sequence:
                self.reset()
            elif (context.frame_id == self.last.frame_id
                  or context.source_pts_ns <= self.last.source_pts_ns):
                return self.reject('DUPLICATE_OR_NONMONOTONIC_FRAME')
            elif (context.source_pts_ns - self.last.source_pts_ns > 2_000_000_000
                  and not context.tracking_continuity_verified):
                self.reset()
        self.last = context
        if not context.quality_valid:
            return self.reject('CURRENT_FRAME_QUALITY_INVALID')
        pose = absolute.get('pose') or {}
        if not self.has_seed:
            if absolute.get('status') != 'VALID' or not pose.get('ok') or pose.get('matrix') is None:
                return self.reject('ABSOLUTE_SEED_REQUIRED')
            seeded = self.motion.seed(image, pose['matrix'])
            if not seeded['ok']:
                return self.reject(seeded['reason'], seed_evidence=seeded)
            self.has_seed = True
            self.last_matrix = np.asarray(pose['matrix'],np.float64)
            return dict(ok=True, reason='VERIFIED_ABSOLUTE_SEED', route='ABSOLUTE_SEED',
                        matrix=pose['matrix'], seed_evidence=seeded)

        measured = self.motion.estimate(image)
        if not measured['ok']:
            return self.reject(measured['reason'], motion_evidence=measured)
        matrix = np.asarray(measured['matrix'])
        # Compare both estimates at the same body points; no class score decides
        # the selected geometry. The tolerance is the frozen pose residual bound.
        points = np.asarray(measured['reference_points'])
        consistency = dict(available=False, disagrees=None)
        if pose.get('ok') and pose.get('matrix') is not None:
            errors = np.linalg.norm(transform(points, matrix)-transform(points, pose['matrix']), axis=1)
            consistency = dict(available=True, median_disagreement_px=float(np.median(errors)),
                               max_disagreement_px=float(errors.max()),
                               disagrees=bool(np.median(errors) > self.config['registration']['max_median_reprojection_error_px']))
        relative = matrix[:,:2] @ np.linalg.inv(self.motion.seed_matrix[:,:2])
        rotation = float(np.degrees(np.arctan2(relative[1,0],relative[0,0])))
        refresh = abs(rotation) >= 10. or measured['motion_from_keyframe_p95_px'] >= 40.
        result = dict(ok=True, reason='CURRENT_BODY_CORRESPONDENCES', route='CURRENT_BODY_REESTIMATE',
                      matrix=matrix.tolist(), motion_evidence=measured,
                      absolute_consistency=consistency, keyframe_refreshed=False)
        if self.last_matrix is not None:
            displacement=np.linalg.norm(transform(points,matrix)-transform(points,self.last_matrix),axis=1)
            result['previous_pose_consistency']=dict(median_current_body_motion_px=float(np.median(displacement)),
                p95_current_body_motion_px=float(np.percentile(displacement,95)),
                interpretation='Measured motion, not an angle-clamping acceptance threshold')
        if refresh:
            # Refresh from the newly measured geometry, never the classifier or
            # a smoothed angle. This keeps LK within its local-motion basin.
            seeded = self.motion.advance_keyframe(image, measured)
            if not seeded['ok']:
                return self.reject(seeded['reason'], seed_evidence=seeded)
            result.update(keyframe_refreshed=True, seed_evidence=seeded)
        self.last_matrix=matrix.copy()
        return result
