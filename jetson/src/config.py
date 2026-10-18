"""검사 프로그램의 편집 가능한 기준값. 첫 이관은 운영값을 그대로 유지한다.

서비스/Worker 재시작 후 적용한다. import는 장비·파일·DB에 접근하지 않는다.
제품 패키지에 들어가는 값은 notebook/deployment/configure_products.py로
새 복제본을 생성하고 기존 해시 검증을 거친다. 원본 자산은 직접 수정하지 않는다.
수정 제한 값은 수학/프로토콜 구조와 달리 문서화 목적이며 임의 보정하지 않는다.
"""

# ── 엔진 전체·부품 검출 (패키지 생성 → detector_factory / engine_dynamic) ──
# 검출기 후보 점수 하한, 0~1. 올리면 후보가 줄어 미검출 위험 증가. 판정 점수와 별개.
DETECTOR_CONFIDENCE = 0.25
# NMS의 두 예측 box IoU 상한. 올리면 겹친 후보가 더 남는다. 정답 비교 IoU가 아니다.
DETECTOR_NMS_IOU = 0.45
# PyTorch 직접 생성의 기존 fallback. 패키지 값이 전달되면 사용하지 않는다.
PYTORCH_DEFAULT_NMS_IOU = 0.7
# 제품 전체 채택 점수 하한. engine_dynamic.inspect_frame, 높이면 TARGET_UNCERTAIN 증가 가능.
ENGINE_PRODUCT_CONFIDENCE = 0.5
# 실제 부품 채택 점수 하한. 같은 정상/결품에 공통 적용. 낮추면 거짓 존재 위험.
ENGINE_PART_CONFIDENCE = 0.5
# 부품 box와 슬롯 교집합 / 부품 box 면적 하한. IoU가 아님. 높이면 배정이 엄격해짐.
ENGINE_SLOT_OVERLAP = 0.4
# 수정 제한: aggregate_three와 신규 사진 계약은 연속3장을 전제로 한다.
REQUIRED_OBSERVATIONS = 3

# ── 촬영·영상 품질 (standalone_service → Service → Worker/FreshFrameSelector) ──
# 서로 다른 채택 프레임의 원본 시각 최소 간격(초). 늘리면 확보 시간 증가.
FRAME_SPACING_SECONDS = 0.15
# 원본 프레임 최대 나이(초). 늘리면 오래된 사진 수용 위험. 신선도 회귀 필요.
MAX_FRAME_AGE_SECONDS = 0.35
# 수정 제한: 요청→유효 사진 기한(ms). 3초는 이번 이관에서 완화하지 않는다.
CAPTURE_WINDOW_MS = 3000
# 수정 제한: 원본 시간 경계 여유(ms). 0은 경계 완화 없음.
FRAME_BOUNDARY_EPSILON_MS = 0
# 서비스 전체 처리 기한(초). 촬영 기한과 별개. 저장/통신 계약 검증 필요.
INSPECTION_TIMEOUT_SECONDS = 15
# 초기 Worker 준비 대기(초). 늘리면 기동 오류를 늦게 알린다.
STARTUP_TIMEOUT_SECONDS = 90
# Laplacian 분산 하한. quality.assess_image, 높이면 흐린 사진을 더 많이 거부한다.
MIN_BLUR_VARIANCE = 25
# 전체 회색 영상 평균 밝기 하한/상한(0~255). 범위를 넓히면 저품질 사진 수용 가능.
MIN_MEAN_BRIGHTNESS = 35
MAX_MEAN_BRIGHTNESS = 225

# ── 움직임 (EngineInspector.motion: 카메라 좌표, 제품 영역의 변화량) ──
# 비교 해상도(폭, 높이). 분모는 이 전체 면적이며 대상 마스크 면적이 아니다. 고급 검증 필요.
MOTION_COMPARISON_WIDTH = 320
MOTION_COMPARISON_HEIGHT = 180
# 두 회색 픽셀의 절대 차이가 이 값보다 크면 변화로 센다. 높이면 미세 움직임에 둔감.
MOTION_PIXEL_DIFFERENCE = 25
# 변화 픽셀 / 전체 비교 면적 상한. 높이면 실제 이동을 놓칠 위험. TARGET_CHANGED 관련.
MOTION_FRACTION_LIMIT = 0.008
# 수정 제한: 안정 조건을 원본 시각으로 유지해야 하는 시간(초). 기존 0.6초 그대로.
MOTION_STABLE_SECONDS = 0.6

