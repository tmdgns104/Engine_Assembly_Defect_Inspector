# JETSON-P0-002R4 — Long-Lived Integrated Runtime Stability Soak

2026-09-16. **LONG_LIVED_RUNTIME_STABILITY_PASS_LAB**. **P0_003_ACTUAL_DEVICE_READY = true**, Latency instrumentation 시작 범위에 한한다. ROOT_CAUSE_UNCONFIRMED이며 production acceptance나 이전 NvMap 원인 해결을 의미하지 않는다.

## 실제 실행

PID20883의 **한 Python process**에서 Camera, Detector, CUDA 초기화, Journal, session을 각각1회 수행했다. R2 candidate의 변경 없는 Camera/Detector/FreshFrameSelector/Quality/Recipe/encode/Journal을 사용했다. 승인 저장 이미지 warmup1회 뒤 동일 runtime으로30 full cycles를 실행했고 fresh detect90회가 완료됐다. cycle마다 객체 ID와 camera epoch/session이 유지됨을 확인했다. 재실행0.

process 전체 관측 시간은 **35.803초**다. 이번 사용자가 정한30 consecutive cycles의 lab gate이며, 수 시간·수일 endurance 시험으로 표현하지 않는다. 정식 성능 benchmark나 percentile 분석은 수행하지 않았다.

| 항목 | 결과 |
|---|---|
| completed cycles | 30/30 |
| warmup / fresh detect API calls | 1 / 90 |
| Python/CUDA exception | 0 |
| stderr NvMap / NVML_SUCCESS / CUDACachingAllocator | 0 / 0 / 0; 전체 stderr0줄 |
| camera epoch 변경 / unexpected close | 0 / 0 |
| pre-trigger / stale / duplicate / PTS regression / epoch mismatch 선택 | 모두0 |
| SQLite integrity | ok |
| inspection COMPLETE / unique inspection / request / cycle | 각30 |
| local publication / late result | 30 / 0 |
| assets | raw90 + overlay30 = 120; 실제 파일 SHA120개 모두 일치 |
| 원본 보호 SHA | 변경0 |

## cycle과 증거 계약

session1에서 cycle_id/request_id1..30, cycle마다 새 trigger UUID를 사용했다. Trigger 직전 preview를 selector에 제시해 PRE_TRIGGER 거부를 확인했다. 선택된90프레임은 모두 estimated_source_monotonic > trigger, 동일 epoch, 증가하는 sequence/PTS, 기존 max age0.35초 이내였다. 과거 frame fallback이나 reconnect는 없다. source monotonic은 GStreamer PTS 추정이며 실제 sensor exposure 시각 검증은 아니다.

각 cycle은 기존 observation_count3/spacing0.15초/window3000ms를 유지했다. Detector → Quality → Recipe → encode → Journal.finish commit → local diagnostic publication을 수행했다. Journal.admit는 기존 연결 의미를 유지해 trigger 직후에 수행했다. 모든 결과는 물리 view/calibration 미승인에 따른 **REVIEW**이며 제품 정확도 PASS를 만들지 않았다.

각 결과의 trigger·selected frame·asset·inspection·request/cycle 연결, 실제 asset SHA, commit 반환 시각 < publication 시각 < cycle deadline, 단일 active session, COMPLETE event와 publication 내용 일치를 확인했다. HTTP/PLC publish나 전체 service orchestration 수용은 아니며 unchanged component runtime의 local publisher smoke다.

새 data root: `/home/jetson/oned_device_bench/data/candidate_p0_002r4_soak/`.

- 정상 종료 뒤 candidate data 총 **48,873,576B**.
- SQLite 본체 **1,314,816B**.
- raw90/overlay30 모두 위 data root 안에만 존재. Dataset에 넣지 않았다.
- 원본 Edge DB 및 PC mirror는 연결하지 않고 content hash만 비교했다.

## 실시간 감시와 종료

R3 parent pipe collector를 새 진단 경로에서 재사용·확장했다. stderr가 ready인 경우 먼저 drain하고, 각 cycle 시작 전 child가 parent에 permission을 요청한다. Parent는 현재 읽을 수 있는 pipe output을 처리한 뒤 CONTINUE/STOP을 회신한다. 첫 대상 marker 수신 시 즉시 stop file을 기록하며 child는 native call이 반환한 뒤 단계 경계에서 멈춘다. 강제 kill, empty_cache, 강제 GC 또는 allocator 설정 변경은 없다. cooperative timeout도 stop 요청만 사용한다.

