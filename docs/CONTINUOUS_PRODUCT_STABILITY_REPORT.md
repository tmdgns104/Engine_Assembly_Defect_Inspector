# 연속 제품 접수 안정화 — 실제 6회 확인

2026-10-15. 구현·배포 후 감독하 연속6회 처리 경로를 검증했다. 최초 START 한 번 뒤 **정상 → 왼쪽 파이프 결품 → 정상 → 오른쪽 파이프 결품 → 정상 → 문양 결품**을 처리했다. 여섯 번째는 사용자가 현장에서 추가 요청했다. 이 6회 사이에 Reset, STOP/START, 소프트웨어 권한 발급, 서비스 재시작은 없었다. 작업자가 각 LED·재가동과 마지막 STOP을 확인했다. 다만 시험 종료 후 장시간 STOP 대기에서 카메라 수신 timeout/Worker 재기동이 발견됐으므로 현재 준비 상태와 6회 성공을 구분한다.

## 실제 원인과 수정 범위

이전 운영 요청10·11은 `PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN`으로 30초 후 종료됐고 실제 AI 원본은 0장이었다. 당시 최초 bbox는 제한 링에서 이미 덮여 **과거 두 건의 최초 물리 관측 원인은 확정할 수 없다**. 다음 코드 결함은 기존 구현의 실패와 수정 후 통과를 재현했다.

1. 새 upstream 제품을 본 뒤 짧은 프레임/검출 누락이 생기면 신규 진입 문맥을 지웠다. 이후 관측을 이전 제품의 배출 bbox와 비교해 영구 invalid로 만들었다. 기존 Track의 누락·시간·공간 한계 안에서 동일 진입 문맥을 유지하고, 연속 증거 창은 다시 시작한다. 누락 자체는 이탈 근거가 아니다.
2. 신규 Request가 분리 근거 확정보다 먼저 올라오면, 이미 관찰한 이전 Request LOW·출력 초기화 대신 **현재 Request LOW**를 다시 요구했다. 아직 검사 미할당인 동일 요청만, 요청 이전에 관찰된 진입과 같은 epoch/generation/연결·이전 트랜잭션 종료 근거가 맞을 때 해소한다. 늦게 들어온 다른 제품·기한 만료·STOP·통신/저장 오류는 통과시키지 않는다.
3. 최초 실패 전후를 보존하려고 추가한 상세 소비 프레임 진단이 Runtime 잠금 안에서 큰 복사를 수행했다. 첫 현장 시도는 PASS/FAIL/PASS 완료 후 유휴 중 health 423.689ms, `HEALTH_LEASE_EXPIRED`로 차단됐다. 당시 Class1 연결1/timeout0, IPC snapshot age44.86ms였다. 기록 참조만 잠금 안에서 잡고 불변 기록의 큰 복사를 잠금 밖으로 옮겼다. 이 결함도 제어 잠금 회귀에서 수정 전 FAIL/수정 후 PASS를 확인했다.

수정 함수/파일:

- `jetson/src/runtime/product_passage.py`: `_observe_entry()`, `observe()`, `status()` — 제한된 진입 재관측과 실제 증거 상태.
- `jetson/src/runtime/standalone.py`: 이전 settled 상태 보존, `_pending_entry_matches_request()` 및 `_observation_hold()`의 동일 요청 재검증, `consumed_frame_snapshot()`의 잠금 범위 분리.
- `jetson/src/runtime/consumed_frames.py`: 실제 Runtime 소비 링1024개·최초 실패 체크포인트4×128, `capture()`/`copy_snapshot()`.
- `jetson/src/runtime/standalone_web.py`: 정상 이전 제품 관찰과 실제 새 요청 미실행 문구 구분. UI 디자인 변경 없음.
- `notebook/tests/test_continuous_product_stability.py`: 짧은 누락·Request 경합·늦은 제품/epoch/STOP/연결/저장/기한·진단 잠금 회귀.

