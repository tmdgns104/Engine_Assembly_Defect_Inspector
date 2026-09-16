# JETSON-P0-002R2 — Integrated Candidate Runtime Reacceptance

2026-09-16. **부분 재수용 / P0-003 실제 장치 진입 BLOCKED.**

통합 cold process 10회와 실제 Fresh Frame 10 triggers는 통과했다. 이어진 모델 cycle은 Recipe, evidence, SQLite commit, local result publication까지 완료했지만 stderr에 **NvMap error 12**가 재현됐다. NVML_SUCCESS assertion과 예외 종료는 재현되지 않았다. 기능 완료를 오류 없는 runtime 수용으로 승격하지 않으며 원인은 미확정이다. 추가 GPU 실행·복구·재시도는 하지 않았다.

## 수용 수준

| 항목 | 결과 | 근거와 범위 |
|---|---|---|
| A CONTRACT_TESTS | PASS — 기존 102 | runtime source 변경0, 이번에는 재실행하지 않음. `runs/jetson_p0_002/tests_verified.json` 유지 |
| B INTEGRATED_RUNTIME_GATE | PASS — 10/10 | INTEGRATED_RUNTIME_GATE_REACCEPTED_LAB. 각 process stderr 비어 있음 |
| C ACTUAL_CAMERA_FRESH_FRAME | PASS — 10/10 | ACTUAL_CAMERA_FRESH_FRAME_LAB. 잘못 선택한 프레임0 |
| D MODEL_FRESH_FRAME_SMOKE | **FAIL — runtime 수용** | 기능 경로 PASS/exit0, 그러나 NvMap error12 재현. 원본 기능 결과 PASS는 raw evidence에 그대로 유지 |
| E MOVING_CONVEYOR_PHYSICAL_ACCEPTANCE | **NOT_RUN** | conveyor/motor/제품 이동/PLC/pusher 사용0 |
| P0-003_ACTUAL_DEVICE_READY | **false / BLOCKED** | D의 메모리 오류를 별도 진단해야 함 |

## 환경과 실행 경계

- Python: `/home/jetson/oned_device_bench/envs/app_v1/bin/python`, 3.10.12. L4T36.4.7.
- process-local NumPy1.26.4: `env_candidates/numpy_compat_001/overlay/numpy/__init__.py`.
- torch2.8.0/CUDA12.6, OpenCV5.0.0, Ultralytics8.4.118은 기존 `~/.local/lib/python3.10/site-packages` 그대로 사용. TensorRT10.3.0은 `/usr/lib/python3.10/dist-packages/tensorrt`에서 import만 수행.
- **OpenCV5 metadata의 NumPy>=2 충돌은 여전히 존재한다.** DEPENDENCIES_OK 또는 production-approved로 표시하지 않는다.
- 새 candidate: `/home/jetson/oned_device_bench/candidates/app_v008_dev_p0_002_reaccept/runtime`. 기존 P0-002 runtime32파일과 SHA가 모두 같고 Windows source와도 일치한다. 기존 launcher는 복사만 했으며 실행하지 않았다.
- 새 data: `data/candidate_p0_002_reaccept/`; 새 diagnostics: `diagnostics/p0_002r2/`. HTTP service/port를 열지 않았다. 기존 DB를 연결하지 않았다.
- 각 process의 Ultralytics/Matplotlib/cache/torch/CUDA disk cache/temp 경로만 자기 diagnostic subfolder로 격리했다. `CUDA_CACHE_PATH`는 디스크 cache 위치이며 allocator 설정을 변경하지 않는다. allocator 환경변수는 모두 unset으로 관측됐다.
- 별도 패키지 설치·삭제, CUDA/TRT/OpenCV/torch 변경, empty_cache, power/clock/swap/CMA/reboot/systemd/PLC/MQTT/학습/TRT 변환/commit/push0. current symlink 유지.

## 통합 Gate 10회

각 회차 새 Python process를 순차 실행했다. NumPy/torch/cv2/Ultralytics/TRT import → NumPy bridge/CUDA 초기화 → HCAM0 MJPG1280×720@30 open → memory-only5프레임 → **동일 pipeline 열린 상태 유지** → 기존 best.pt CPU load/CUDA 이동 → 승인 저장 이미지에 기존 PyTorchDetector.detect 1회 → synchronize → 추가5프레임 → 정상 close 순서다. detect 내부 Ultralytics warmup과 forward를 단일 forward로 계산하지 않는다.

