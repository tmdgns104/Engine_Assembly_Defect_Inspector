# JETSON-P0-002 — Moving Conveyor Fresh Frame

Status: **IMPLEMENTED / CONTRACT_TESTS_PASS / DEVICE_GATE_BLOCKED** (2026-09-16). 앞 Task: P0-001R. 다음: Runtime Gate C 원인 확인 후 P0-002 실기기 재검증. P0-003 실제 성능 검증은 BLOCKED.

## 현재 실행 계약 (2026-09-16)

사용자가 구현 및 격리 Candidate 검증을 승인했다. Windows Runtime 소스의 선택적 Fresh Frame 기능을 개발하되 Jetson `releases/app_v007`, app_v1 환경, earbud package/model, 기존 DB/assets, P0-001R overlay는 보존한다. baseline 코드와 별도 config/cache/data로 선행 Gate를 실행했다. A import/bridge/CUDA 및 B camera 5 frames PASS; C는 기존 Detector의 첫 predict warmup convolution에서 CUDA allocator `NVML_SUCCESS` assertion으로 실패했다. 추가 패키지 변경·inference 재시도·actual-device Fresh Frame 및 모델 결합 검증은 하지 않는다.

독립 범위: TriggerContext/PTS clock/epoch/selector, Worker·Service 연결, 합성 12개 필수 시나리오 및 기존 Runtime 회귀. single-active, 원장 commit 후 공개, 사람 calibration 기준을 유지한다. candidate 설정은 lab 값이며 physical acceptance가 아니다. C/D 실제 검증은 NOT_RUN, E physical acceptance도 NOT_RUN으로 기록한다.

완료 게이트: 계약/회귀 결과, Gate 실패 전체 원인 근거, 보호 파일 전후 hash, candidate inventory, git diff --check. 산출물은 Fresh Frame 계약 문서·verification JSON 및 이 Task. commit/push 금지.

## 수용 결과

| 수준 | 결과 | Evidence |
|---|---|---|
| A CONTRACT_TESTS | PASS | 새 27 + 기존 Runtime 75 = 102 tests |
| B CANDIDATE_RUNTIME_SMOKE | FAIL | import/bridge/CUDA, memory-only camera 5 frames PASS; 모델 warmup CUDA allocator assertion |
| C ACTUAL_CAMERA_FRESH_FRAME | NOT_RUN | Gate C 실패로 중단 |
| D MODEL_FRESH_FRAME_SMOKE | NOT_RUN | 모델+fresh frame+recipe+candidate DB cycle 0 |
| E MOVING_CONVEYOR_PHYSICAL_ACCEPTANCE | NOT_RUN | 실제 conveyor 미사용 |

Gate C 오류: `NVML_SUCCESS == r INTERNAL ASSERT FAILED` (`CUDACachingAllocator.cpp:1131`), stderr NvMap allocation error 12. 기존 승인 이미지로 Detector 한 번 시도했으나 warmup에서 실패했다. 원인 미확정이며 읽기 전용 자원 진단만 수행했다. OpenCV5 metadata의 numpy>=2와 candidate 1.26.4 충돌은 유지한다.

TriggerContext/selector, Camera PTS·segment·epoch, Worker 선택 및 inference/encoding 후 취소/deadline 검사, Service session/trigger 검증, Journal의 원자적 TRIGGER_ACCEPTED와 asset frame_id 연결을 구현했다. single-active와 기존 사람 calibration 승인, Recipe 및 파일→commit→publish 의미를 유지했다. DB schema 변경은 없다.

필수 합성 12개 조건과 기존 Camera/Worker/Service/Journal/Mock/PC Sync/Product Package 회귀를 수행했다. 최초 회귀 100 PASS 후 asset frame 연결 추가로 102개 중 기존 ID 없는 합성 입력 1개 실패를 발견했고, optional legacy frame_id 호환을 유지하도록 수정한 뒤 최종 102 PASS. 새 selector의 frame_id 필수 검사는 유지한다. 최초 실패와 최종 로그 모두 보존한다.

