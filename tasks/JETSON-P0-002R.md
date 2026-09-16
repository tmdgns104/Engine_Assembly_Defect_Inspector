# JETSON-P0-002R — CUDA Allocator Gate C Root Cause Isolation

Status: **DONE / FAILURE_NOT_REPRODUCED_WITH_CONTROLLED_EVIDENCE** (2026-09-16). 분류: **CASE G — INTERMITTENT / ROOT_CAUSE_UNCONFIRMED**.

## 실행 계약

목표는 패키지 복구가 아니라 최초 CUDA 실패 경계를 확인하는 것이다. P0-002의 102 tests, Camera Gate B와 실제 Detector warmup 실패를 기준으로 삼는다. Fresh Frame 소스와 기존 app_v007/app_v1/사용자 패키지/제품/모델/DB/assets/P0-001R overlay/P0-002 candidate는 변경하지 않는다.

새 진단 경로 `diagnostics/p0_002r_cuda/`만 사용하며 테스트마다 새 Python process를 실행한다. NumPy overlay는 process-local이다. 설정/cache/log는 새 경로 아래로 격리한다. CUDA allocator/NVML 설정, empty_cache, batch/imgsz 축소, 재부팅, 전력/CMA/swap 변경, 프로세스 강제 정리, 패키지 설치·교체는 하지 않는다. camera를 다시 열지 않으며 PLC/MQTT/TRT 변환/Dataset/commit/push/reset/clean도 금지한다.

## 순서와 수용

원본 SHA와 import 전 시스템 상태 → CPU tensor → 작은 CUDA allocation → 640 FP32 입력 → 16/32/64/128/256 MiB 각각 새 process → elementwise/matrix → CPU Conv → CUDA Conv → 모델 SHA/CPU load/구조/CUDA move/640 warmup → 선행 Conv·raw model PASS일 때만 Ultralytics 단계 → project adapter.

각 단계 전후 /proc/meminfo와 CUDA allocated/reserved/peak 및 mem_get_info를 기록한다. CPU-only 단계는 CUDA query도 수행하지 않는다. 실패 후 같은 process에서 테스트를 이어가지 않는다. 큰 allocation은 첫 실패에서 중단한다. 상위 검증의 선결 조건 실패는 NOT_RUN이며 독립적인 CPU model load/정적 NVML 조사·보존 검증은 계속한다.

성공은 FIRST_FAILURE_BOUNDARY_IDENTIFIED 또는 FAILURE_NOT_REPRODUCED_WITH_CONTROLLED_EVIDENCE다. 사용자 Case A~G 분류를 증거에 맞게 사용하고 물리 원인은 별도로 확정/미확정으로 남긴다. 최종 원본 보존, 산출물 일관성 및 git diff --check를 확인한다.

산출물: `docs/jetson/JETSON_CUDA_ALLOCATOR_DIAGNOSIS.md`, `docs/verification/JETSON-P0-002R.json`, 이 Task. Raw evidence: `runs/jetson_p0_002r/`.

## 결과

- 새 process 23개, CPU tensor / CUDA 1원소 / 640 FP32 / 16–256 MiB ladder / elementwise / matrix / CPU·CUDA Conv2d / model SHA·CPU load·구조·CUDA move·raw640 warmup / Ultralytics CPU·CUDA·zero·승인 이미지 / 기존 PyTorchDetector 모두 PASS. 최초 실패 단계·크기는 관측되지 않았다.
- Detector는 `[1,3,640,640]`와 3 detections를 반환했다. 실제 camera/Recipe/DB cycle은 0이며 정확도 수용이 아니다.
- case 관측 MemAvailable 3,298,252–4,200,456 kB, CmaFree 0–32,152 kB. CmaFree 0에서도 allocation 및 Detector PASS. 값만으로 원인을 확정하지 않는다.
- NVML 초기화/개수/handle 조회 성공, compute-process query는 Not Supported(3). upstream의 같은 assertion은 allocation-failure memory reporting 경로에 있지만 설치 binary line1131과 upstream line1063 차이로 exact 대응은 미검증이다.
- 원본 Jetson 보호 경로·P0-001R overlay·P0-002 candidate·Fresh Frame 코드 변경 0. 새 diagnostics 87파일만 생성했다. Windows의 진단 외 문서 `tasks/engine-dataset-codex-support.md` 해시 변경은 별도 기록·보존했다.
- 기존 102 tests는 변경이 없어 재실행하지 않았다. 23개 실제 분리 진단과 결과/보존/문서 검사, git diff --check로 검증한다. 환경 복구 변경·commit/push 없음.

## 해석과 다음 Task

새 process, 별도 config/cache, CUDA memory query를 먼저 수행하는 통제 조건에서는 재현되지 않았다. 단발 통과는 원래 camera/import/model 복합 process의 장애 해결 증거가 아니다. P0-002 actual Fresh Frame은 BLOCKED로 유지하며, 별도 Runtime Gate 재현·재수용 Task가 필요하다. 추가 실패 근거 없이 패키지 교체 또는 allocator 우회를 복구 방식으로 확정하지 않는다.