모델 CPU load 지점은 `sys.setprofile`로 실제 YOLO 생성자 return을 관측했다. source나 모델을 수정하거나 모델을 추가로 load하지 않았다. CUDA 이동 지점은 기존 Detector 생성자 완료 후 관측했다. 모두 CPU load → cuda:0 이동, 입력 `[1,3,640,640]`를 확인했다.

모델 SHA: `49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1`.

승인 이미지 SHA: `04380e88c2802d39826da972d2fdb30eaba03e0c7a17713d5178434fa16c2b18`. 기존 assets의 `5031fbaf16a94877b5b6aa46f9e90c03/215fc0dd6f7a4fc19fbee249cfdd5642.png`를 읽기만 했다.

| 회차 | PID | 결과 | AFTER_DETECT MemAvailable kB | CmaFree kB |
|---|---:|---|---:|---:|
| 1 | 17992 | PASS | 3,193,324 | 324 |
| 2 | 18085 | PASS | 3,217,708 | 0 |
| 3 | 18175 | PASS | 3,229,380 | 0 |
| 4 | 18265 | PASS | 3,261,540 | 36 |
| 5 | 18354 | PASS | 3,255,524 | 0 |
| 6 | 18443 | PASS | 3,244,160 | 0 |
| 7 | 18537 | PASS | 3,234,780 | 0 |
| 8 | 18626 | PASS | 3,239,596 | 160 |
| 9 | 18715 | PASS | 3,241,556 | 0 |
| 10 | 18804 | PASS | 3,236,292 | 0 |

11개 관측 지점은 PROCESS_START, AFTER_IMPORT, AFTER_CUDA_INIT, AFTER_CAMERA_OPEN, AFTER_CAMERA_5_FRAMES, AFTER_MODEL_LOAD, AFTER_MODEL_TO_CUDA, AFTER_DETECT, AFTER_SECOND_CAMERA_BATCH, AFTER_CAMERA_CLOSE, PROCESS_END다. 각 회차 JSON에 MemAvailable/CmaFree/SwapFree와 초기화 이후 CUDA free/total/allocated/reserved/peak가 있다. 초기화 전 snapshot은 CUDA를 강제 초기화하지 않는다.

통합 관측 범위: MemAvailable3,193,324–4,138,256kB, CmaFree0–6,524kB. AFTER_DETECT CUDA allocated12,142,592B/reserved60,817,408B. CmaFree0에서도 통과했으며 이 값만으로 부족·단편화·driver 원인을 확정할 수 없다. 각 회차 loaded libraries/process list/camera owner를 보존했다. 10회는 이번 lab gate이며 신뢰도·성능 benchmark가 아니다.

## Actual Fresh Frame

기존 FreshFrameSelector를 그대로 사용했다. Trigger 직전 preview metadata를 먼저 제시해 PRE_TRIGGER 거부를 확인하고, 같은 epoch에서 trigger 이후 source 추정 시각을 가진 프레임만 선택했다. 10 triggers 모두 통과했고 PRE_TRIGGER/STALE/DUPLICATE_FRAME/PTS_REGRESSION/CAMERA_EPOCH_CHANGED 잘못 선택0이다. 각 trigger/frame ID, sequence, PTS, source/received/trigger monotonic, wait/age를 raw JSON에 보존했다. 이미지는 저장하지 않았다.

관측값 범위(ms): trigger_to_frame0.066–35.675, frame_age29.618–35.720, selection_wait29.684–68.515. percentile/성능 합격 기준은 산출하지 않았다. source 시각은 GStreamer PTS의 local monotonic 추정이며 **sensor exposure timestamp는 검증되지 않았다**. epsilon0, max_age0.35초, window3000ms, 기존 설정을 유지했다. 실제 conveyor 제품 정합 기준으로 확정하지 않는다.

## 모델 cycle과 NvMap 재현

