"""설정 검증과 시작 시점 사본. 장비 제어·운전 중 reload는 수행하지 않는다."""
import copy
import hashlib
import json
import math
from src import config


def validate_settings(values=config):
    """입력 허용 범위 검사이며 해당 범위의 실물 성능 보증은 아니다."""
    text_names = {'ENGINE_PARTS_PACKAGE', 'ENGINE_ENVELOPE_PACKAGE',
                  'ENGINE_POSE_REFERENCE', 'ENGINE_POSE_REFERENCE_SHA256'}
    tuple_names = {'MODEL_INPUT_SIZE', 'POSE_CLAHE_GRID'}
    for name, value in vars(values).items():
        if not name.isupper():
            continue
        if name in text_names:
            if type(value) is not str or not value.strip():
                raise ValueError('INVALID_TEXT_SETTING:'+name)
            continue
        if name in tuple_names:
            if type(value) is not tuple or len(value) != 2 or any(type(v) is not int or v < 1 for v in value):
                raise ValueError('INVALID_DIMENSIONS_SETTING:'+name)
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('INVALID_SETTING:'+name)
    probabilities = ('DETECTOR_CONFIDENCE', 'DETECTOR_NMS_IOU', 'PYTORCH_DEFAULT_NMS_IOU',
        'ENGINE_PRODUCT_CONFIDENCE', 'ENGINE_PART_CONFIDENCE', 'ENGINE_SLOT_OVERLAP',
        'POSE_RATIO_TEST', 'POSE_MIN_INLIER_RATIO', 'MOTION_FRACTION_LIMIT')
    for name in probabilities:
        value=getattr(values,name)
        if type(value) not in (int,float) or not 0 < value <= 1:
            raise ValueError('INVALID_SETTING:'+name)
    integers=('MOTION_COMPARISON_WIDTH','MOTION_COMPARISON_HEIGHT','POSE_ORB_FEATURES',
        'POSE_MIN_MATCHES','POSE_MIN_INLIERS','POSE_ORB_LEVELS','POSE_ORB_EDGE_THRESHOLD',
        'POSE_ORB_FAST_THRESHOLD','JOURNAL_MIN_FREE_BYTES','JOURNAL_OUTBOX_LIMIT',
        'HISTORY_DEFAULT_LIMIT','HISTORY_MAX_PAGE_SIZE','HISTORY_EXPORT_LIMIT',
        'HEALTH_DIAGNOSTIC_LIMIT','CONSUMED_FRAME_LIMIT','DIAGNOSTIC_QUEUE_ITEMS',
        'RUN_CAPTURE_FRAMES','RUN_CAPTURE_BYTES','TRACK_MAX_MISSED_FRAMES','TRACK_CLEAR_FRAMES',
        'TRACK_ZONE_ENTRY_FRAMES','IPC_SENT_CACHE_LIMIT','PRODUCT_OBSERVATION_QUEUE_SIZE',
        'PREVIEW_RATE_SAMPLE_COUNT','JOURNAL_RECENT_LIMIT','FIELD_RAW_QUEUE_SIZE',
        'FIELD_RAW_ENCODER_WORKERS','DIAGNOSTIC_TRACE_RECORDS','DIAGNOSTIC_DEFAULT_FRAMES',
        'DIAGNOSTIC_RESERVE_BYTES','DIAGNOSTIC_MAX_BUFFER_BYTES','DIAGNOSTIC_DEFAULT_BYTES',
        'RUN_CAPTURE_MEMORY_RESERVE','RUN_CAPTURE_SCRATCH_BYTES','RUN_CAPTURE_BOOKKEEPING_BYTES',
        'RUN_CAPTURE_MAX_IMAGE_BYTES','LINE_MIN_FREE_BYTES','PREVIEW_JPEG_QUALITY',
        'RUNTIME_LOG_MAX_BYTES','RUNTIME_LOG_BACKUPS','AREA_CLEAR_FRAMES')
    for name in integers:
        if type(getattr(values,name)) is not int or getattr(values,name)<1:
            raise ValueError('POSITIVE_INTEGER_SETTING_REQUIRED:'+name)
    if not 0 <= values.MIN_MEAN_BRIGHTNESS < values.MAX_MEAN_BRIGHTNESS <= 255:
        raise ValueError('INVALID_BRIGHTNESS_RANGE')
    if not 0 < values.POSE_MIN_SCALE < values.POSE_MAX_SCALE:
        raise ValueError('INVALID_POSE_SCALE_RANGE')
    if values.HISTORY_DEFAULT_LIMIT > values.HISTORY_MAX_PAGE_SIZE or values.HISTORY_MAX_PAGE_SIZE > 1000 or values.HISTORY_EXPORT_LIMIT > 10000:
        raise ValueError('BOUNDED_HISTORY_LIMIT_REQUIRED')
    if not 0 < values.HISTORY_QUERY_TIMEOUT_SECONDS <= 5:
        raise ValueError('BOUNDED_HISTORY_QUERY_REQUIRED')
    if (values.REQUIRED_OBSERVATIONS != 3 or type(values.REQUIRED_OBSERVATIONS) is not int
            or values.PLC_HEALTH_LEASE_SECONDS != .4 or values.IPC_GRANT_LEASE_SECONDS != .4
            or values.IPC_RESULT_LEASE_SECONDS != .4 or values.MODEL_INPUT_SIZE != (640,640)
            or values.CAPTURE_WINDOW_MS != 3000 or values.MOTION_STABLE_SECONDS != .6
            or values.FRAME_BOUNDARY_EPSILON_MS != 0):
        raise ValueError('RESTRICTED_CONTRACT_CHANGE_REQUIRES_SEPARATE_VALIDATION')
    if not 0 < values.FRAME_SPACING_SECONDS or not 0 < values.MAX_FRAME_AGE_SECONDS:
        raise ValueError('POSITIVE_FRAME_TIMING_REQUIRED')
    required=values.MOTION_STABLE_SECONDS+(values.REQUIRED_OBSERVATIONS-1)*values.FRAME_SPACING_SECONDS
    if not required < values.CAPTURE_WINDOW_MS/1000 <= values.INSPECTION_TIMEOUT_SECONDS:
        raise ValueError('FRAME_TIME_BUDGET_CONFLICT')
    if values.RUN_CAPTURE_BYTES <= values.RUN_CAPTURE_SCRATCH_BYTES+values.RUN_CAPTURE_BOOKKEEPING_BYTES:
        raise ValueError('RUN_CAPTURE_MEMORY_BUDGET_TOO_SMALL')
    for name in ('IPC_SNAPSHOT_MAX_AGE_SECONDS','IPC_RECONNECT_SECONDS','IPC_SOCKET_POLL_SECONDS',
                 'IPC_CLOSE_SECONDS','STARTUP_TIMEOUT_SECONDS','LINE_ARRIVAL_DEADLINE_SECONDS',
                 'LINE_ASSEMBLY_DEADLINE_SECONDS','ADMISSION_PREVIEW_MAX_AGE_SECONDS',
                 'MOCK_CYCLE_TIMEOUT_SECONDS','TRACK_MAX_UNOBSERVED_SECONDS','TRACK_MAX_CENTER_SPEED'):
        if getattr(values,name) <= 0:
            raise ValueError('POSITIVE_TIME_OR_RATE_REQUIRED:'+name)
    if not 0 < values.TRACK_ZONE_HYSTERESIS < 1 or not 0 < values.TRACK_MAX_CENTER_STEP <= 1 or not 0 < values.TRACK_MAX_REVERSE_STEP <= 1:
        raise ValueError('INVALID_TRACKING_RANGE')
    if values.POSE_ORB_SCALE_FACTOR <= 1 or values.RECTIFICATION_BACKGROUND > 255 or values.MOTION_PIXEL_DIFFERENCE > 255:
        raise ValueError('INVALID_IMAGE_SETTING')
    if not 1 <= values.PREVIEW_JPEG_QUALITY <= 100 or values.HISTORY_EXPORT_LIMIT < values.HISTORY_MAX_PAGE_SIZE:
        raise ValueError('INVALID_PREVIEW_OR_HISTORY_LIMIT')
    return values


