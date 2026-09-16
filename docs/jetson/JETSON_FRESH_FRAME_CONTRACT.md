# JETSON-P0-002 — Fresh Frame Contract

2026-09-16. **IMPLEMENTED / SYNTHETIC_VERIFIED / ACTUAL_DEVICE_BLOCKED**.

| 수용 수준 | 결과 | 근거 / 한계 |
|---|---|---|
| A. CONTRACT_TESTS | PASS | 새 27개 + 기존 Runtime 75개 = 102 tests |
| B. CANDIDATE_RUNTIME_SMOKE | FAIL | A import/bridge/CUDA, B camera PASS; C Detector warmup CUDA allocator 실패 |
| C. ACTUAL_CAMERA_FRESH_FRAME | NOT_RUN | 선행 Runtime Gate C 실패로 실행 금지 |
| D. MODEL_FRESH_FRAME_SMOKE | NOT_RUN | 실제 모델 + fresh frame + recipe + candidate DB cycle 0 |
| E. MOVING_CONVEYOR_PHYSICAL_ACCEPTANCE | NOT_RUN | 실제 conveyor/PLC 접근·제어 없음 |

공식 Evidence: [JETSON-P0-002.json](../verification/JETSON-P0-002.json). 이 결과는 `FRESH_FRAME_RUNTIME_SMOKE` 또는 `MOVING_CONVEYOR_ACCEPTED`가 아니다. app_v007이 복구되었다고 판단하지 않는다.

## 선행 Runtime Gate와 중단 근거

기존 app_v007 코드와 best.pt를 읽기 전용 대조로 사용했다. 별도 Candidate process에서 P0-001R NumPy overlay를 sys.path 앞에 넣고 Ultralytics/Matplotlib/GStreamer cache를 새 candidate root 아래로 격리했다. 기존 DB를 열지 않았다.

| 항목 | 실제 경로 / 결과 |
|---|---|
| Python | `/home/jetson/oned_device_bench/envs/app_v1/bin/python`, 3.10.12 |
| NumPy | `env_candidates/numpy_compat_001/overlay/numpy/__init__.py`, 1.26.4 |
| torch | `/home/jetson/.local/lib/python3.10/site-packages/torch/__init__.py`, 2.8.0, CUDA 12.6 |
| cv2 | `/home/jetson/.local/lib/python3.10/site-packages/cv2/__init__.py`, 5.0.0 |
| TensorRT | `/usr/lib/python3.10/dist-packages/tensorrt/__init__.py`, 10.3.0 |
| Gate A | 4 imports, `torch.from_numpy`, `torch.cuda.is_available` PASS |
| Gate B | USB HCAM0 MJPG 1280×720@30, memory-only 5 frames; sequence·PTS·received_monotonic 증가, source estimate 존재, 수신 age 약 32–46 ms |
| Gate C | 승인된 기존 저장 이미지에서 기존 `PyTorchDetector.detect` 1회 호출 시도. Ultralytics warmup convolution에서 실패, 결과 반환 0 |

오류: `RuntimeError: NVML_SUCCESS == r INTERNAL ASSERT FAILED at /opt/pytorch/c10/cuda/CUDACachingAllocator.cpp:1131`. stderr에는 `NvMapMemAllocInternalTagged ... error 12`도 있다. 실패 직후 MemAvailable 약 4.34 GB, CmaFree 2,024 kB였다. **메모리 할당 경로의 실패는 관측 사실이고, 물리 메모리 부족/단편화/torch allocator 호환성 중 어느 것이 원인인지는 미확정**이다. 사용자 프로세스 종료, 캐시 비우기, 파라미터 우회, 패키지 교체 또는 inference 재시도는 하지 않았다.

OpenCV metadata의 `numpy>=2` 요구와 overlay 1.26.4 충돌은 그대로다. 이번에는 모델 Gate가 실패했으므로 `RUNTIME_SMOKE_PASS_WITH_METADATA_CONFLICT`도 부여하지 않는다. 기본 새 프로세스는 다시 NumPy 2.2.6을 선택한다. P0-001R의 PREPROCESS_READY는 실제 Detector 성공을 뜻하지 않는다.

원시 `runs/jetson_p0_002/gate.json`의 `gate_C` 초기값은 예외 전에 PASS로 바뀌지 않아 NOT_RUN으로 남았다. 실제 traceback으로 호출 시도가 확인되므로 이 문서와 verification의 Gate C 판정은 **FAIL**이다. 원시 기록을 덮어쓰지 않았다.

## 후보 코드와 재사용 경계

기존 Camera/Worker/InspectionService/Journal을 확장했다. 새 Camera owner, 처리 queue, Detector backend, PLC adapter는 만들지 않았다. `station.fresh_frame`이 있는 Candidate에서만 Trigger/selector 경로를 사용한다. 카메라 clock 환산·metadata 보완과 asset frame 연결은 후보 소스에 반영했으며 Jetson의 app_v007 원본은 그대로다.