새 Jetson Candidate에 소스 32파일 배치, Python 30파일 compile-only PASS. Gate 실패로 launcher가 앱/DB 시작을 차단하는 것을 확인했으며 후보 DB/기록 생성 0, port listener 0, camera owner 0이다. 최초 inventory와 후보 파일 1개 수정 이력 및 최종 inventory를 보존한다. 원본 보존 해시와 git diff --check 결과는 verification에 수록한다.

산출물: [계약](../docs/jetson/JETSON_FRESH_FRAME_CONTRACT.md), [verification JSON](../docs/verification/JETSON-P0-002.json). Raw evidence: `runs/jetson_p0_002/` (Git ignored). Candidate: `/home/jetson/oned_device_bench/candidates/app_v008_dev_p0_002/`.

재개 순서: CUDA allocator 원인 확인 → Runtime Gate C 통과 → 반복 실제 camera trigger → model/recipe/candidate DB 최소 cycle. 그전에는 Task 전체 완료 또는 P0-003 실제 성능 Gate 준비 완료로 표시하지 않는다. 패키지 교체·환경 우회가 필요하면 별도 승인 범위다.

## 이전 초안 기록 (현재 실행 권한·결과는 위 계약 우선)

### 문제와 목표

app_v007은 Service 수락 후 추정 source time을 필터링하지만, 물리 trigger 시각·센서 노출 시각·이동 중 같은 제품이라는 보장은 없다. 기존 latest queue/PTS 검사·단일 Camera owner를 재사용하여 trigger와 관측의 명시적 관계를 설계하고 검증한다.

## 선결 조건 / 설계 결정

- [Baseline](../docs/jetson/JETSON_RUNTIME_BASELINE.md)의 현재 torch/NumPy FAIL을 별도 허가 범위에서 해결한 후 대상 실행 검증. 이 초안은 설치 변경 권한이 아니다.
- trigger 의미(로컬 request 수신 또는 나중의 PLC event), clock domain, 첫 유효 프레임 창, 최대 frame age, 제품 간 간격/속도/허용 지연은 착수 시 합의한다. 임의 숫자를 성능 수용값으로 확정하지 않는다.
- 고정 calibration/슬롯과 이동 대상 정합은 별도 설계 경계다. Fresh Frame 완료만으로 엔진 누락 판정·Moving Conveyor 전체 완료를 주장하지 않는다.

## 예정 범위

검토 대상은 `src/camera/gstreamer_camera.py`, `src/vision/inspection_worker.py`, Camera/frame 계약 및 새 station 설정이다. source PTS·수신 시각·trigger ID/time·선택/폐기 이유·capture epoch를 분리하고, 노출 시각 미검증 플래그를 유지한다. 현재 단일 active job/busy 거부를 기본으로 하며 다중 queue/제품 tracking 도입은 별도 설계 결정이다. 실제 작업은 app_v007과 earbud package를 보존한 새 후보 릴리스/설정에만 수행한다.

## 수용 초안

1. synthetic clock/frame으로 trigger 이전·경계값·stale·중복/역행 PTS·camera epoch 변경·버퍼 적체·연속 trigger·취소·deadline을 시험한다. 거부 프레임을 조용히 현재 제품으로 사용하지 않는다.
2. `frame_id/source_pts/trigger_id/session/cycle/request`를 같은 근거에 연결한다. 추론 전후의 age 창을 구별하고 timeout 시 과거 프레임을 대신 반환하지 않는다.
3. 실제 장치에서는 별도 승인된 촬영 범위에서 source time 추정과 가능하면 노출 시각을 대조한다. 실제 센서 timestamp 증거가 없으면 그 한계를 유지한다.
4. 기존 정지 검사·취소/늦은 결과·원장 불변 회귀 통과 및 app_v007/model/DB/이미지 보존 hash를 확인한다. 속도·FPS 실측은 필요한 경우 합의한 동일 workload로 수행한다.

초안의 산출물 예정은 새 후보 코드/관련 집중 시험, trigger/frame 계약 문서, `docs/verification/JETSON-P0-002.json`이었다. 초안 당시 구현·촬영·실행 미승인 상태는 이번 사용자의 구현/Candidate smoke 승인으로 대체되었다. PLC/컨베이어 실제 제어, TensorRT 변환, MQTT, 원본 삭제/DB migration 제외는 유지한다.
