"""Cold-start sequence anchor verified across multiple TRAIN body regions."""
import cv2
import numpy as np
from robust_preprocessing import ReciprocalMatcher,CachedFeatures
from robustness import spatial_support
from src.vision.engine_pose import _expanded_mask,transform_polygon
from src.vision.engine_rectification import rectify_image


def estimate_body_seed(processor,image,output):
    products=[p for p in output.get('products',[]) if p['confidence']>=processor.cfg['decision_policy']['product_confidence']]
    attempt=dict(ok=False,reason='SEED_SINGLE_PRODUCT_REQUIRED',matrix=None)
    if len(products)!=1:return attempt,None,{}
    box=[products[0]['bounding_box'][k] for k in ('x1','y1','x2','y2')]
    estimator=processor.estimator;orb,matcher=estimator.orb,estimator.matcher
    kp,des=orb.detectAndCompute(estimator._gray(image),_expanded_mask(image.shape,box,.18))
    if des is None:
        attempt['reason']='SEED_NO_BODY_DESCRIPTORS';return attempt,None,{}
    reciprocal=ReciprocalMatcher(matcher)
    estimator.orb=CachedFeatures(kp,des);estimator.matcher=reciprocal
    try:pose=estimator._estimate(image,box,bank=True)
    finally:estimator.orb,estimator.matcher=orb,matcher
    good=[pair[0] for pair in reciprocal.pairs if pair[0].distance<estimator.cfg['registration']['ratio_test']*pair[1].distance]
    unique={}
    for match in sorted(good,key=lambda m:m.distance):unique.setdefault(match.trainIdx,match)
    good=list(unique.values())
    src=np.float32([estimator.bank_points[m.queryIdx] for m in good]).reshape(-1,2)
    dst=np.float32([kp[m.trainIdx].pt for m in good]).reshape(-1,2)
    errors=np.linalg.norm(transform_polygon(src,pose.matrix)-dst,axis=1) if pose.matrix is not None and len(src) else np.full(len(src),1e9)
    support=spatial_support(src,errors,processor.cfg['fixed_body_feature_regions_xyxy'])
    attempt.update(reason=pose.reason,matrix=pose.matrix.tolist() if pose.matrix is not None else None,
        angle_deg=pose.angle_deg,scale=pose.scale,inliers=pose.inliers,good_matches=pose.good_matches,
        median_error_px=pose.median_error_px,diagnostics=pose.diagnostics,spatial_support=support,
        reference_points=src.tolist(),current_points=dst.tolist(),reprojection_errors=errors.tolist())
    if not pose.ok:return attempt,None,{}
    if not support['ok']:
        attempt['reason']='SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT';return attempt,None,{}
    canonical=rectify_image(image,pose.matrix,processor.cfg)
    score=processor.check_direction(canonical);attempt['orientation_anchor_correlation']=score
    if not np.isfinite(score) or score<processor.cfg['min_orientation_anchor_correlation']:
        attempt['reason']='SEED_BODY_DIRECTION_NOT_VERIFIED';return attempt,canonical,{}
    crop_record,canonical,crops=processor.extract(image,canonical,pose.matrix,{})
    attempt['crop_evidence']=crop_record
    if crop_record['status']!='VALID':
        attempt['reason']='SEED_ESSENTIAL_REGION_NOT_VERIFIED';return attempt,canonical,crops
    attempt.update(ok=True,reason='MULTI_REGION_RECIPROCAL_BODY_SEED')
    return attempt,canonical,crops