# ── 자세·슬롯 (EnginePoseEstimator, 기존 reference bank/좌표는 동결 자산) ──
# ORB 특징점 상한. 늘리면 대응점과 계산량 증가. 신규 성능 검증 필요.
POSE_ORB_FEATURES = 3500
# Lowe 거리 비율 상한. 낮추면 매칭은 엄격해지나 대응점 부족 가능.
POSE_RATIO_TEST = 0.75
# 자세 계산에 필요한 대응점/내점 최소 개수. 낮추면 잘못된 자세 채택 위험.
POSE_MIN_MATCHES = 12
POSE_MIN_INLIERS = 10
# 내점 / 사용 대응점 비율 하한. 낮추면 오매칭 수용 위험.
POSE_MIN_INLIER_RATIO = 0.18
# 재투영 오차 중앙값 상한(px). 높이면 부정확한 자세 수용 가능.
POSE_MAX_REPROJECTION_ERROR_PX = 3.5
# 기준 영상 대비 affine 배율 범위. 넓히면 다른 크기·오매칭 수용 가능.
POSE_MIN_SCALE = 0.6
POSE_MAX_SCALE = 1.6
# ORB pyramid 비율/단계/edge/FAST. engine_pose의 기존 구현값, 고급 검증 필요.
POSE_ORB_SCALE_FACTOR = 1.2
POSE_ORB_LEVELS = 8
POSE_ORB_EDGE_THRESHOLD = 15
POSE_ORB_FAST_THRESHOLD = 10
# bbox 폭·높이 각각에 곱하는 마스크 여백. 늘리면 주변 배경 특징이 더 들어간다.
POSE_DEFAULT_MARGIN = 0.15
POSE_REFERENCE_MARGIN = 0.08
POSE_SEARCH_MARGIN = 0.18
# affine 정규화 시 bbox 바깥 여백/배경값. 학습 입력 계약 관련, 임의 변경 금지.
RECTIFICATION_MARGIN = 0.18
RECTIFICATION_BACKGROUND = 40
# 기존 enhanced pose 모드에서만 사용되는 CLAHE. 일반 경로 전처리 추가가 아니다.
POSE_CLAHE_CLIP = 2.0
POSE_CLAHE_GRID = (8, 8)

# ── 저장·조회·진단 자원 (각각 독립된 의미의 예산) ──
# Journal.capacity의 최소 디스크 여유(bytes). 낮추면 원본 저장 실패 위험.
JOURNAL_MIN_FREE_BYTES = 100_000_000
# ACK 대기 이벤트 최대 개수. outbox 보호이며 운영의 별도 None 설정은 그대로 유지.
JOURNAL_OUTBOX_LIMIT = 10000
# 최근 이력 기존 API의 기본/최대 개수. 새 검색은 페이지 단위로 읽는다.
HISTORY_DEFAULT_LIMIT = 30
HISTORY_MAX_PAGE_SIZE = 100
# CSV 한 번 내보내기 상한. 더 큰 기간은 나눠 받는다. 검사 쓰기 lock을 사용하지 않는다.
HISTORY_EXPORT_LIMIT = 5000
# 읽기 전용 DB 조회 제한(초). 넘으면 조회만 중단하고 검사 Worker는 유지.
HISTORY_QUERY_TIMEOUT_SECONDS = 2.0
# process-local health 진단 최근 이벤트 수. 증가 시 메모리·상태응답 크기 증가.
HEALTH_DIAGNOSTIC_LIMIT = 64
# 이전 프레임 사용 내역 한도. consumed_frames의 중복 증거 조회 범위.
CONSUMED_FRAME_LIMIT = 1024
# 진단 저장 후에도 남겨둘 디스크 bytes / writer queue 개수. 증가 시 수집 거부/메모리 증가.
DIAGNOSTIC_RESERVE_BYTES = 512 * 1024 * 1024
DIAGNOSTIC_MAX_BUFFER_BYTES = 1024 ** 3
DIAGNOSTIC_QUEUE_ITEMS = 64
# STOP 진단의 기존 기본 요청. 승인된 경로별 더 작은 상한은 별도로 유지한다.
DIAGNOSTIC_DEFAULT_SECONDS = 10
DIAGNOSTIC_DEFAULT_FRAMES = 600
DIAGNOSTIC_DEFAULT_BYTES = 512 * 1024 * 1024
# 운전 진단 기존 상한. 신규 수집을 승인하는 값이 아니다. 늘릴 때 별도 부하/현장 승인 필요.
RUN_CAPTURE_SECONDS = 20
RUN_CAPTURE_FRAMES = 240
RUN_CAPTURE_BYTES = 768 * 1024 ** 2
RUN_CAPTURE_MEMORY_RESERVE = 1024 ** 3
RUN_CAPTURE_SCRATCH_BYTES = 32 * 1024 ** 2
RUN_CAPTURE_BOOKKEEPING_BYTES = 8 * 1024 ** 2
RUN_CAPTURE_MAX_IMAGE_BYTES = 8 * 1024 ** 2