| 위치 | 책임 |
|---|---|
| `src/camera/fresh_frame.py` | 불변 TriggerContext, 순수 selector, bounded rejection evidence |
| `src/camera/gstreamer_camera.py` | PTS/segment/running-time 환산, camera epoch, 시각 metadata |
| `src/vision/inspection_worker.py` | 선택 후 inference, inference/encoding 후 재검사, raw/overlay의 frame_id 연결 |
| `apps/edge_service/inspection.py` | server 수신 시각·epoch 결합, single-active, session/trigger 재검증 |
| `src/journal/sqlite.py` | request와 TRIGGER_ACCEPTED event의 동일 transaction, 기존 파일→DB commit→공개 유지 |
| `config/inspection_station_candidate_p0_002.json` | Candidate만 쓰는 lab 설정 |
| `scripts/run_jetson_fresh_candidate.py` | 별도 path/data/port, process-only overlay, Gate 실패 시 시작 차단 |

기존 Product Package, Recipe, Detector, 품질 기준, 사람 calibration/가시성 승인 및 PC Sync 의미는 유지한다. 원장 schema migration은 없다. frame_id는 immutable result/assets JSON에 보존되고 PC mirror에서도 유지된다.

## Trigger와 시간 계약

`TriggerContext`는 `trigger_id`, `cell_id`, `plc_session_id`, `cycle_id`, `request_id`, `trigger_received_monotonic`, `trigger_source`, `capture_epoch`, `deadline_monotonic`을 갖는다. 현재 source는 MOCK 또는 LOCAL_TEST만 허용한다. OMRON_PLC는 아직 지원하지 않는다.

Service.submit 진입 때 읽은 **Jetson local monotonic** 값이 t0다. 이 시점은 API body가 Service에 전달된 시점이며 HTTP 첫 바이트 도착 시각이나 실제 PLC edge 시각이 아니다. 클라이언트 supplied timestamp/epoch를 사용하지 않는다. 수락 당시 최신 preview의 camera epoch에 trigger를 묶고, 이미 처리 중이면 새 request를 BUSY로 거절한다. 같은 request 재전송은 같은 inspection으로 응답하며 새 trigger를 생성하지 않는다.

최종 결과 전에 현재 session과 active trigger 일치를 다시 검사한다. 취소·deadline·old session·잘못된 trigger 결과는 원장에 ERROR/CANCELLED 또는 quarantine으로 남기며 정상 검사 결과로 공개하지 않는다. 취소된 Worker가 끝나기 전 다음 cycle을 수락하지 않는다.

프레임은 `frame_id`, `sequence`, `source_pts_ns`, `received_monotonic`, `estimated_source_monotonic`, `received_at`, `camera_epoch`를 가진다. received_monotonic은 BGR copy가 끝나 소유권을 확보한 시점이다. received_at은 UTC 관측 기록일 뿐 freshness 비교에 쓰지 않는다.

PTS는 `sample.get_segment().to_running_time(TIME, pts)`로 변환한다. monotonic anchor를 **GstClock 읽기 직전**에 잡고 pipeline running time과 차이를 빼 source time을 추정한다. 이미지 복사 뒤 시각을 anchor로 쓰면 복사 시간이 source estimate를 미래 쪽으로 이동시키므로 제외했다. clock 읽기 전후 간격은 `clock_mapping_uncertainty_ms`로 남긴다. 이 conservative mapping은 두 clock이 해당 capture 구간에서 정상 동작한다는 조건 아래의 추정이며 센서 노출 시각 증명이 아니다. [GStreamer clock/segment 문서](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html)

Camera 객체를 새로 만들면 epoch UUID가 새로 생긴다. CLOCK_LOST는 epoch를 바꾸고 중단한다. 자동 reconnect는 추가하지 않았다. Trigger 이후 새 epoch frame은 현 cycle에서 ERROR이며 몰래 재시도하지 않는다. 새 GStreamer segment/clock 경로의 **실제 장치 검증은 NOT_RUN**이고 모의 clock 테스트만 통과했다.

## 선택·거부 규칙

수락에는 `source_estimate > t0 + epsilon`과 `0 <= source_estimate <= received <= select_now`가 필요하다. age는 capture 시 저장된 age가 아니라 `select_now - source_estimate`로 다시 계산한다.

