# JETSON-P0-003 — Candidate latency instrumentation

판정: **LATENCY_INSTRUMENTATION_VERIFIED_LAB** (2026-09-16). 단일 Jetson process PID21354에서 startup/warmup1을 분리하고 warm10 Cycle/30 observations를 측정했다. process 전체19.837초이며 성능 SLA나 장시간 endurance 평가가 아니다. NvMap/NVML/allocator stderr0, Python/CUDA exception0. 이전 NvMap 원인은 **UNCONFIRMED**다.

사용자가 지정한 [ChatGPT 대화](https://chatgpt.com/c/6aa23182-dfe4-83ee-9ab4-be9e20b06b3b)에 R4 결과를 전달한 뒤, 답변의 P0-003 candidate-only 범위를 저장소 소스와 보호 규칙에 대조하여 착수했다. 외부 답변으로 환경/PLC/TRT 변경 권한을 확대하지 않았다.

## 변경 범위와 실제 소스 계약

R2 runtime32파일의 exact copy에서 시작했다. 새 Candidate `candidates/app_v008_dev_p0_003_latency/runtime/src/vision/pytorch_detector.py` 한 파일만 변경했다. Windows 동일 사본/patch controller는 `runs/jetson_p0_003`에 있다. root `src/apps/config/scripts`, 기존 candidate, Fresh Frame, Worker, Recipe, Journal 소스는 변경0이다.

Detector의 선택적 `latency_enabled=False` 인자는 기본 동작과 DetectionResult를 보존한다. 활성화하면 CPU load/기존 `.to(cuda:0)` 구간 timestamp 및 `Results.speed` 복사만 추가한다. 모델/전처리/predict 경로를 재구현하지 않는다. OFF/ON 결과 의미와 기존 두 synchronize 유지 여부를 합성 검증했다.

| 구간 | 확인한 실제 의미 |
|---|---|
| 기존 `inference_ms` | `YOLO.predict()` 전체 + 호출 후 기존 synchronize. 호출 전 synchronize와 뒤의 boxes CPU 변환은 제외한다. |
| `detector_host_total_ms` | `detect()` 전체의 monotonic wall time. 기존 synchronize2회와 CPU 결과 변환 포함. |
| `ultralytics_preprocess_ms` | 설치된8.4.118 predictor의 letterbox/stack/BGR→RGB/BCHW/from_numpy/`.to(device)`/dtype/정규화. H2D 포함. |
| `ultralytics_inference_ms` | predictor.inference profile 구간. 순수 GPU kernel 시간으로 해석하지 않는다. |
| `ultralytics_postprocess_ms` | NMS와 coordinate scaling/Results 구성. |
| `quality_ms` | 실제 Worker 순서대로 detect 다음 `assess_image()` 호출. |
| `evidence_encode_ms` | raw PNG3 + 마지막 frame overlay JPG1의 메모리 인코딩. |
| `persist_total_ms` | `Journal.finish()`의 atomic file write/fsync + SHA/metadata + SQL commit 반환까지. |
| `trigger_to_durable_result_ms` | trigger부터 finish 반환까지. 기존 immutable 결과를 수정하지 않고 sidecar에 남긴다. |
| local publication | commit 확인 후 진단 publication 파일 쓰기 직전 local handoff timestamp. PLC/network ACK나 publication 파일 내구성 지연이 아니다. |

근거 원본은 `runs/jetson_p0_003/runtime/`와 읽기 전용으로 수집한 `upstream/{engine/predictor.py,models/yolo/detect/predict.py,utils/ops.py}`, SHA는 `source_contract.json`에 있다. Ultralytics `ops.Profile`은 자체 perf_counter와 기존 device synchronize를 사용한다. 이 reported duration들을 새 host timer와 합산하지 않는다.

H2D를 독립 관측할 안전한 seam이 없어 `h2d_ms=null`, `NOT_SEPARATELY_OBSERVABLE_WITH_CURRENT_ADAPTER`를 기록했다. pure GPU kernel, 별도 asset write/DB commit, PLC/network ACK는 측정하지 않았다. 모델 CUDA ready 시간은 기존 `.to()` 반환 구간이며 새 synchronize를 넣지 않았다.

## 시계와 표본

새 timestamp는 `time.monotonic_ns()`, `clock=jetson_process_monotonic`. 기존 Frame/Trigger의 monotonic 초 값을 ns로 반올림했으며 selector 지표와0.00001ms 이내 일치를 검증했다. UTC는 duration 계산에 쓰지 않는다.

`trigger_to_source_estimate`, `source_estimate_to_receive`, `trigger_to_receive`, `selection_wait`, `frame_age_at_select`는 이름 그대로 local estimate/수신/선택 경계다. source estimate는 sensor exposure timestamp가 아니며 `exposure_time_verified=false`다. observation2/3의 selection_wait는 같은 Cycle trigger에서부터 누적된 값이다.

startup6개 지표와 warmup1은 `STARTUP_OR_WARMUP`, 실제30 observations/10 cycles만 `MEASURED_WARM`이다. 여기서 warmup 범위는 **MODEL_DETECT_PATH**다. 모델/CUDA detect1회 이후 표본이라는 뜻이며 encoder/DB/filesystem/OS cache나 온도 상태가 모두 안정화되었다는 뜻은 아니다. 원시 record는 변경하지 않고 이 해석을 별도 verification metadata에 기록한다. 표의 분위수는 `(n-1)*p` 선형보간(type7)으로 계산한 작은 lab 표본의 기술 통계다. **production threshold=NOT_DEFINED**.

| 지표 ms | n | min | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|
| detector host total | 30 | 46.861 | 54.075 | 91.272 | 91.569 | 91.676 |
| Ultralytics preprocess (H2D 포함) | 30 | 5.312 | 6.805 | 13.163 | 13.251 | 13.282 |
| Ultralytics inference reported | 30 | 35.947 | 40.759 | 69.960 | 70.198 | 70.283 |
| Ultralytics postprocess reported | 30 | 2.589 | 3.235 | 4.024 | 4.386 | 4.479 |
| quality | 30 | 17.864 | 28.055 | 41.280 | 47.517 | 50.007 |
| evidence encode | 10 | 99.742 | 108.682 | 114.268 | 115.057 | 115.255 |
| persist total | 10 | 124.095 | 126.822 | 197.026 | 239.557 | 250.190 |
| trigger → durable result | 10 | 686.672 | 717.406 | 801.362 | 850.987 | 863.393 |
| trigger → local publish | 10 | 688.194 | 718.976 | 803.138 | 853.027 | 865.499 |

전체 지표/정밀값/null_count는 `remote/latency/latency_summary.json` 및 `.md`에 있다. startup은 import2998.393ms, camera open2289.402ms, package load36.553ms, model construct2245.482ms(그 내부 CUDA 이동141.666ms), warmup detect2541.293ms다. 중첩 지표나 서로 다른 표본의 component p50을 더해 Cycle p50을 설명하지 않는다. 이 Cycle 지연은3 observations와 기존150ms spacing을 포함하므로 컨베이어 속도/제품 간격 기준으로 바로 환산할 수 없다.

## 수집 영향과 오류 처리

`sync_policy=EXISTING_RUNTIME_SYNCHRONIZE_ONLY`, 추가 CUDA synchronize0. 단계 이벤트는 메모리에 모으고 다음 Cycle permission 직전/종료 시 JSONL/stdout에 flush한다. 매 timing point의 disk write/fsync 없음. memory snapshot은 RUNTIME_READY/Cycle END에서만 수집한다. Parent는 stderr를 별도로 실시간 drain하며 첫 marker에 stop flag를 만들고 다음 Cycle을 거부한다. native call은 kill하지 않는다. 종료 후 stderr EOF까지 관측한다.

이벤트 수/JSONL bytes는 `run_manifest.json`에 기록했다. timer/메모리 append/중단 확인 등 계측 오버헤드는 포함될 수 있다. OFF와의 hardware paired 비교를 하지 않았으므로 wall overhead는 **UNMEASURED**다. 지연 최적화나 원래 생산 runtime의 정확한 latency라고 주장하지 않는다. Buffered stage라도 child 시각을 기준으로 stderr pipe 수신과 interval을 연결할 수 있으나 native emission 시각은 아니다.

## 검증과 보존

기존102 회귀 + timing synthetic12 =114 PASS, skip0. 실제 import 경로가 새 Candidate인지 검증했다. collector fragmented stderr/cooperative stop/teardown selftest PASS. 첫 Windows 실행기에는 multiprocessing main guard가 없어 실패했으며 실패 로그를 보존하고 실행기만 수정했다. 실제 장치 실행은1회이며 PASS 채우기 재실행 없음.

10 Cycle 모두 REVIEW(물리 view/calibration 미승인 유지), COMPLETE10/publication10/late0, SQLite integrity ok. raw30/overlay10 =40개 실제 SHA 일치, trigger/frame/asset/inspection ID 연결과 commit-before-publication 검증. camera epoch/잘못된 Fresh Frame 선택0.

독립 검증은 원시 ns duration 재계산, stdlib statistics의 inclusive 분위수 교차검산, JSON/CSV 모든 값·ID, event 순서, candidate 배포 SHA, 보호 SHA를 대조했다. 결과는 `final_checks.json`이다. app_v007/app_v1/NumPy overlay/기존 candidates/package/model/DB/assets/PC mirror/Fresh Frame/이전 diagnostics 등 보호36그룹+overlay/current와 Windows 원본 변경0. 이는 열거한 보호 파일 내용 비교이며 OS background 파일 변경 전체를 의미하지 않는다. git diff --check PASS, commit/push0.

NumPy1.26.4 overlay는 process-local만 재사용했다. OpenCV5 metadata의 NumPy>=2 충돌은 남아 있다. 환경은 production-approved가 아니며 NvMap root cause는 UNCONFIRMED다. physical conveyor acceptance=NOT_RUN.

## 산출물과 재현 경계

- 검증: `docs/verification/JETSON-P0-003.json`, `runs/jetson_p0_003/final_checks.json`.
- 원본: `remote/latency/latency_events.jsonl`, `latency_observations.jsonl`, `latency_cycles.jsonl`, `latency_startup.jsonl`.
- 파생: observation/cycle CSV, summary JSON/MD, run_manifest JSON.
- 새 Jetson runtime/data/diagnostics는 각각 `app_v008_dev_p0_003_latency/runtime`, `candidate_p0_003_latency`, `p0_003_latency`.
- 읽기 검증 재현: `C:/Python313/python.exe -B -X utf8 runs/jetson_p0_003/verify.py`. 합성/회귀: `.venv/Scripts/python.exe -B -X utf8 runs/jetson_p0_003/run_tests.py`.

실제 장치 controller는 기존 evidence/data 경로 재사용을 거부한다. 반복 측정은 별도 Task/새 경로로 정해야 한다. P0-004/TensorRT 구현·변환은 자동으로 시작하지 않는다.

## 지정 대화 결과 리뷰 반영

P0-003 결과를 같은 대화에 다시 전달하고 리뷰를 확인했다. 수용 판정 유지에 동의했으며 추가 장치 실행은 하지 않았다. 원시 evidence와 측정 소스를 동결하고 다음 해석만 명확히 했다.

- 기존 `inference_ms`는 **legacy detector timing**이며 pure GPU kernel 지표가 아니다.
- `MEASURED_WARM`은 모델 detect 경로 warmup 이후 표본이다. 전체 시스템 안정화 주장이 아니다.
- persist의 atomic은 개별 파일 저장 함수의 성질이다. **파일시스템 asset 저장과 SQLite commit 전체가 하나의 원자적 transaction은 아니다.** asset 저장/fsync/SHA 후 SQL commit, 그 후 반환·공개 순서만 검증했다.
- local publish는 diagnostic handoff다. PLC/network ACK는 측정하지 않았다.

리뷰는 전달한 실행 결과에 대한 외부 의견이며 코드/장치를 독립 검증한 증거로 세지 않는다. 실제 수용 근거는 저장소 원시 결과와 독립 재계산이다. 후속 Task 실행 없이 결과를 동결한다.