def snapshot(values=config):
    validate_settings(values)
    data={key:value for key,value in vars(values).items() if key.isupper()}
    encoded=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    return {'sha256':hashlib.sha256(encoded.encode()).hexdigest(), 'values':json.loads(encoded),
            'scope':'PROCESS_IMPORT_SETTINGS', 'reload':'SERVICE_WORKER_RESTART_REQUIRED'}


def station_settings(station):
    """운영 진입점에서 한 번 호출. 장치 경로·승인·세션 정보는 원본 그대로 둔다."""
    validate_settings()
    result=copy.deepcopy(station)
    result.update(frame_spacing_seconds=config.FRAME_SPACING_SECONDS,
        max_frame_age_seconds=config.MAX_FRAME_AGE_SECONDS,
        inspection_timeout_seconds=config.INSPECTION_TIMEOUT_SECONDS,
        startup_timeout_seconds=config.STARTUP_TIMEOUT_SECONDS)
    result['fresh_frame'].update(max_trigger_to_frame_ms=config.CAPTURE_WINDOW_MS,
        inspection_window_ms=config.CAPTURE_WINDOW_MS,boundary_epsilon_ms=config.FRAME_BOUNDARY_EPSILON_MS)
    result['quality'].update(min_blur_variance=config.MIN_BLUR_VARIANCE,
        min_mean_brightness=config.MIN_MEAN_BRIGHTNESS,max_mean_brightness=config.MAX_MEAN_BRIGHTNESS)
    return result


