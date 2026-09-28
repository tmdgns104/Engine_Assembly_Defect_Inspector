"""자동 요청의 실제 후속 프레임 검증과 보정 기준의 제품 상대 좌표 변환."""
from copy import deepcopy
import math
from src.decision.slots import assign_slots


def box_values(box):
    return [box[k] for k in ('x1','y1','x2','y2')]


def validate_bound_frame(previous, packet, profile):
    for key in ('camera_epoch','package_sha256'):
        if key in previous and packet.get(key) != previous[key]:
            raise ValueError('AUTO_FRAME_CONTEXT_MISMATCH: '+key)
    if not packet['integrity']['valid'] or packet['provider']['status'] != 'PRODUCT_OBSERVED':
        raise ValueError('AUTO_PRODUCT_FRAME_UNAVAILABLE')
    bbox = box_values(packet['provider']['observations'][0]['bbox'])
    elapsed = packet['monotonic_s']-previous['monotonic_s']
    if packet['sequence'] <= previous['sequence'] or not 0 < elapsed <= profile['max_unobserved_seconds']:
        raise ValueError('AUTO_PRODUCT_FRAME_GAP_OR_REPLAY')
    center = [(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2]
    old = [(previous['bbox'][0]+previous['bbox'][2])/2,(previous['bbox'][1]+previous['bbox'][3])/2]
    limit = profile['max_center_step_norm']+profile['max_center_speed_norm_s']*elapsed
    if math.dist(center,old) > limit or center[1]-old[1] < -profile['max_reverse_step_norm']:
        raise ValueError('AUTO_PRODUCT_ASSOCIATION_INVALID')
    x1,y1,x2,y2 = profile['inspection_window']
    if not x1 <= center[0] <= x2 or not y1 <= center[1] <= y2:
        raise ValueError('AUTO_PRODUCT_LEFT_INSPECTION_WINDOW')
    return dict(previous,sequence=packet['sequence'],monotonic_s=packet['monotonic_s'],bbox=bbox)


def automatic_coverage(observation, package, calibration, bbox, profile):
    """검출이 충분한 슬롯만 PRESENT 판정 가능. 누락과 가림의 구분 불가는 REVIEW다."""
    if not calibration or calibration.get('confirmed') is not True:
        raise ValueError('AUTO_CONFIRMED_REFERENCE_REQUIRED')
    reference = calibration['reference_box']
    rw,rh = reference[2]-reference[0], reference[3]-reference[1]
    bw,bh = bbox[2]-bbox[0], bbox[3]-bbox[1]
    if min(rw,rh,bw,bh) <= 0:
        raise ValueError('AUTO_REFERENCE_GEOMETRY_INVALID')
    ratio = (bw/bh)/(rw/rh)
    low,high = profile['reference_scale_range']
    aligned = low <= bw/rw <= high and low <= bh/rh <= high and abs(ratio-1) <= profile['reference_aspect_tolerance']
    regions = {}
    for key,region in calibration['slots'].items():
        transformed = [bbox[0]+(region[0]-reference[0])*bw/rw,
                       bbox[1]+(region[1]-reference[1])*bh/rh,
                       bbox[0]+(region[2]-reference[0])*bw/rw,
                       bbox[1]+(region[3]-reference[1])*bh/rh]
        aligned = aligned and all(0 <= v <= 1 for v in transformed)
        regions[key] = transformed
    assignments,uncertain = assign_slots(observation['detections'],package.recipe,observation['width'],observation['height'],regions)
    visibility = {slot['id']: aligned and slot['id'] not in uncertain and
                  len(assignments[slot['id']]) == slot['expected_count'] for slot in package.recipe['slots']}
    projected = deepcopy(calibration)
    projected.update(slots=regions,reference_box=bbox)
    return {'source':'CALIBRATED_CARRIER_POSITIVE_SLOT_EVIDENCE','alignment_confirmed':aligned,
            'product_identity':'package_carrier_observed','visible_slots':visibility,
            'calibration':projected,'limitation':'미검출 슬롯의 누락/가림 자동 구분은 미검증; REVIEW 유지'}