| 사유 | 동작 |
|---|---|
| PRE_TRIGGER | t0 또는 그 이전 추정 source; 폐기 후 창 안에서 다음 frame 대기 |
| STALE | 선택 시 max age 초과; selector는 폐기. Camera의 1초 hard guard 실패는 cycle ERROR |
| DUPLICATE_FRAME | 같은/역행 sequence, 반복 frame_id 또는 같은 PTS; selector는 폐기. Camera 단계 검출은 cycle ERROR |
| PTS_REGRESSION | 이전 관측보다 작은 PTS; cycle ERROR |
| CAMERA_EPOCH_CHANGED | trigger epoch 불일치 또는 clock loss; cycle ERROR |
| DEADLINE_EXCEEDED | 유효 창의 끝 이상; cycle ERROR, 과거 frame fallback 없음 |
| FRAME_METADATA_INVALID | 결측·NaN·잘못된 시각 순서·invalid segment/PTS 등; cycle ERROR |
| CANCELLED | 취소 후 frame/inference 결과 사용 금지 |
| OBSERVATION_SPACING | 기존 multi-observation 간격 미달; 다음 frame 대기 |

선택 결과에는 trigger_id, trigger_to_frame_ms, frame_age_at_select_ms, selection_wait_ms, freshness_basis와 **exposure_time_verified=false**를 연결한다. 거부 metadata는 최근 32개, 이유별 전체 count 및 잘린 개수를 보존한다. 매 frame 이미지는 저장하지 않는다. 최종 선택된 recipe observation 3장과 overlay만 기존 원장 경로로 전달한다. 취소/오류 시 부분 observation 이미지 공개도 하지 않는다.

Candidate lab 값: max frame age 350 ms, observation spacing 150 ms, max_trigger_to_frame_ms와 inspection_window_ms 각각 3000 ms, epsilon 0 ms. 실제 deadline은 두 창과 trigger.deadline 중 가장 이른 값이다. **모든 observation, inference 후, encoding 후를 이 창 안에서 검사**하므로 첫 frame만 fresh이고 나중 observation이 무제한 늦어지는 동작은 없다. 이 값은 기존 3관측 Recipe를 확인할 lab 설정이며 conveyor 속도/간격/위치 측정 전 production 기준이 아니다. Freshness만으로 같은 제품임을 입증하지 않는다.

## Candidate 배치와 보존

새 경로는 `/home/jetson/oned_device_bench/candidates/app_v008_dev_p0_002/`이다. `runtime/`에 소스 32파일, 별도 logs/config/cache를 둔다. `data/candidate_p0_002/`는 생성했지만 비어 있고 DB/inspection/session/event 0이다. 후보 port는 loopback 18768로 설정했으며 실제 listener/API 시작은 0이다. launcher를 실행하면 저장된 Gate C 실패로 app import/DB 생성 전에 중단한다.

`runtime`은 앱 실행 전 소스 snapshot이며 production 배포가 아니다. 최초 배치 후 기존 encode_evidence 호환 보완 1파일을 기존 SHA 일치 확인 후 갱신했다. 최초 inventory와 수정 내역은 보존하고 최종 inventory를 verification JSON에 기록했다. Python 30개는 Jetson Python에서 compile-only 검사했다.

`releases/app_v007`, app_v1 env, earbud package/best.pt, 기존 Jetson DB/assets, PC mirror DB/WAL/SHM/assets, P0-001R candidate 전체 및 사용자 Ultralytics 설정을 전후 SHA256으로 비교한다. `current` symlink를 바꾸지 않는다. 새 camera 프레임 5장은 memory-only, Dataset 저장 0, 기존 승인 이미지 읽기 1회다. 실제 PLC/conveyor/MQTT/systemd/retention/TRT 변환/학습/E04 접근은 0이다.

## 검증과 남은 Gate

합성 필수 12개 시나리오, 실제 Worker의 모의 Camera/Detector 경로, segment clock 변환, clock loss, bounded metadata, trigger admission transaction rollback, PC mirror frame 연결, 별도 SQLite reader의 commit 전 비공개를 확인했다. 기존 Camera/Bench, Worker/Calibration, Service/API, Journal, Mock, PC Sync, Product Package 회귀를 포함해 **102 tests PASS**다.

중간 회귀 102개 중 1개가 기존 합성 frame의 frame_id 부재로 실패했다. Fresh Frame selector는 ID를 필수 검사하고, 기존 encode_evidence 입력은 optional frame_id로 유지해 수정 후 102개를 재실행했다. 최초 실패 로그도 보존한다.

다음 순서는 Gate C의 CUDA allocator 실패 원인 확인 → 동일 환경 범위의 Runtime Gate 재수용 → 실제 local/mock trigger 반복 fresh frame → 기존 모델/recipe + candidate DB 최소 cycle이다. 이번 Task의 C/D가 미검증이므로 **P0-003 실제 장치 성능 검증은 BLOCKED**다. 별도 승인 없이 torch/OpenCV/CUDA 교체나 시간/메모리 우회 설정으로 Gate를 통과시키지 않는다.