합성 시험에서 첫 작업 완료, 다음 cycle STOP, 분할 stderr line 수집, atexit teardown 수집을 확인했다. 실제 soak는30개의 CONTINUE를 받았고 stop 요청은 없었다. 실시간 감시는 실제 출력의 parent 수신을 기준으로 하므로 아직 pipe에 도착하지 않은 native 출력까지 선제 탐지한다고 주장하지 않는다.

초기화, cycle별 trigger/선택/detect/Recipe/encode/commit/publish/END, camera/journal close와 BEFORE_PROCESS_EXIT까지 총647개 stage를 기록했다. Parent는 이후 양쪽 EOF와 process exit까지 수집했다. native emission 시각과 pipe 수신 시각은 다르며, 이번에는 실제 오류 line이 없어 최초 오류 cycle/interval은 N/A다.

## 메모리 누적 관측

시작은 warmup·Journal/session 초기화 후 RUNTIME_READY, 종료는 CYCLE_30_END다. cycle END는 cycle 함수가 반환하며 일반 참조가 해제된 후 측정했다. 강제 GC는 수행하지 않았다. 각 detect END와 stage에서도 CUDA 및 host memory를 기록했다.

| 항목 | start | min | max | end |
|---|---:|---:|---:|---:|
| MemAvailable kB | 2,179,752 | 2,174,596 | 2,187,532 | 2,177,436 |
| CmaFree kB | 0 | 0 | 3,596 | 0 |
| SwapFree kB | 3,343,032 | 3,343,032 | 3,343,032 | 3,343,032 |
| CUDA allocated B | 12,142,592 | 12,142,080 | 12,142,592 | 12,142,080 |
| CUDA reserved B | 60,817,408 | 60,817,408 | 60,817,408 | 60,817,408 |

CUDA free/total/peak 값은 raw stage JSON에 있다. 이30개 cycle에서 reserved 증가가 관측되지 않았으며 MemAvailable은 시작 대비2,316kB 낮았다. 단순 차이로 leak을 확정하거나 장기 leak 부재를 증명하지 않는다. CmaFree0에서도 이번 경로가 통과한 사실만 기록하며 이전 오류 원인을 추측하지 않는다.

## 환경·원본 보존

Python은 기존 app_v1, NumPy1.26.4는 기존 overlay의 process-local 우선 경로다. torch2.8.0/CUDA12.6/OpenCV5.0.0/Ultralytics8.4.118, HCAM0 MJPG1280×720@30을 유지했다. OpenCV5 metadata의 numpy>=2 충돌은 계속 존재한다. DEPENDENCIES_OK 또는 production-approved 환경으로 표시하지 않는다.

Jetson 신규 쓰기는 `diagnostics/p0_002r4_soak/` 및 `data/candidate_p0_002r4_soak/`뿐이다. Ultralytics/Matplotlib/torch/CUDA disk cache/temp도 새 diagnostics에 격리했다. app_v007/app_v1/P0-001R overlay/P0-002·R2 candidates/package·best.pt/기존 DB·assets/R2 data/이전 R·R2·R3 diagnostics/사용자 패키지·settings·알려진 cache의 SHA를 비교했다. 보호34그룹+overlay inventory+current symlink가 동일하며 Windows source·PC mirror·이전 raw evidence도 동일하다. 이는 열거한 보호 대상의 content hash 검증이며 OS 전체 background write 감사가 아니다.

runtime source/환경/camera 설정/시스템 서비스 변경0. 설치·reboot·power/swap/CMA·PLC/MQTT·TensorRT 변환·학습·Dataset 변경·reset/clean·commit/push0. 기존 사용자/다른 팀원 변경을 보존했다. 기존102 tests는 source 변경이 없어 재실행하지 않았다.

## 검증과 후속 범위

기계 판정은 [JETSON-P0-002R4.json](../verification/JETSON-P0-002R4.json), raw는 `runs/jetson_p0_002r4/soak.json`, 파일 inventory와 보호 비교는 같은 폴더의 `inventory/before/after/windows_before.json`이다. 최종 대조·compile·git diff --check는 `final_checks.json`에 기록한다. 원본 stdout/stderr/stage/cycle/publication은 Jetson diagnostics에도 보존한다.

이번 lab gate는 완료했다. P0-003에서 실제 장치 latency instrumentation을 시작할 수 있다. 실제 conveyor acceptance와 production reliability, 이전 NvMap root cause resolution은 여전히 미확정이다.
