# JETSON-P0-003 — Latency Instrumentation

Status: **DONE / LATENCY_INSTRUMENTATION_VERIFIED_LAB**. 선행: P0-002R4 lab gate PASS. P0-004 자동 착수 금지.

## 완료 결과

- 새 Candidate Detector1파일에 optional latency metadata만 추가. 기존 root/source/36그룹 보호 파일/overlay/current/PC mirror/이전 evidence 변경0.
- 기존102 + timing12 =114 tests PASS, collector fail-stop selftest PASS. 첫 Windows test runner main guard 오류는 실행기만 수정하고 실패 증거를 보존했다.
- Jetson PID21354, 단일 process19.837초, warmup1/measured10 cycles/30 observations. REVIEW10, DB integrity ok/COMPLETE10/publication10/late0, raw30+overlay10 SHA40개 PASS.
- monotonic_ns, 기존 synchronize만 사용/추가0. Ultralytics reported timings 별도 보존, H2D null. warmup은 분위수에서 제외, production threshold NOT_DEFINED.
- detector host n30/min46.861/p5054.075/p9591.272/p9991.569/max91.676ms. trigger→durable n10/min686.672/p50717.406/p95801.362/p99850.987/max863.393ms.
- NvMap/NVML/allocator/Python/CUDA exception0, camera epoch 변화/invalid selection0. ROOT_CAUSE_UNCONFIRMED, Conveyor NOT_RUN.
- raw/CSV/summary 독립 교차검증1128 checks PASS. git diff --check PASS, commit/push0.

문서: `docs/jetson/JETSON_LATENCY_INSTRUMENTATION.md`; 검증: `docs/verification/JETSON-P0-003.json`; raw: `runs/jetson_p0_003/remote/latency/`.

## 2026-09-16 착수 계약

사용자의 지정 ChatGPT 대화 결과 공유·계속 진행 요청에 따라 R4 결과를 전달하고 다음 P0-003 범위를 검토했다. 협의 출처: https://chatgpt.com/c/6aa23182-dfe4-83ee-9ab4-be9e20b06b3b. 아래 계약이 이전 예정 범위를 구체화한다. 외부 답변은 환경 변경 권한을 추가하지 않는다.

- R2 runtime exact copy로 새 `candidates/app_v008_dev_p0_003_latency/runtime`만 수정한다. Windows root runtime/기존 Jetson candidate/환경/package/DB/assets/PC mirror/이전 evidence는 보존한다.
- 기존 Detector 반환 계약과 두 CUDA synchronize를 유지한다. 선택적 `latency_enabled`에서 모델 이동 timestamp와 `Results.speed` 복사만 추가한다. 별도 harness가 host monotonic timestamp를 기록한다.
- H2D는 Ultralytics preprocess 내부이므로 독립값 null. upstream profiling은 기존 device synchronization을 포함한 host timer이며 순수 GPU kernel 시간으로 부르지 않는다.
- startup/warmup1과 measured warm 10 cycles ×3 observations를 분리한다. Recipe REVIEW 의미, fresh frame/commit-before-local-publication 계약을 유지한다.
- 단계 이벤트는 메모리에 수집해 Cycle 경계와 종료 시 flush한다. 추가 CUDA synchronize/매 단계 fsync/설정 변경 없음.
- JSONL 원본 → CSV → type-7 linear quantile summary. observation n30/cycle n10을 분리하고 null/INVALID를 보존한다. 생산 threshold 없음.
- synthetic + candidate 대상 기존102 회귀 + parent cooperative-stop selftest가 PASS한 뒤 실제 장치 1 process 실행. NvMap/NVML/allocator 관측 시 다음 Cycle 차단, 재실행으로 PASS 채우기 금지.
- 새 data/diagnostics는 `candidate_p0_003_latency`/`p0_003_latency`, Windows raw는 `runs/jetson_p0_003`. 전후 보호 SHA/DB/assets/CSV 통계/원본 보존 및 git diff --check로 판정한다.

산출물: `docs/jetson/JETSON_LATENCY_INSTRUMENTATION.md`, `docs/verification/JETSON-P0-003.json`, 이 Task 및 raw/CSV/summary/manifest. PLC/network ACK, production SLA, 최적화, TRT/모델 학습/환경 교체/commit/push는 범위 밖이다.

## 문제와 목표

기존 detector/worker/durable-result 시간은 존재하지만 시작점과 포함 단계가 다르다. P0-002 trigger/frame 계약을 바탕으로 지연을 같은 시계·같은 ID로 추적하여 병목을 분리한다. 현재 app_v007의 `inference_ms`는 Ultralytics predict 전체 호출이며 순수 GPU kernel 시간으로 재명명하지 않는다.

## 이전 초안 (범위 이력; 위 착수 계약 우선)

- trigger 수신, journal admit, frame 선택/age, preprocess, H2D, infer, postprocess/NMS, evidence encode, file 저장, DB commit, result 공개/소비, PC event/asset ACK를 구별한다. backend가 내부 구간을 노출하지 않으면 측정 불가/포함 범위를 표시한다.
- Jetson 단조 시계로 local duration을 계산하고 PC/PLC와 UTC 차감으로 network latency를 만들지 않는다. 클라이언트 왕복과 peer 관측은 별도 지표다.
- 기존 원결과는 불변으로 유지하고 새로운 별도 event/선택 필드의 호환성을 검토한다. 오류/취소/timeout에도 부분 trace와 이유를 남긴다.
- 계측 허용 오버헤드·성능 목표·반복 수·입력/배치/clock 설정은 착수 시 고정한다. 무근거 수치 목표를 추가하지 않는다.

## 수용 초안

합성 clock으로 단계 순서·누락/음수 duration·ID 혼합을 검사하고, commit 이전 시간을 end-to-end 완료로 표시하지 않는지 확인한다. 같은 대표 workload에서 cold start/first request와 warm 반복을 분리하고 n/P50/P95/P99·분위수 계산법·오버헤드·메모리/동기화를 기록한다. 측정 전후 원본/모델/DB보존과 기존 회귀를 확인한다. 단일 timing으로 TensorRT 속도 향상을 주장하지 않는다.

산출물 예정: 후보 계측 코드/집중 검증, 지표 사전과 재현 명령, `docs/verification/JETSON-P0-003.json`. app_v007 수정·새 모델·PLC 제어·MQTT·배포는 이 초안으로 시작하지 않는다.
