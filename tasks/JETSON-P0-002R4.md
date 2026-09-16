# JETSON-P0-002R4 — Long-Lived Integrated Runtime Soak

Status: DONE / LONG_LIVED_RUNTIME_STABILITY_PASS_LAB (2026-09-16). P0_003_ACTUAL_DEVICE_READY=true, latency instrumentation 한정.

단일 process에서 Camera/Detector/CUDA/Journal/session을 한 번만 초기화하고 full cycle30개를 연속 수행한다. R2 runtime source, 기존 package/model과 NumPy overlay를 읽기만 한다. 새 Jetson 쓰기는 `diagnostics/p0_002r4_soak`와 `data/candidate_p0_002r4_soak`로 제한한다. 기존 환경·source·이전 evidence·사용자 변경을 보존하고 설치/allocator/GC/cache 비우기/시스템 설정/PLC/MQTT/conveyor/commit/push는 금지한다.

cycle/request1..30, 새 trigger UUID, 한 session/epoch, 기존3 fresh observations/Recipe/encode/Journal commit/local publication을 검증한다. view/calibration은 미승인으로 REVIEW를 유지한다. Parent는 stderr를 EOF까지 실시간 수집하고 대상 marker를 관측하면 stop flag와 cycle 시작 handshake로 후속 cycle을 차단한다. 현재 native call을 kill하지 않고 제어가 돌아온 뒤 증거를 보존하고 닫는다. 재실행으로 PASS 수를 채우지 않는다.

30/30 clean + DB integrity/COMPLETE30/publication30/assets120 SHA·연결/fresh metadata/epoch 검증이 모두 통과해야 LONG_LIVED_RUNTIME_STABILITY_PASS_LAB 및 P0_003_ACTUAL_DEVICE_READY=true다. production acceptance 또는 root cause resolved가 아니다. 오류 시 이후 cycle 중단, 최초 interval·memory·DB/asset 상태를 남긴다.

산출물: `docs/jetson/JETSON_LONG_LIVED_RUNTIME_SOAK.md`, `docs/verification/JETSON-P0-002R4.json`, `runs/jetson_p0_002r4/`. 시작/종료 SHA, collector 협조 중단 합성 시험, 결과 대조, git diff --check를 수행한다.

## 결과

- 단일 PID20883, Camera/Detector/CUDA/Journal/session 각1회 초기화. 30/30 full cycles, warmup1/fresh detect90회, stage647개. process 전체35.803초이며 장시간 endurance 보증이 아니다.
- stderr0, Python/CUDA exception0, epoch 변경/잘못된 fresh 선택0. 최초 오류 cycle/interval은 N/A.
- SQLite integrity ok, COMPLETE30/고유 inspection·request·cycle30, publication30/late0. raw90+overlay30 SHA120개 및 ID·commit-before-publication 연결 PASS. Recipe는 미승인 view에 따라 모두 REVIEW.
- MemAvailable2,179,752→2,177,436kB, CUDA allocated12,142,592→12,142,080B/reserved60,817,408→60,817,408B. 이 값만으로 leak 여부를 확정하지 않는다.
- candidate data48,873,576B, DB1,314,816B. 보호34그룹/overlay/current 및 Windows source·PC mirror·이전 evidence SHA 변경0. 기존 runtime 변경·환경교체·강제GC/empty_cache·commit/push0.
- P0-003 latency instrumentation 준비만 수용. ROOT_CAUSE_UNCONFIRMED, production 및 physical conveyor acceptance는 아니다.
