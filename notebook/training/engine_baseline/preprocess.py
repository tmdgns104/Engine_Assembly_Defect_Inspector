"""Image-only body registration and fixed-slot extraction for the local baseline.

No label, filename, capture order, guide ROI, or target angle enters this path.
Existing runtime ORB/RANSAC and inverse-affine rectification are imported unchanged.
"""
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(PROJECT / 'jetson'))
from src.vision.engine_pose import EnginePoseEstimator, transform_polygon
from src.vision.engine_rectification import rectify_image

PARTS = ('pipe_left','pipe_right','exhaust','symbol')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_image(path):
    image = cv2.imdecode(np.frombuffer(Path(path).read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('IMAGE_DECODE_FAILED')
    return image


def write_image(path,image):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    ok, encoded = cv2.imencode('.png',image)
    if not ok:
        raise ValueError('IMAGE_ENCODE_FAILED')
    path.write_bytes(encoded.tobytes())
    return sha(path)


def padded_224(image):
    """BGR uint8 -> symmetric square pad(40) -> 224px bilinear, no cropping."""
    h,w = image.shape[:2]
    side = max(h,w)
    top,left = (side-h)//2,(side-w)//2
    square = cv2.copyMakeBorder(image,top,side-h-top,left,side-w-left,cv2.BORDER_CONSTANT,value=(40,40,40))
    return cv2.resize(square,(224,224),interpolation=cv2.INTER_LINEAR)


def normalized_correlation(first,second):
    a,b=first.astype(np.float32).ravel(),second.astype(np.float32).ravel()
    a-=a.mean();b-=b.mean()
    return float(np.dot(a,b)/max(float(np.linalg.norm(a)*np.linalg.norm(b)),1e-8))


class BodyPreprocessor:
    def __init__(self, config_path):
        self.path = Path(config_path)
        self.cfg = json.loads(self.path.read_text(encoding='utf-8'))
        self.estimator = EnginePoseEstimator(self.path)
        reference = self.estimator.reference
        mask = np.zeros(reference.shape[:2],np.uint8)
        for x1,y1,x2,y2 in self.cfg['fixed_body_feature_regions_xyxy']:
            mask[y1:y2,x1:x2]=255
        points, descriptors = self.estimator.orb.detectAndCompute(self.estimator._gray(reference),mask)
        # Keep descriptor support inside invariant areas, away from inspected parts.
        distance = cv2.distanceTransform(mask,cv2.DIST_L2,5)
        keep = [i for i,kp in enumerate(points) if distance[round(kp.pt[1]),round(kp.pt[0])] >= kp.size*.5]
        if len(keep)<12:
            raise ValueError(f'TOO_FEW_FIXED_BODY_FEATURES: {len(keep)}')
        self.estimator.ref_kp = [points[i] for i in keep]
        self.estimator.ref_des = descriptors[keep]
        self.reference_mask = mask
        settings = self.cfg['envelope_detector']
        from ultralytics import YOLO
        assert sha(PROJECT / settings['path']) == settings['sha256']
        # The runtime wrapper's bound diagnostics hook cannot be deep-copied by
        # installed Ultralytics 8.4.146. Use its same weights/contract locally.
        self.detector = YOLO(str(PROJECT / settings['path'])).to('cuda:0')
        assert self.detector.names == {0:'product_envelope'}
        self.reference_gray = cv2.cvtColor(reference,cv2.COLOR_BGR2GRAY)

    def process(self, image):
        """Return an auditable transform and crops; every rejection remains explicit."""
        h,w = image.shape[:2]
        prediction = self.detector.predict(image,imgsz=[640,640],rect=False,device=0,quantize=32,
                                           conf=.25,iou=.45,augment=False,verbose=False)[0]
        detected = [dict(class_name='product_envelope',confidence=float(conf),
                         bounding_box=dict(zip(('x1','y1','x2','y2'),map(float,box))))
                    for box,conf in zip(prediction.boxes.xyxy.cpu().numpy(),prediction.boxes.conf.cpu().numpy())]
        products = [d for d in detected if d['confidence']>=self.cfg['decision_policy']['product_confidence']]
        output = dict(status='FAILED',reason=None,products=detected,parts={})
        if len(products)!=1:
            output['reason']='PRODUCT_COUNT_NOT_ONE'
            return output, None, {}
        box=products[0]['bounding_box']
        bbox=[box[k] for k in ('x1','y1','x2','y2')]
        pose=self.estimator.estimate(image,bbox)
        output['pose']=dict(ok=pose.ok,reason=pose.reason,matrix=pose.matrix.tolist() if pose.matrix is not None else None,
                           angle_deg=pose.angle_deg,scale=pose.scale,inliers=pose.inliers,
                           good_matches=pose.good_matches,median_error_px=pose.median_error_px,diagnostics=pose.diagnostics)
        if not pose.ok:
            output['reason']='BODY_ALIGNMENT_' + pose.reason
            return output,None,{}
        canonical=rectify_image(image,pose.matrix,self.cfg)
        gray=cv2.cvtColor(canonical,cv2.COLOR_BGR2GRAY)
        x1,y1,x2,y2=self.cfg['orientation_anchor_xyxy']
        correlation=normalized_correlation(self.reference_gray[y1:y2,x1:x2],gray[y1:y2,x1:x2])
        output['orientation_anchor_correlation']=correlation
        if correlation<self.cfg['min_orientation_anchor_correlation']:
            output['reason']='BODY_DIRECTION_NOT_VERIFIED'
            return output,canonical,{}
        # Verify support in the original frame; warp borders cannot masquerade as missing parts.
        coverage=cv2.warpAffine(np.ones((h,w),np.uint8),cv2.invertAffineTransform(pose.matrix),
                               (self.cfg['frame_width'],self.cfg['frame_height']),flags=cv2.INTER_NEAREST)
        crops={}
        for part,(x1,y1,x2,y2) in self.cfg['crop_regions_xyxy'].items():
            region=canonical[y1:y2,x1:x2]
            polygon=transform_polygon([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],pose.matrix)
            support=float(coverage[y1:y2,x1:x2].mean())
            reason='CROP_OUT_OF_SOURCE_FRAME' if support<.999 else 'EMPTY_OR_FLAT_CROP' if region.size==0 or float(region.std())<4 else None
            output['parts'][part]=dict(status='FAILED' if reason else 'VALID',reason=reason,
                                      source_polygon=polygon.tolist(),source_coverage=support,canonical_xyxy=[x1,y1,x2,y2])
            if reason is None:
                crops[part]=padded_224(region)
        output['status']='VALID' if len(crops)==4 else 'PARTIAL'
        output['reason']=None if len(crops)==4 else 'ONE_OR_MORE_CROPS_FAILED'
        return output,canonical,crops
