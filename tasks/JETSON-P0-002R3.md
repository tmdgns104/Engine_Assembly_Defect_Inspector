# JETSON-P0-002R3 — NvMap Exact-Stage Isolation

Status: DONE / NVMAP_NOT_REPRODUCED_IN_BOUNDED_STAIRCASE (2026-09-16). ROOT_CAUSE_UNCONFIRMED / P0-003 BLOCKED.

원본 환경·runtime·camera 설정·데이터·이전 evidence를 보존하는 진단이다. 새 `diagnostics/p0_002r3_nvmap` 안에만 Jetson 파일과 Case H용 일회성 Journal을 만든다. 기존 R2 candidate source를 읽어 사용하고 변경하지 않는다. process-local NumPy overlay와 config/cache 격리만 유지하며 설치·allocator/시스템 변경·PLC·MQTT·conveyor·commit/push는 금지한다.

Parent가 stderr pipe를 실시간 읽어 Jetson monotonic 수신 시각을 JSONL로 저장한다. Child는 각 stage의 monotonic·host/CUDA memory를 flush한다. 종료 직전 marker 이후에도 pipe EOF와 process exit까지 수집한다. pipe 수신 시각은 native emission 시각이 아니므로 인접 stage interval로만 분류한다.

A camera5frames → B construct → C warmup → D fresh detect1 → E fresh detect3 → F Recipe → G encode → H 새 Journal/commit/local publication을 새 process로 순차 실행한다. 첫 stderr NvMap/NVML_SUCCESS/CUDACachingAllocator 또는 실행 실패 후 다음 Case를 시작하지 않는다. 모두 clean이면 H 조건을 최대5회 추가 반복한다. 같은 Case 재시도로 PASS를 채우지 않는다.

성공은 NVMAP_STAGE_INTERVAL_IDENTIFIED 또는 NVMAP_NOT_REPRODUCED_IN_BOUNDED_STAIRCASE. 물리 원인은 증거 없으면 ROOT_CAUSE_UNCONFIRMED. P0-003은 계속 BLOCKED.

산출물: `docs/jetson/JETSON_NVMAP_STAGE_DIAGNOSIS.md`, `docs/verification/JETSON-P0-002R3.json`, `runs/jetson_p0_002r3/`. 원본 전후 SHA, 진단 collector 합성 검증, 결과 대조와 git diff --check를 수행한다.

## 결과

- A~H 각1회 + H 추가5회 = 13개 새 process 모두 exit0, stderr0. 최초 NvMap Case/interval은 관측되지 않았다.
- 456 stage events, warmup11/fresh detect28회. Camera close/Journal close/BEFORE_PROCESS_EXIT 이후 EOF·process exit까지 수집했다.
- Recipe/encode/Journal 추가 조합에서도 재현되지 않았다. Model-only는 이번 NOT_RUN, 이전 진단을 현재 대조군으로 과장하지 않는다.
- MemAvailable1,786,848–3,034,204kB/CmaFree0–43,980kB. 오류 직전 값은 N/A. Python exception/NVML assertion0.
- collector 분할 line·atexit synthetic test PASS. 원본 Jetson 보호33그룹/overlay/current와 Windows source/PC mirror/이전 evidence 동일.
- 기존 코드·환경·카메라 설정 변경0. H의 새 DB/assets는 diagnostics subfolder에만 저장. 102 기존 tests는 source 변경0으로 재실행하지 않음.
- 재현되지 않았다는 관측만 수용한다. 원인 해결·production acceptance·P0-003 준비 완료로 표시하지 않는다. 추가 복구/수용 Task는 별도 결정한다.