새 process에서 카메라를 열고 기존 Detector를 준비했다. 지속 worker의 준비 완료 상태와 같이 승인 저장 이미지 warmup1회를 trigger 전에 수행했다. 이후 LOCAL_TEST trigger1개에 기존 Recipe의 observation_count3/spacing0.15초를 유지해 서로 다른 fresh frame3개를 검사했다. 기존 `assess`, `encode_evidence`, `Journal.admit/finish`를 직접 연결한 **component integration smoke**이며 전체 API/worker orchestration 수용은 아니다. calibration/UI 사람 승인을 생성하지 않았다.

- inspection: `25f87ed9ea1145b2b66bb1da149137a8`
- trigger: `74977597c0604750b3c5e08c26d53951`
- Recipe: **REVIEW**, 물리 view/제품 identity/calibration 미승인. 제품 정확도 PASS로 해석하지 않는다.
- raw PNG3개(529,924 / 529,382 / 537,869B), overlay JPEG1개(56,846B). 각 파일 SHA와 selected frame_id 연결 확인.
- 후보 SQLite integrity `ok`. 독립 reader가 COMPLETE result와 INSPECTION_COMPLETED outbox를 확인한 뒤 diagnostic local file에 공개1회. PLC/network publication0.
- commit 반환 monotonic16905.15917851 → publish16905.164094698. 둘 모두 trigger 후3초 window 안에 있고 active session 일치. late result0.
- cycle에서 PRE_TRIGGER2개, OBSERVATION_SPACING6개 거부. timeout/과거 frame fallback0.

그러나 process stderr는 다음을 포함한다.

```text
NvMapMemAllocInternalTagged: 1075072515 error 12
NvMapMemHandleAlloc: error 0
```

process exit0과 raw functional PASS를 덮어쓰지 않았다. 최종 D 수용은 **FAIL**로 분리했다. 오류가 warmup·camera·세 번의 detect 중 어디에서 출력됐는지는 **미확정**이다. stderr는 process 종료 후 수집했고 timestamp가 없으므로 정확한 지점과 동시 메모리 값을 역으로 만들 수 없다. 모델 cycle의 별도 loaded-library snapshot도 없다. 통합 Gate10회 library 목록과 process 종료 후 host 관측은 보존돼 있다.

종료 후 관측: MemAvailable2,538,744kB/CmaFree1,876kB, fuser camera owner없음. 이 값은 오류 순간의 값이 아니다. NVML assertion은 재현되지 않았고 NvMap 출력만 재현됐다. 이전 P0-002의 전체 실패가 동일하게 재현됐다고 단정하지 않는다. 오류 확인 이후 GPU 작업·재시도0. 다음은 별도 Task에서 통합 모델 cycle의 stderr 발생 단계와 동시 메모리를 계측하는 것이며, 패키지/allocator 복구를 임의로 정하지 않는다.

## 보존과 산출물

Jetson 보호30경로 그룹, P0-001R inventory922파일, current symlink 전후 동일. app_v007/app_v1/기존 사용자 패키지/원본 product·model·DB·assets/P0-002 candidate/이전 P0-002R diagnostics/Ultralytics settings와 알려진 cache를 포함한다. Windows manifest의 PC mirror86파일과 Fresh Frame source도 동일하다. 신규 경로는 candidate32파일, candidate data7파일(DB/WAL/SHM+assets4), diagnostics85파일이다. 전 OS의 모든 background write를 감사한 결과는 아니며 지정 보호 경로의 SHA256 보존 결과다.

기존 사용자 변경은 보존했고 수정한 기존 파일은 Task 진행 기록용 `docs/STATUS.md`뿐이다. 새 Task 문서는 이번 실행 결과로 갱신했다. 저장소 runtime source 변경0, git diff --check 및 새 진단 코드 compile/결과 대조 검증은 `runs/jetson_p0_002r2/final_checks.json` 참조. commit/push 없음.

기계 판정: [JETSON-P0-002R2.json](../verification/JETSON-P0-002R2.json). Raw evidence: `runs/jetson_p0_002r2/{integrated_01..10,fresh,model_cycle,before,after,new_inventory}.json`. Jetson에는 원본 process stderr와 stage JSON을 `diagnostics/p0_002r2/`에 보존했다.
