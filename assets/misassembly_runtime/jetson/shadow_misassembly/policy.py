"""Pure shadow-only semantics. No PLC, production decision or actuator imports."""
import math

PARTS=('pipe_left','pipe_right','exhaust','symbol')
DEFECTS={'MISSING','UPWARD_ROTATED','OUTWARD_SPLAYED','REVERSED','SIDEWAYS','UPSIDE_DOWN'}


def aggregate_frame(record):
    if record.get('error'):return 'ERROR'
    if record['preprocessing']['status']!='VALID':return 'REVIEW'
    parts=record.get('parts',{})
    if set(parts)!=set(PARTS) or any(not p.get('valid') for p in parts.values()):return 'REVIEW'
    if record.get('quality_review_reasons'):return 'REVIEW'
    states=[p.get('predicted_state') for p in parts.values()]
    if any(s not in DEFECTS|{'CORRECT'} for s in states):return 'ERROR'
    for part in parts.values():
        scores=part.get('class_scores')
        if not scores or not all(math.isfinite(v) and 0<=v<=1 for v in scores.values()):return 'ERROR'
    return 'FAIL_CANDIDATE' if any(s in DEFECTS for s in states) else 'PASS_CANDIDATE'


def compare_case(pc,jetson):
    reasons=[];visual=[]
    if pc['raw_sha256']!=jetson['raw_sha256']:reasons.append('RAW_HASH_MISMATCH')
    if pc['preprocessing']['status']!=jetson['preprocessing']['status']:reasons.append('PREPROCESSING_STATUS_MISMATCH')
    if aggregate_frame(pc)!=aggregate_frame(jetson):reasons.append('SHADOW_STATE_MISMATCH')
    a=pc['preprocessing'].get('pose',{}).get('angle_deg')
    b=jetson['preprocessing'].get('pose',{}).get('angle_deg')
    if a is not None and b is not None and abs((a-b+180)%360-180)>90:reasons.append('BODY_DIRECTION_MISMATCH')
    for name in PARTS:
        first=pc['parts'].get(name,{});second=jetson['parts'].get(name,{})
        for key in ['valid','predicted_state','class_mapping']:
            if first.get(key)!=second.get(key):reasons.append(name+':'+key.upper()+'_MISMATCH')
        if first.get('crop_sha256')!=second.get('crop_sha256'):visual.append(name+':CROP_BYTES_DIFFER')
    return dict(status='FAIL' if reasons else 'NEEDS_VISUAL_REVIEW' if visual else 'PASS',reasons=reasons,visual_review=visual)
