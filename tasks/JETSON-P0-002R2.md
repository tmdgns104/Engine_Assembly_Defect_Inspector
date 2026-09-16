# JETSON-P0-002R2 — Integrated Candidate Runtime Gate Reacceptance

Status: DONE / REACCEPTANCE_PARTIAL_RUNTIME_ERROR_REPRODUCED (2026-09-16). P0-003 실제 장치 진입 BLOCKED.

## 계약

기존 Fresh Frame 소스와 모든 baseline 환경·데이터·실패 evidence를 보존한다. 새 `candidates/app_v008_dev_p0_002_reaccept`, `data/candidate_p0_002_reaccept`, `diagnostics/p0_002r2`만 Jetson 쓰기 대상으로 사용한다. 기존 NumPy overlay는 process-local로 재사용한다. 설치·allocator/전력/시스템 설정 변경, cache 비우기, PLC/conveyor/MQTT/TRT 변환, Dataset 변경, commit/push는 금지한다.

카메라를 연 상태에서 기존 Detector의 승인 이미지 inference와 추가 camera 수신을 같은 process에서 수행한다. 새 process 10개를 순차 실행하고 첫 실패에서 즉시 중단한다. 전부 통과해야 기존 selector의 LOCAL_TEST 10 triggers, 이어서 기존 Detector/Recipe/encode/Journal을 연결한 candidate cycle 1개로 진행한다. 원본 SHA와 current symlink를 전후 비교한다.

## 수용

- A: 기존 102 tests 근거 유지; 소스 변경 여부와 재실행 여부를 명시.
- B: 통합 runtime 10/10만 INTEGRATED_RUNTIME_GATE_REACCEPTED_LAB.
- C: 실제 카메라 fresh frame 10/10, 잘못 선택한 pre-trigger/stale/duplicate/PTS regression/epoch mismatch 0.
- D: candidate raw/overlay SHA와 trigger/frame 연결, SQLite commit 후 local result publication 확인. 물리 배치·calibration 사람 승인을 만들지 않는다. 미확인 view는 기존 Recipe 의미에 따라 REVIEW로 남긴다.
- E: MOVING_CONVEYOR_PHYSICAL_ACCEPTANCE = NOT_RUN.
- B/C/D 모두 통과해야 P0-003_ACTUAL_DEVICE_READY = true. 간헐 오류의 원인이 해결됐다고 주장하지 않는다.

## 산출물

`docs/jetson/JETSON_INTEGRATED_RUNTIME_REACCEPTANCE.md`, `docs/verification/JETSON-P0-002R2.json`, `runs/jetson_p0_002r2/`. 진단 코드만 추가하며 기존 runtime source는 수정하지 않는다. 최종 `git diff --check`와 보호 파일 비교를 수행한다.

## 결과

- A 기존102 tests PASS 유지, source 변경0으로 재실행하지 않음.
- B 통합 cold process10/10 PASS, stderr 오류0. Camera 전후 각5프레임, 동일 epoch, 모델 CPU load/CUDA 이동과 총11 memory stages 확인.
- C 실제 Fresh Frame10/10 PASS. trigger 이전 preview 거부, 잘못된 pre-trigger/stale/duplicate/PTS regression/epoch 선택0.
- D 기능 경로는 PASS: 기존 Recipe3개 fresh frame → REVIEW(물리 view/calibration 미승인) → raw3/overlay1 SHA → 새 SQLite COMPLETE/outbox commit → local publication1. 그러나 해당 process stderr에 NvMap error12가 재현돼 **runtime 수용 FAIL**. NVML assertion/예외 종료는 없었다. raw PASS와 stderr를 그대로 보존했다.
- E conveyor physical acceptance NOT_RUN. P0-003_ACTUAL_DEVICE_READY=false.
- app_v007/app_v1/overlay/기존 candidate/package/model/DB/assets/PC mirror/Fresh Frame source/Ultralytics settings SHA 변경0. 새 candidate32/data7/diagnostics85파일. 소스·환경·기존 evidence 변경0.
- 오류 확인 이후 GPU 재실행·복구0. 정확한 오류 출력 단계는 timestamp 없는 stderr로 확정할 수 없으며 다음 별도 진단 Task가 필요하다. 기능 반환 성공을 오류 없는 runtime 수용으로 간주하지 않는다.
