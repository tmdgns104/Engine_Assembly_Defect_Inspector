from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
import hashlib
import json, math
import cv2
import numpy as np

@dataclass(frozen=True)
class PoseResult:
    ok: bool
    reason: str
    matrix: np.ndarray | None = None
    angle_deg: float | None = None
    scale: float | None = None
    inliers: int = 0
    good_matches: int = 0
    median_error_px: float | None = None
    diagnostics: dict | None = None


def _xyxy(det: dict) -> list[float]:
    b=det.get('bounding_box',det.get('bbox'))
    if isinstance(b,dict):return [float(b['x1']),float(b['y1']),float(b['x2']),float(b['y2'])]
    if isinstance(b,(list,tuple)) and len(b)==4:return [float(x) for x in b]
    raise ValueError('Detection requires bounding_box{x1,y1,x2,y2} or bbox[4].')

def _poly(box):
    x1,y1,x2,y2=box
    return np.asarray([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],np.float32)

def transform_polygon(poly, matrix):
    return cv2.transform(np.asarray(poly,np.float32).reshape(-1,1,2),np.asarray(matrix,np.float32)).reshape(-1,2)

def _expanded_mask(shape,box,margin=0.15):
    h,w=shape[:2];x1,y1,x2,y2=box;bw=x2-x1;bh=y2-y1
    x1=max(0,int(x1-bw*margin));y1=max(0,int(y1-bh*margin));x2=min(w,int(x2+bw*margin));y2=min(h,int(y2+bh*margin))
    m=np.zeros((h,w),np.uint8);cv2.rectangle(m,(x1,y1),(x2,y2),255,-1);return m