PLC·EDS·4/8/10B·C 바이너리·모델·임계값·카메라 배치·RPI/timeout/lease·판정 정책은 변경하지 않았다. 과거 검사 원본/판정/ABORTED/승인 원장은 보존했다. 정상 제품 사이에는 유지보수 복구를 호출하지 않았다.

## 검증 결과

집중 PC **144/144**, Jetson ARM64 **144/144** 통과. 기존 실제 bbox 너비 이상 재생, 제품 구분 근거 부족·중복 요청/출력·epoch/STOP/통신/저장 보호를 포함한다. 신규 gap/Request 재현은 격리 입력이며 과거 실패 프레임 자체를 복원한 것으로 주장하지 않는다.

현장 6회는 같은 서비스 PID16809, Camera Worker16852, Assembly16830, OpENer16826, C boot `29564594ce31fe35`·connection1을 유지했다. Request 번호2~7은 앞선 별도 접촉 시험1을 제외한 이번 연속 구간이다.

|순서|실물|기본/최종|검사 ID|Request→Result|Result→Done 패킷|
|---|---|---|---|---:|---|
|1|정상|PASS/PASS|a3848cc356c24c1e8f29d3d1446b26c0|9.233초|10331→10332|
|2|왼쪽 파이프 결품|FAIL/FAIL|64a6f0d135534ebca841971ae584105f|9.430초|11660→11661|
|3|정상 복원|PASS/PASS|d31450e2a6804acc8ae662453cd75562|9.279초|13151→13152|
|4|오른쪽 파이프 결품|FAIL/FAIL|9b60f3a8cb4d48789e52ae5711125475|9.882초|14411→14412|
|5|정상 복원|PASS/PASS|3f17179b2bf041d3b76ae61991a0c910|9.132초|15678→15679|
|6|문양 결품|FAIL/FAIL|fbca6d7da0b8480194ffdc5420dd638a|7.633초|16762→16763|

- 각 검사 새 원본3장, 총18장의 PNG SHA·입력 픽셀 SHA·frame ID/epoch/generation/PTS 확인. 모든 frame에서 실제 Pose·slot 할당 유효. 결품 이유는 각각 `LEFT_PIPE_MISSING`, `RIGHT_PIPE_MISSING`, `SYMBOL_MODULE_MISSING`이다.
- Journal COMPLETE → 최종판정 저장 → Result-only → 다음 패킷 Done → Request 해제 → 출력0/transaction settled. 동일 요청 중복 Result/Done 없음.
- 2~6번째는 이전 outbound 궤적과 실제 새 upstream 진입으로 구분했다. 빈 화면·시간 경과·Request LOW를 제품 분리 증거로 만들지 않았다. 전체 물리 이탈/Area CLEAR를 주장하지 않는 기존 증거 계약이다.
- 실제 LED·재가동은 현장 작업자 확인이다. cyclic 전송+요청 해제와 별도의 PLC 내부 결과 소비 태그 검증은 구분한다. 독립 PLC 로직 동등성은 미검증이다.
- 원본 저장 commit 293~534ms 중 health 유지. 연속 구간 health 최대380.371ms, 기록된 ready=false 없음. C timeout0/opens1. lease 확대 없음. 400ms 조건 대비 여유가 작아 장시간·다른 부하 안정성은 추가 검증 대상이다.
- 최종 STOP: Mc_Run/Request OFF, raw100=00000000, Worker IDLE, 저장/Assembly/final 작업0, SQLite integrity ok, 운영185파일 SHA 일치.

## 실패·복구 기록의 구분

