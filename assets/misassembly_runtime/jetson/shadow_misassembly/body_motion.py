"""Re-estimate current pose from image evidence on fixed, invariant body regions.

This is sparse feature tracking, not angle averaging or an old-pose fallback.
Every returned matrix requires current forward/backward image correspondences.
Classifier outputs, labels, filenames and intended engine angles are not inputs.
"""
import cv2
import numpy as np

from robustness import spatial_support


def transform(points, matrix):
    return cv2.transform(np.asarray(points,np.float32).reshape(-1,1,2),np.asarray(matrix,np.float64)).reshape(-1,2)


class BodyMotionEstimator:
    def __init__(self, config):
        self.config = config
        self.gray = None
        self.points = None
        self.canonical_points = None
        self.seed_matrix = None
        self.original = None

    @staticmethod
    def rejected(reason, **evidence):
        # No caller can accidentally classify with an old matrix after rejection.
        return dict(ok=False, reason=reason, matrix=None, **evidence)

    def seed(self, image, matrix):
        self.gray = self.points = self.canonical_points = self.seed_matrix = self.original = None
        matrix = np.asarray(matrix,dtype=np.float64)
        if matrix.shape != (2,3) or not np.isfinite(matrix).all() or np.linalg.det(matrix[:,:2]) <= 0:
            return self.rejected('INVALID_ANCHOR_MATRIX')
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        mask = np.zeros(gray.shape,np.uint8)
        for x1,y1,x2,y2 in self.config['fixed_body_feature_regions_xyxy']:
            polygon = transform([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],matrix)
            cv2.fillPoly(mask,[np.rint(polygon).astype(np.int32)],255)
        # Keep corner centers away from inspected-part boundaries. The regions
        # themselves are the TRAIN-frozen body geometry, identical for all classes.
        mask = cv2.erode(mask,np.ones((11,11),np.uint8))
        points = cv2.goodFeaturesToTrack(gray,400,.01,5,mask=mask,blockSize=7)
        minimum = self.config['registration']['min_good_matches']
        if points is None or len(points) < minimum:
            return self.rejected('ANCHOR_BODY_FEATURES_INSUFFICIENT')
        canonical = transform(points.reshape(-1,2),cv2.invertAffineTransform(matrix))
        support = spatial_support(canonical,np.zeros(len(canonical)),self.config['fixed_body_feature_regions_xyxy'])
        if not support['ok']:
            return self.rejected('ANCHOR_SPATIAL_SUPPORT_INSUFFICIENT',spatial_support=support)
        self.gray, self.points, self.canonical_points, self.seed_matrix = gray, points, canonical, matrix.copy()
        self.original = (gray.copy(), canonical.copy(), matrix.copy())
        return dict(ok=True,features=len(points),spatial_support=support)

    def estimate(self, image):
        if self.gray is None:
            return self.rejected('NO_VERIFIED_KEYFRAME')
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        if gray.shape != self.gray.shape:
            return self.rejected('FRAME_SIZE_CHANGED')
        settings = dict(winSize=(21,21),maxLevel=3,
                        criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
        current,forward_ok,_ = cv2.calcOpticalFlowPyrLK(self.gray,gray,self.points,None,**settings)
        if current is None or forward_ok is None:
            return self.rejected('BODY_FLOW_FORWARD_FAILED')
        backward,backward_ok,_ = cv2.calcOpticalFlowPyrLK(gray,self.gray,current,None,**settings)
        if backward is None or backward_ok is None:
            return self.rejected('BODY_FLOW_BACKWARD_FAILED')
        fb_error = np.linalg.norm(backward-self.points,axis=2).ravel()
        # One-pixel cycle error is a correspondence check, not a classifier score
        # threshold. The pose fit retains the frozen 3px registration radius.
        keep = (forward_ok.ravel()!=0)&(backward_ok.ravel()!=0)&np.isfinite(fb_error)&(fb_error<=1.)
        keep &= np.isfinite(current.reshape(-1,2)).all(axis=1)
        reference = self.canonical_points[keep]
        destination = current.reshape(-1,2)[keep]
        registration = self.config['registration']
        evidence = dict(features=len(self.points),forward_backward_kept=int(keep.sum()))
        if len(reference) < registration['min_good_matches']:
            return self.rejected('BODY_FLOW_TOO_FEW_MATCHES',**evidence)
        matrix,inlier_mask = cv2.estimateAffinePartial2D(reference,destination,method=cv2.RANSAC,
            ransacReprojThreshold=3.,maxIters=7000,confidence=.995,refineIters=20)
        if matrix is None or inlier_mask is None or not np.isfinite(matrix).all():
            return self.rejected('BODY_FLOW_AFFINE_FAILED',**evidence)
        # Refine against the original verified pixels, warped by the coarse
        # current estimate. This avoids both a large-rotation LK failure and
        # cumulative feature drift from repeatedly replacing the anchor image.
        original_gray, original_points, original_matrix = self.original
        relative = np.vstack([matrix,[0,0,1]]) @ np.linalg.inv(np.vstack([original_matrix,[0,0,1]]))
        warped = cv2.warpAffine(original_gray,relative[:2],(gray.shape[1],gray.shape[0]))
        predicted = transform(original_points,matrix)
        inside = ((predicted[:,0]>=12)&(predicted[:,0]<gray.shape[1]-12)
                  &(predicted[:,1]>=12)&(predicted[:,1]<gray.shape[0]-12))
        reference = original_points[inside]
        predicted = predicted[inside].reshape(-1,1,2)
        if len(predicted) < registration['min_good_matches']:
            return self.rejected('ORIGINAL_BODY_SUPPORT_OUT_OF_FRAME',**evidence)
        refined,forward_ok,_ = cv2.calcOpticalFlowPyrLK(warped,gray,predicted,None,**settings)
        if refined is None:
            return self.rejected('ORIGINAL_BODY_REFINEMENT_FAILED',**evidence)
        backward,backward_ok,_ = cv2.calcOpticalFlowPyrLK(gray,warped,refined,None,**settings)
        if backward is None:
            return self.rejected('ORIGINAL_BODY_REFINEMENT_FAILED',**evidence)
        fb_error = np.linalg.norm(backward-predicted,axis=2).ravel()
        keep = (forward_ok.ravel()!=0)&(backward_ok.ravel()!=0)&np.isfinite(fb_error)&(fb_error<=1.)
        keep &= np.isfinite(refined.reshape(-1,2)).all(axis=1)
        reference = reference[keep]
        destination = refined.reshape(-1,2)[keep]
        if len(reference) < registration['min_good_matches']:
            return self.rejected('ORIGINAL_BODY_TOO_FEW_MATCHES',**evidence)
        matrix,inlier_mask = cv2.estimateAffinePartial2D(reference,destination,method=cv2.RANSAC,
            ransacReprojThreshold=3.,maxIters=7000,confidence=.995,refineIters=20)
        if matrix is None or inlier_mask is None or not np.isfinite(matrix).all():
            return self.rejected('ORIGINAL_BODY_AFFINE_FAILED',**evidence)
        evidence['original_anchor_refinement'] = True
        evidence['forward_backward_kept'] = int(keep.sum())
        inliers = inlier_mask.ravel()!=0
        error = np.linalg.norm(transform(reference,matrix)-destination,axis=1)
        count = int(inliers.sum())
        median = float(np.median(error[inliers])) if count else float('inf')
        scale = float(np.hypot(matrix[0,0],matrix[1,0]))
        support = spatial_support(reference,error,self.config['fixed_body_feature_regions_xyxy'])
        evidence.update(inliers=count,inlier_ratio=count/len(reference),median_error_px=median,
                        spatial_support=support,reference_points=reference.tolist(),current_points=destination.tolist(),
                        reprojection_errors=error.tolist(),forward_backward_errors=fb_error[keep].tolist())
        if (count < registration['min_inliers'] or count/len(reference) < registration['min_inlier_ratio']
                or median > registration['max_median_reprojection_error_px']
                or not registration['min_scale'] <= scale <= registration['max_scale']):
            return self.rejected('BODY_FLOW_GEOMETRY_REJECTED',**evidence)
        if not support['ok']:
            return self.rejected('BODY_FLOW_SPATIAL_SUPPORT_INSUFFICIENT',**evidence)
        displacement = np.linalg.norm(destination-transform(reference,self.seed_matrix),axis=1)
        return dict(ok=True,reason='CURRENT_BODY_CORRESPONDENCES',matrix=matrix.tolist(),
                    angle_deg=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0]))),scale=scale,
                    motion_from_keyframe_p95_px=float(np.percentile(displacement[inliers],95)),**evidence)

    def advance_keyframe(self, image, measured):
        """Retain feature identities and their original canonical coordinates.

        Regenerating canonical coordinates from each fitted matrix would compound
        its fitting error. Only tracked inliers survive a keyframe advance.
        """
        keep = np.asarray(measured['reprojection_errors']) <= 3.
        reference = np.asarray(measured['reference_points'], np.float32)[keep]
        current = np.asarray(measured['current_points'], np.float32)[keep]
        support = spatial_support(reference, np.zeros(len(reference)), self.config['fixed_body_feature_regions_xyxy'])
        if len(reference) < self.config['registration']['min_good_matches'] or not support['ok']:
            return self.rejected('KEYFRAME_SUPPORT_INSUFFICIENT', spatial_support=support)
        self.gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.points = current.reshape(-1,1,2)
        self.canonical_points = reference
        self.seed_matrix = np.asarray(measured['matrix'], np.float64)
        return dict(ok=True, features=len(reference), spatial_support=support)