class EnginePoseEstimator:
    def __init__(self, reference_json: str|Path, *, enhanced=False):
        self.path=Path(reference_json);self.cfg=json.loads(self.path.read_text(encoding='utf-8'))
        fallback=self.cfg['registration'].get('fallback')
        if enhanced:self.cfg['registration'].update(fallback)
        self.fallback=EnginePoseEstimator(reference_json,enhanced=True) if fallback and not enhanced else None
        self.bank_points=self.bank_des=None
        bank=self.cfg.get('reference_bank')
        if bank:
            bank_path=(self.path.parent/bank['path']).resolve()
            if not bank_path.is_relative_to(self.path.parent.resolve()) or hashlib.sha256(bank_path.read_bytes()).hexdigest()!=bank['sha256']:
                raise ValueError('POSE_REFERENCE_BANK_HASH_MISMATCH')
            with np.load(bank_path,allow_pickle=False) as data:
                self.bank_points=data['points'].copy();self.bank_des=data['descriptors'].copy()
            if self.bank_des.dtype!=np.uint8 or self.bank_des.ndim!=2 or self.bank_des.shape[1]!=32 or not 10<=len(self.bank_des)<=50000 or self.bank_points.shape!=(len(self.bank_des),2) or not np.isfinite(self.bank_points).all():
                raise ValueError('POSE_REFERENCE_BANK_INVALID')
        self.reference=cv2.imread(str(self.path.parent/self.cfg['reference_image']))
        if self.reference is None:raise FileNotFoundError(self.cfg['reference_image'])
        r=self.cfg['registration'];self.orb=cv2.ORB_create(nfeatures=r['orb_nfeatures'],scaleFactor=1.2,nlevels=r.get('orb_nlevels',8),edgeThreshold=15,fastThreshold=r.get('orb_fast_threshold',10))
        self.matcher=cv2.BFMatcher(cv2.NORM_HAMMING)
        gray=self._gray(self.reference)
        self.ref_kp,self.ref_des=self.orb.detectAndCompute(gray,_expanded_mask(self.reference.shape,self.cfg['canonical_product_box_xyxy'],.08))
        if self.ref_des is None:raise RuntimeError('Reference ORB descriptors missing.')

    def _gray(self,image):
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        if self.cfg['registration'].get('contrast_normalization')=='clahe':
            gray=cv2.createCLAHE(2.,(8,8)).apply(gray)
        return gray

    def estimate(self, frame: np.ndarray, product_box: list[float]) -> PoseResult:
        baseline=self._estimate(frame,product_box)
        def selected(value, attempts):
            return replace(value,diagnostics={**(value.diagnostics or {}),
                'attempts':[attempt.diagnostics for attempt in attempts]})
        if not baseline.ok and self.bank_des is not None:
            alternative=self._estimate(frame,product_box,bank=True)
            if alternative.ok:
                return selected(replace(alternative,reason='ORB_TRAIN_REFERENCE_BANK'),[baseline,alternative])
            return selected(alternative if alternative.inliers>baseline.inliers else baseline,[baseline,alternative])
        if baseline.ok or self.fallback is None:return selected(baseline,[baseline])
        alternative=self.fallback._estimate(frame,product_box)
        if alternative.ok:
            return selected(replace(alternative,reason='ORB_CLAHE_FALLBACK'),[baseline,alternative])
        return selected(alternative if alternative.inliers>baseline.inliers else baseline,[baseline,alternative])

    def _estimate(self, frame: np.ndarray, product_box: list[float], *, bank=False) -> PoseResult:
        r=self.cfg['registration']
        diagnostics=dict(reference='train_reference_bank' if bank else self.cfg['reference_image'],
            reference_sha256=self.cfg.get('reference_bank',{}).get('sha256') if bank else self.cfg.get('reference_image_sha256'),
            configuration_sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
            product_box=product_box,roi=None,ratio_test=r['ratio_test'],
            thresholds={k:r[k] for k in ('min_good_matches','min_inliers','min_inlier_ratio','max_median_reprojection_error_px','min_scale','max_scale')},
            raw_match_pairs=None,lowe_matches=None,unique_correspondences=None,used_correspondences=None,
            inlier_ratio=None,inliers=None,reprojection_error_px=None,angle_deg=None,scale=None,translation=None,
            inlier_reference_hull_area=None,inlier_current_hull_area=None,failed_conditions=[],evaluation='NOT_EVALUATED')
        def rejected(reason, **values):
            diagnostics['failed_conditions']=[reason]
            return PoseResult(False,reason,diagnostics=diagnostics,**values)
        if not isinstance(frame,np.ndarray) or frame.ndim!=3 or frame.shape[2]!=3 or not frame.size:
            return rejected('POSE_INVALID_FRAME')
        if len(product_box)!=4 or not np.isfinite(product_box).all() or product_box[2]<=product_box[0] or product_box[3]<=product_box[1]:
            return rejected('POSE_INVALID_PRODUCT_BOX')
        r=self.cfg['registration'];gray=self._gray(frame)
        roi_mask=_expanded_mask(frame.shape,product_box,.18)
        rx,ry,rw,rh=cv2.boundingRect(roi_mask)
        diagnostics['roi']=[rx,ry,rx+rw,ry+rh]
        kp,des=self.orb.detectAndCompute(gray,roi_mask)
        if des is None:return rejected('POSE_NO_FEATURES')
        pairs=self.matcher.knnMatch(self.bank_des if bank else self.ref_des,des,k=2)
        good=[pair[0] for pair in pairs if len(pair)==2 and pair[0].distance < r['ratio_test']*pair[1].distance]
        diagnostics.update(raw_match_pairs=len(pairs),lowe_matches=len(good),unique_correspondences=len({m.trainIdx for m in good}))
        if bank:
            # Multiple reference views cannot inflate the inlier count by voting
            # repeatedly for one current keypoint.
            unique={}
            for match in sorted(good,key=lambda match:match.distance):unique.setdefault(match.trainIdx,match)
            good=list(unique.values())
        diagnostics['used_correspondences']=len(good)
        if len(good)<r['min_good_matches']:return rejected('POSE_TOO_FEW_MATCHES',good_matches=len(good))
        src=np.float32([self.bank_points[m.queryIdx] if bank else self.ref_kp[m.queryIdx].pt for m in good]).reshape(-1,1,2)
        dst=np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1,1,2)
        M,inlier_mask=cv2.estimateAffinePartial2D(src,dst,method=cv2.RANSAC,ransacReprojThreshold=3.0,maxIters=7000,confidence=.995,refineIters=20)
        if M is None or not np.isfinite(M).all():return rejected('POSE_AFFINE_FAILED',good_matches=len(good))
        if inlier_mask is None:return rejected('POSE_NO_INLIERS',good_matches=len(good))
        mask=inlier_mask.reshape(-1).astype(bool);inliers=int(mask.sum());ratio=inliers/max(1,len(good))
        if not inliers:return rejected('POSE_NO_INLIERS',matrix=M,good_matches=len(good))
        pred=cv2.transform(src,M);err=np.linalg.norm(pred-dst,axis=2).reshape(-1);med=float(np.median(err[mask])) if inliers else math.inf
        scale=float(math.hypot(M[0,0],M[1,0]));angle=float(math.degrees(math.atan2(M[1,0],M[0,0])))
        failed=[]
        for condition,failed_gate in [('INLIER_COUNT',inliers<r['min_inliers']),('INLIER_RATIO',ratio<r['min_inlier_ratio']),
                ('REPROJECTION_ERROR',med>r['max_median_reprojection_error_px']),('SCALE_RANGE',not r['min_scale']<=scale<=r['max_scale'])]:
            if failed_gate:failed.append(condition)
        diagnostics.update(inlier_ratio=ratio,inliers=inliers,reprojection_error_px=med,angle_deg=angle,scale=scale,
            translation=M[:,2].tolist(),failed_conditions=failed,evaluation='EVALUATED',
            inlier_reference_hull_area=float(cv2.contourArea(cv2.convexHull(src[mask]))),
            inlier_current_hull_area=float(cv2.contourArea(cv2.convexHull(dst[mask]))))
        return PoseResult(not failed,'POSE_QUALITY_REJECTED' if failed else 'OK',M,angle,scale,inliers,len(good),med,diagnostics)

    def current_slots(self, pose: PoseResult) -> dict[str,np.ndarray]:
        if not pose.ok or pose.matrix is None:raise ValueError('Verified pose required.')
        polygons = self.cfg.get('slot_polygons')
        if polygons:
            return {name:transform_polygon(poly,pose.matrix) for name,poly in polygons.items()}
        return {name:transform_polygon(_poly(box),pose.matrix) for name,box in self.cfg['slot_center_regions_xyxy'].items()}

    def visibility_slots(self,pose:PoseResult) -> dict[str,np.ndarray]:
        """D001 physical part extents; search tolerance must not enlarge visibility claims."""
        polygons=self.cfg.get('visibility_polygons')
        if not polygons:return self.current_slots(pose)
        return {name:transform_polygon(poly,pose.matrix) for name,poly in polygons.items()}