- 첫 배포의 카메라 timeout은 직전 코드로 복원해도 지속됐다. 사용자 USB 재연결 뒤 복구됐고 동일 검증본을 다시 적용했다. 카메라 문제를 소프트웨어 수정으로 해결했다고 주장하지 않는다.
- 첫 연속 시도는 3회 완료 후 진단 잠금 health 결함으로 종료. 위 6회 성공에 합산하지 않는다.
- 다음 시도 첫 제품 PASS 후 배출 bbox 오른쪽 끝이 약223→440px로 되돌아왔다. 사용자가 배출 중 모형을 잡으려다 벨트를 밀었다고 확인했다. 실제 몸체 이동인지 손 포함 검출인지는 bbox만으로 확정 불가. **이 한 건에만** 물리 개입을 기록하며 과거 코드 오류에 적용하지 않는다. 이때 코드는 추가 변경하지 않았다.
- 각 중단 후 현재 STOP·실물 벨트 밖·무출력·유휴 확인을 받고 기존 유지보수 문맥 종료만 수행했다. 가짜 CLEAR/최종판정/결과 재전송은 없었다. 최종 6회 구간에는 복구 명령0회다.

## 운영본과 복원

- 소스 commit: `a859b21e00b2d1f661b27e301f4705be74273d04` (첫 상태 전이 수정 `d376ffcf0c26a7b2a06c020c56304df7bac3a567` 포함).
- 실제 Release: `engine-integrated-80882c05c181fbd6`, `INTEGRATED_AI_OFFLINE`, 185파일. Python·모델/Pose·HTML/JS·OpENer 자산 유지.
- 최종 패키지 SHA: `d91edb124bbee920745b0161edca3c45c4946d35afe5f8273f65e86ed3802dea`.
- C SHA 유지: `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4`.
- 직전 운영본/설정/unit/일관 SQLite 노트북 백업170파일 SHA 검증: `1ff338bdcea76b13eaef7a229ca3b7f802c12f860a05f91d9d3158e77e0eb1c5`.
- 복원은 실제 STOP·무출력·유휴 확인 → 서비스 정상 종료 → 검증된 백업의 코드/설정/unit 복원 → 기동·SHA/단일 소유 확인 순서다. 최신 Journal/PNG/ABORTED/승인 소비 기록은 되돌리지 않는다. 직전 a390 버전에는 진단 잠금 결함이 있으므로 복원은 ‘직전 상태 복원’이지 정상 운전 보장이 아니다.

비공개 노트북 증거: `runs/continuous_stability_001/VERIFIED_SIX_TRIALS.json`, `OPERATOR_CONFIRMATIONS.json`, `FIVE_TRIALS_03/`, `FIVE_CYCLES_03/STATUS.jsonl`, `FINAL_STOP/`, `diagnostic_lock/`. 운영 DB·사진·개인 설정·인증정보는 Git에 올리지 않는다.

## 남은 한계

종료 뒤 추가 확인에서 `CameraError: CAMERA_FRAME_TIMEOUT` → 기존 자동 카메라 복구 → camera epoch/Worker 교체가 반복됐다. main service/C 연결은 유지되고 새 Request/Result/Done은 없었다. 이때 과거 제품 문맥은 `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`으로 보수적으로 복원됐다. 6회 시험 동안 동일 Worker로 처리한 사실과 구분한다. 이 카메라 수신 문제는 원래 코드 복원 때도 관측됐으며 USB/드라이버/수집 경로 중 정확한 최초 원인은 미확정이다. 현재 보호 조건을 해제하거나 가짜 이탈로 복구하지 않는다.

감독하 이 배치·간격의 6회 연속 처리를 검증했다. 미관측 진입, 큰 역행/가림, epoch 변화, 실제 통신/저장 장애에서 임의로 다음 제품을 정상으로 확정하지 않는다. 장시간 Class1·health 여유, 무인 장애 복구, 다양한 투입 간격/각도와 모델 정확도는 완료 주장에 포함하지 않는다. Assembly는 여전히 공간 지지 부족 REVIEW이며 기존 V1 기본검사·확정 FAIL 정책으로 최종 PASS/FAIL을 만들었다. 조립 정렬을 고친 작업이 아니다. 다음 UI/DB 작업은 시작하지 않았다.
