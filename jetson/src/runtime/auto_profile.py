"""제품 프로파일을 패키지 계약에 묶는다. AUTO 필수 설정의 암묵적 기본값은 없다."""
import math
from src.tracking.contracts import InspectionWindow, SingleActiveTrackerConfig


def validate_profile(profile, package):
    if profile['schema_version'] != 1 or profile['package_sha256'] != package.manifest_hash:
        raise ValueError('AUTO_PROFILE_PACKAGE_MISMATCH')
    if not isinstance(profile['product_unit'],str) or not profile['product_unit'].strip():
        raise ValueError('AUTO_PRODUCT_UNIT_REQUIRED')
    if profile['carrier_class'] != package.recipe['reference_class']:
        raise ValueError('AUTO_CARRIER_REQUIRES_PACKAGE_REFERENCE_CLASS')
    required = {c for slot in package.recipe['slots'] for c in slot['allowed_classes']}
    if profile['carrier_class'] in required:
        raise ValueError('AUTO_CARRIER_MUST_BE_INDEPENDENT_OF_REQUIRED_PARTS')
    if not package.recipe.get('reference_class') or profile['carrier_confidence'] < package.recipe['reference_confidence']:
        raise ValueError('AUTO_CARRIER_CONFIDENCE_CONTRACT')
    for key in ('max_center_step_norm','max_center_speed_norm_s','max_reverse_step_norm',
                'max_unobserved_seconds','max_frame_gap','empty_seconds','initial_empty_seconds',
                'reference_aspect_tolerance','observation_stale_seconds'):
        if type(profile[key]) not in (int,float) or not math.isfinite(profile[key]) or profile[key] <= 0:
            raise ValueError('AUTO_PROFILE_INVALID: '+key)
    for key in ('empty_frames','consecutive_error_limit','recovery_attempt_limit'):
        if type(profile[key]) is not int or profile[key] < 1:
            raise ValueError('AUTO_PROFILE_INVALID: '+key)
    if profile['empty_frames'] < 2:
        raise ValueError('AUTO_EXIT_REQUIRES_MULTIPLE_FRAMES')
    window = InspectionWindow(*profile['inspection_window'])
    if not 0 < profile['entry_y'] < window.y1 < window.y2 < profile['exit_y'] < 1:
        raise ValueError('AUTO_ZONE_ORDER_INVALID')
    low,high = profile['reference_scale_range']
    if not 0 < low <= 1 <= high:
        raise ValueError('AUTO_REFERENCE_SCALE_INVALID')
    return SingleActiveTrackerConfig(window,'y',1,profile['max_center_step_norm'],
        profile['max_reverse_step_norm'],2,1,profile['max_center_speed_norm_s'],
        profile['max_unobserved_seconds'],True)