# ── 라인 시간·수정 제한 계약·동결 자산 ──
# 기존 line_profile에서 실제 읽은 초 단위 기한. PLC 래더 타이머를 바꾸는 값은 아니다.
LINE_ARRIVAL_DEADLINE_SECONDS = 30
LINE_ASSEMBLY_DEADLINE_SECONDS = 30
LINE_MIN_FREE_BYTES = 1_000_000_000
# IPC snapshot 신선도(초). OpenerGateway.decode_snapshot, 400ms ready lease와 별개.
IPC_SNAPSHOT_MAX_AGE_SECONDS = 0.5
# 수정 제한: C/OpENer와 공유하는 준비 유효시간. 숫자만 바꿔 C가 바뀌지 않는다.
PLC_HEALTH_LEASE_SECONDS = 0.4
# 수정 제한: TensorRT 입력 크기는 모델 엔진 계약. 변경에는 재변환·대상장치 검증 필요.
MODEL_INPUT_SIZE = (640, 640)
# 동결 자산 경로. 기준점 배열·학습 통계·모델 바이트를 이 파일에 복사하지 않는다.
ENGINE_PARTS_PACKAGE = 'products/ENGINE_Z3005_5/dynamic_parts_005'
ENGINE_ENVELOPE_PACKAGE = 'products/ENGINE_Z3005_5/envelope_v007_fp16'
ENGINE_POSE_REFERENCE = 'pose/pose_reference.json'
ENGINE_POSE_REFERENCE_SHA256 = '1787dd7206b45f4ae4b6484a4b1883d2543f2c3da2d5e283f9c0e97c263e8afe'

# ── 추적·IPC·자원 기본값 (기존 동작을 그대로 이관) ──
# production_profile.tracker_config: 정규화 중심 이동/역방향 이동 상한. 크게 하면 오연결 위험.
TRACK_MAX_CENTER_STEP = 0.22
TRACK_MAX_REVERSE_STEP = 0.22
# 같은 추적에서 허용하는 관찰 소실 프레임 수 / 배출 확인 프레임 수.
TRACK_MAX_MISSED_FRAMES = 12
TRACK_CLEAR_FRAMES = 1
# 정규화 초당 중심 속도 상한 / 관찰 소실 최대 초. 위치 허용 편차의 실측값은 아니다.
TRACK_MAX_CENTER_SPEED = 0.2
TRACK_MAX_UNOBSERVED_SECONDS = 3
# 검사 영역 진입 hysteresis(정규화) / 연속 진입 프레임 수.
TRACK_ZONE_HYSTERESIS = 0.025
TRACK_ZONE_ENTRY_FRAMES = 3
# IPC 재접속 대기 / 소켓 poll 초. 실패 보호와 ready lease는 별도 계약이다.
IPC_RECONNECT_SECONDS = 0.5
IPC_SOCKET_POLL_SECONDS = 0.1
# 수정 제한: C와 연결된 승인/결과 큐 유효시간. 같은 숫자여도 health와 의미가 다르다.
IPC_GRANT_LEASE_SECONDS = 0.4
IPC_RESULT_LEASE_SECONDS = 0.4
# 송신 중복 증거 캐시 크기 / 종료 확인 초. 늘리면 메모리/종료 대기 증가.
IPC_SENT_CACHE_LIMIT = 512
IPC_CLOSE_SECONDS = 1
# InspectionService의 제품 관찰 큐와 미리보기 FPS 집계 길이. 영상 큐는 최신1장 계약 유지.
PRODUCT_OBSERVATION_QUEUE_SIZE = 16
PREVIEW_RATE_SAMPLE_COUNT = 30
# 이전 recent API/Journal의 기본 개수. 새 검색 페이지 설정과 의미를 구분한다.
JOURNAL_RECENT_LIMIT = 50
# field_raw_capture: 기존 별도 승인 진단에서만 사용하는 큐/인코더 개수.
FIELD_RAW_QUEUE_SIZE = 8
FIELD_RAW_ENCODER_WORKERS = 2
# STOP/운전 진단 controller의 시간대별 관찰 메타데이터 상한. 원본 영상 장수와 별개.
DIAGNOSTIC_TRACE_RECORDS = 1200
# FULL_FRAME 요청 승인 시 미리보기 최대 나이(초). 최신 원본 촬영 나이와 별개.
ADMISSION_PREVIEW_MAX_AGE_SECONDS = 2.0
# MockCell 거래 기한(초). 실제 PLC의 기한을 변경하지 않는다.
MOCK_CYCLE_TIMEOUT_SECONDS = 15

# 미리보기 JPEG 갱신 간격(초)/품질(0~100). 저장 원본 PNG 품질을 바꾸지 않는다.
PREVIEW_INTERVAL_SECONDS = 0.1
PREVIEW_JPEG_QUALITY = 75
# Worker 생존 신호 주기 / 전송 queue 대기(초). PLC 400ms health와 별도 경로.
WORKER_HEARTBEAT_INTERVAL_SECONDS = 0.5
WORKER_RESULT_QUEUE_TIMEOUT_SECONDS = 2
# 서비스/공정 루프 조회 주기(초). 늘리면 상태 갱신이 늦어진다.
SERVICE_POLL_SECONDS = 0.03
RUNTIME_POLL_SECONDS = 0.03
# RuntimeLog 회전 파일 크기(bytes)와 과거 파일 개수. 원본 Journal 보존 정책과 별개.
RUNTIME_LOG_MAX_BYTES = 8 * 1024 * 1024
RUNTIME_LOG_BACKUPS = 5
# ClearWindow 빈 영역 확인의 기존 기본값. 승인된 제품별 geometry는 별도 동결 자산.
AREA_CLEAR_SECONDS = 1.2
AREA_CLEAR_FRAMES = 6
AREA_MAX_FRAME_GAP_SECONDS = 0.5
AREA_MAX_FRAME_AGE_SECONDS = 1.0