def profile_settings(profile):
    validate_settings()
    result=copy.deepcopy(profile)
    result.update(arrival_deadline_s=config.LINE_ARRIVAL_DEADLINE_SECONDS,
        assembly_deadline_s=config.LINE_ASSEMBLY_DEADLINE_SECONDS,min_free_bytes=config.LINE_MIN_FREE_BYTES)
    return result


def package_values():
    """이미 존재하는 제품 JSON을 생성하는 값. 모델/기준점/해시는 별도 검증한다."""
    validate_settings()
    return dict(preprocessing={'confidence':config.DETECTOR_CONFIDENCE,'nms_iou':config.DETECTOR_NMS_IOU},
        decision_policy={'product_confidence':config.ENGINE_PRODUCT_CONFIDENCE,
            'part_confidence':config.ENGINE_PART_CONFIDENCE,'slot_overlap':config.ENGINE_SLOT_OVERLAP,
            'observation_count':config.REQUIRED_OBSERVATIONS},
        registration={'orb_nfeatures':config.POSE_ORB_FEATURES,'ratio_test':config.POSE_RATIO_TEST,
            'min_good_matches':config.POSE_MIN_MATCHES,'min_inliers':config.POSE_MIN_INLIERS,
            'min_inlier_ratio':config.POSE_MIN_INLIER_RATIO,'max_median_reprojection_error_px':config.POSE_MAX_REPROJECTION_ERROR_PX,
            'min_scale':config.POSE_MIN_SCALE,'max_scale':config.POSE_MAX_SCALE})


def validate_package_settings(package):
    """설정과 동결 엔진 패키지가 다르면 시작/교체 전 거부. 다른 제품은 기존 계약 사용."""
    if not package.recipe.get('engine_pose'):
        return
    from src.recipe.package import load_package
    settings = package_values()
    pose_info = package.recipe['engine_pose']
    pose_path = (package.root/pose_info['path']).resolve()
    if not pose_path.is_relative_to(package.root.resolve()):
        raise ValueError('POSE_REFERENCE_PATH_INVALID')
    pose_bytes = pose_path.read_bytes()
    if hashlib.sha256(pose_bytes).hexdigest() != pose_info['sha256']:
        raise ValueError('POSE_REFERENCE_HASH_MISMATCH')
    pose = json.loads(pose_bytes)
    envelope_root = (package.root/pose_info['envelope_package']).resolve()
    if not envelope_root.is_relative_to(package.root.parent.parent.resolve()):
        raise ValueError('ENVELOPE_PACKAGE_PATH_INVALID')
    envelope = load_package(envelope_root)
    if envelope.manifest_hash != pose_info['envelope_manifest_sha256']:
        raise ValueError('ENVELOPE_PACKAGE_HASH_MISMATCH')
    for actual in (package.preprocessing, envelope.preprocessing):
        if any(actual.get(key) != value for key, value in settings['preprocessing'].items()):
            raise ValueError('CONFIG_PACKAGE_MISMATCH: generate a new product package')
    for section in ('decision_policy','registration'):
        if any(pose[section].get(key) != value for key, value in settings[section].items()):
            raise ValueError('CONFIG_PACKAGE_MISMATCH: '+section)


def recorded_package(package, active_settings):
    """당시 설정을 기존 package_json에 연결. 판정·요청키는 변경하지 않는다."""
    value = package.snapshot()
    if active_settings is not None:
        value['configuration'] = copy.deepcopy(active_settings)
    return value


def validate_worker_settings(active_settings, backend):
    if backend.get('configuration_sha256') != active_settings['sha256']:
        raise ValueError('WORKER_CONFIGURATION_MISMATCH_RESTART_SERVICE')
