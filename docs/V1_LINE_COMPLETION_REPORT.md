# V1 판정·복구·실물 검사

2026-10-15 최신 상태: **제품 추적 수정본에서 START 한 번으로 왼쪽 파이프·오른쪽 파이프·문양·문양 재시험 네 사이클을 중간 STOP/START·Reset 없이 처리했다.** 왼쪽·오른쪽·문양 재시험은 실제 세 프레임의 해당 결품으로 최종 FAIL, NG→다음 cyclic Done·요청 해제·불량 LED·재가동을 확인했다. 첫 문양 시험은 한 프레임 엔진 검출 점수 부족으로 FAIL이어서 결품 확정과 구분한다. 현재 STOP·무출력·검사/저장 유휴다. 장기 무인 운전·오조립 정렬 완성으로 확대하지 않는다.

## 최신 추가 결품·자동 반복 현장 검증

운영 Release `engine-integrated-32d132a4256d4ef8`, 소스 commit `7ec9d25e204f60a0e2ec7825f1d1560968510611`. 변경한 운영 파일은 `src/runtime/product_passage.py` 하나(SHA `a25c74e0c6ea6a539066453509a0a51f4dba93d408d309ad1126d4157a66428f`)이며 Release 메타데이터를 일치시켰다. C SHA `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4`, 모델·임계값·PLC·현장 설정은 유지했다. 실제 185파일 SHA가 일치한다.

기존 추적은 상자 폭 변화가 한 프레임 한도를 넘으면 영구 invalid가 됐다. 새 구현은 폭만 이상한 관측을 근거에서 제외하고 마지막 신뢰 상자에서 기존 Track의 시간/누락 한도 내 재관측한다. 역방향·불연속·다중 물체·품질/epoch 오류는 유지한다. 재현133프레임과 집중 PC125/ARM64125 회귀를 통과한 후 실제 적용했다. 허용 폭·시간을 늘리거나 검출 누락을 제품 이탈로 바꾸지 않았다.

|실물 조건|새 검사 ID|기본 / 최종 및 실제 사유|Result→Done|요청→Result|
|---|---|---|---|---|
|왼쪽 파이프만 제거|a489d5fa39114100afd2fbc1646d9247|FAIL / FAIL, LEFT_PIPE_MISSING|NG 6954→6955|9.690초|
|왼쪽 복원·오른쪽만 제거|5d1aa003d63c43faa953e331c66f6abf|FAIL / FAIL, RIGHT_PIPE_MISSING|NG 8972→8973|9.186초|
|오른쪽 복원·문양만 제거|86131de3e5e343c98ab1b62065b6e5b7|FAIL / FAIL, PRODUCT_ENVELOPE_NOT_FOUND|NG 10406→10407|6.741초|
|동일 문양 결품 추가 재투입|caabb4cb02164db09e2019c9f711c922|FAIL / FAIL, SYMBOL_MODULE_MISSING|NG 13009→13010|8.982초|

각각 실제 새 원본3장(총12장), PNG/픽셀 SHA, frame ID/PTS/epoch/generation, Journal COMPLETE와 통합 final, C 요청 token 및 단일 Result/다음 Done/요청 해제/출력 초기화를 검증했다. 사용자는 네 번 모두 불량 LED·재가동, 중간 STOP/START·Reset 없음, 마지막 실제 STOP을 확인했다. 카메라 Worker12135·Assembly12113·service12092·C12109/연결1이 유지됐고 Class1 timeout0, 서비스 재시작0이다. 소프트웨어 결과 소비 근거는 cyclic 송신과 Request 해제이며 물리 LED/재가동 확인과 별도로 표기한다.

두 번째~네 번째 final에는 직전 검사 ID/token을 가리키는 `OUTBOUND_PRODUCT_AND_NEW_UPSTREAM_ENTRY`가 있다. 실제 이전 이송과 구별되는 상류 진입 연속 프레임을 사용하며 전체 화면 비움, 포토센서 원신호 또는 완전 이탈을 주장하지 않는다. 최초 옛 문맥9aeab7d7만 사용자의 STOP·모형 벨트 밖 보관 확인으로 유지보수 종료했으며 네 새 검사 사이에는 문맥 복구·소프트웨어 권한·CLI 준비 명령을 수행하지 않았다.

### 첫 문양 시험의 한계

첫 원본의 엔진 전체 점수0.484223이 기존0.5 기준보다 낮아 pose/부품 검사를 실행하지 않았다. 나머지 두 원본은0.513172/0.592260으로 엔진 검출·pose·슬롯 할당이 유효했고 문양 MISSING, 나머지 세 부품 PRESENT였다. `aggregate_three()`의 기존 제품 미검출 우선 분기 때문에 최종 사유는 PRODUCT_ENVELOPE_NOT_FOUND다. 이 첫 시험을 세 프레임 문양 결품 성공으로 세지 않는다. 추가 재시험에서 세 프레임 모두 문양 MISSING을 확인했으나 한 번의 재시험으로 검출 안정성 문제까지 해결됐다고 하지 않는다. 모델/기준/원본 판정 변경 없음. 네 건의 오조립 참고 분석은 REVIEW이므로 오조립 정렬 해결도 아니다.

### 저장·통신·복원 근거

471개 상태 표본과 실제 Runtime 소비 프레임을 노트북에 보존했다. 네 raw 저장 commit은277.46/421.25/281.98/292.83ms, 시험 구간 bounded 진단의 health 갱신 최대255.45ms, ready=false 없음. 기동~최종 전체 범위 health 최대388.86ms(시험 이전 문맥 종료 구간), IPC snapshot 최대125.90ms이며 서로 다른 범위다. 1Hz HTTP 표본의 IPC 관측 최대54.51ms를 실제 전체 IPC 최대라고 해석하지 않는다. 장기 Class1·통신/카메라 장애복구는 이번 유한 시험의 검증 범위 밖이다.

노트북 직전 운영본/설정/unit/SQLite 일관된 백업170파일 SHA 확인, 아카이브 SHA `74a80da9209d8a5248d4d2746efee2235de1ae5649b88d2029300723d34b3d59`. 필요시 정상 서비스 정지 후 직전 current/config/unit만 복원하며 최신 Journal·사진·ABORTED·승인 소비 기록은 되돌리지 않는다. 직전 Release는 `engine-integrated-9f6abef5e3c00168`로 추적 결함이 있던 상태다. 이번 실제 복원은 하지 않았다. 배포용 전체 `INTEGRATED_AI_OFFLINE` 패키지 SHA `90a76abb36f307ce2d2065500285c643fc30ddc1866e8cdefa7eac0479fd2a8a`.

비공개 증거: `runs/v1_line_completion_001/passage_reobservation/VERIFIED_ACTUAL_TRIALS.json`, `OPERATOR_CONFIRMATIONS.json`, `V1_SEQUENCE/`, `FINAL_STOP/`, `LEFT_PIPE_FIELD/STATUS.jsonl`. 그림은 기존 `V1_FIELD_RESULTS.html` 맨 위에 추가했다. 사진/DB/현장 설정은 Git에 추가하지 않는다. 아래는 수정 전 단계의 원래 결과·한계를 보존한 기록이며 최신 운영 상태는 이 절을 따른다.

이번 Jetson 임시 검증 폴더89파일(193,149,051바이트)은 노트북 `REMOTE_TEMP_ARCHIVE/v1_passage_reobservation`으로 회수해 전부 SHA를 대조한 후 정리했다. inventory SHA `b9c744c1c38bdd31e346f6083e30ef8c09fce392e2b0b1bd1058fe2972fa986a`. 정리 시 프로세스 비의존과 운영185SHA를 재확인했고 운영 데이터는 변경하지 않았다. HTML의 실제 원본·검출 그림은 직접 열어 대조하고 모든 이미지 경로를 검증했다. 자동 브라우저의 file URL 렌더 확인은 도구 URL 정책에 막혀 미실행이며 우회하지 않았다.

---

## 변경 전 실물 확인

기존 `ANY_CONFIRMED_FAIL_V2`, Release `engine-integrated-2719dff19eb79478`에서 새 배기 결품 검사 `0fd4458adf01458f8350283527e6e865`를 수행했다. 실제 원본3장의 PNG·픽셀 SHA를 확인했고 기본 `FAIL/EXHAUST_TOP_MISSING`, 조립 `REVIEW`, 최종 `FAIL`이었다. NG는 cyclic31667, Done은 다음31668, 요청 해제와 출력0 및 transaction settled를 확인했다. 요청부터 Result10.019초. 현장 사용자가 불량 LED·재가동·마지막 STOP을 확인했다. Worker7590/연결1 유지, 해당 시험 timeout0.

## 최소 수정

- `integrated_decision.py`: `BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1`. 유효한 기본 PASS는 조립 정렬/분석 불확실성만으로 NG가 되지 않는다. 기본 FAIL과 근거가 확인된 조립 FAIL은 우선한다. 조립 후보 문자열만으로 확정하지 않고 각 원본3장의 식별·무결성, 몸체 자세, crop 저장, argmax와 세 프레임 합의를 확인한다. 모델·정렬·점수 임계값은 그대로다.
- `standalone.py`: 원본/저장 증거가 없거나 취소된 요청은 선택적 분석으로 우회하여 발행하지 않는다. 실제 cyclic STOP 입력으로 카메라 복구를 판단하며 새 Worker 준비 중에는 이전 프레임의 시계로 오류를 만들지 않는다. 새 epoch는 이전 제품 이탈 근거가 아니므로 제품/미완료 Journal 계약을 보존한다.
- `standalone_web.py`, `line_hmi.html`, `line_details.js`: 기본 부품 검사와 오조립 참고 분석을 구분하고 개별 원인과 확정 여부를 표시한다. 이전 저장 결과는 수정하지 않는다.

## 최초 카메라 오류 근거

이전 시험 기록에서 monotonic6249.863에 `FRAME_INTEGRITY_REJECTED/BROAD_HORIZONTAL_CORRUPTION`이 최초 원인이었다. Worker6099→6626, generation 변경6250.124, 새 유효 영상6251.835. 기존 Runtime은6251.462에 옛 프레임의 시각으로 `CAMERA_OR_OBSERVATION_STREAM_UNAVAILABLE`을 남겼다. 줄무늬 검출은 유지한다. 이 기록만으로 하드웨어 고장 또는 줄무늬 검출의 오탐을 확정하지 않는다.

정상 분석 불확실성은 결과 처리로 끝나지만 실제 카메라/저장/통신 장애는 현재 요청을 취소한다. 카메라 복구는 정지·무출력·유휴 상태에서 하며 미완료 기록을 가짜 final/ABORTED로 변경하지 않는다. 기존 독립 ABORTED 복구와 Journal 차단을 재사용한다.

## 검증·배포 상태

노트북 집중 회귀147개 PASS(환경별2skip), UI 검사 PASS. ARM64 집중 회귀도147개 PASS(플랫폼 조건1skip). 검증용 도구의 첫 ARM64 실행은 spawn 진입 가드 및 fixture 누락으로 실패하여 도구를 수정했다. 증거 내보내기의 ID 길이 검사 및 검증기의 UI 파생 필드 가정도 바로잡았으며 운영 판정/원본은 수정하지 않았다.

직전 current/config/systemd/SQLite backup API 사본170파일을 노트북에서 읽고 SHA와 DB 무결성을 확인했다. 백업 SHA `a817e5cb532409e1f687bf50456cea8a175d262753038aca14d854c87bbcca26`.

- 실제 소스 commit: `6a9dd7a6bea26bbd0f1fbb1e3e251655d5167078`
- 실제 운영 Release: `engine-integrated-9f6abef5e3c00168`
- 전체 통합 묶음 SHA: `be33f96039d3bf1a900e2cae9838e2f64913866095db3474fff17caafb57b8ca`
- 기동 직후 및 시험 종료 시 **185파일 SHA 일치**, 서비스9609/OpENer9626/카메라Worker9652/Assembly9630 한 벌, 서비스 재시작0, C 연결1/timeout0.
- C 실행 파일은 기존 `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4` 그대로다.

## 실제 판정·PLC 검증

|실물 조건|검사 ID|기본 / 최종|오조립 참고|Result → Done cyclic|요청→실제 Result|
|---|---|---|---|---|---|
|정상|b57e91faa06549b1a6a74665f9356f90|PASS / PASS|REVIEW|6596 → 6597, OK|10.142초|
|배기만 결품|6d0b4101c116434dbc807bd55a234d36|FAIL / FAIL, EXHAUST_TOP_MISSING|REVIEW|18192 → 18193, NG|9.134초|
|정상 복원|9aeab7d71b944392b93851eae1e90244|PASS / PASS|REVIEW|22530 → 22531, OK|9.231초|

각각 실제 새로운 원본3장, PNG와 BGR 픽셀SHA, frame ID/epoch/sequence/PTS, Journal COMPLETE, 통합 final, 정확한 C 요청 식별자, 단일 Result와 다음 패킷 Done, Request OFF/출력0를 대조했다. 사용자는 세 조건 모두 해당 정상/불량 LED와 재가동을 확인했다. PLC의 별도 소비 ACK 태그는 없으므로 소프트웨어 확인 범위는 cyclic 송신·요청 해제이고 물리 LED/재가동은 사용자 확인 근거로 분리했다.

오조립 참고 분석은 세 조건 모두 `SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT`였다. 이를 정상 조립 CORRECT 또는 정렬 해결로 표시하지 않는다. 신뢰 가능한 오조립 FAIL의 우선순위는 회귀로 검증했으며 이번 현장에서는 확정 오조립 FAIL 장면을 수행하지 않았다.

## 추가 실제 요청과 연속성 한계

- `109fe4afce494563b2654b46ec4d3b5f`: 사용자가 정상 모형을 추가 재투입. 새3원본/PASS/OK→Done/요청해제, 9.245초. 첫 정상 이후 Reset·권한 발급 없이 자동 접수됐다.
- `2622483389b24be0bcbbddc0fce8a256`: 배기 결품을 예정했지만 실제 저장 원본에는 배기 부품이 있었다. PASS/OK, 8.944초. 사용자가 결품을 앞으로 투입할 예정이라고 설명했다. 폴더의 예정 장면명 `MISSING_EXHAUST`를 결품 정답으로 사용하지 않는다.
- `d9d903c35f274614a830453ec9d750eb`: 이후 추가 요청은 제품 식별/이탈 근거 부족으로 실제 촬영0, `PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN` ERROR. 기존 사용자 확정 ERROR→NG/Done 계약으로 30.144초에 처리됐다. 실제 AI 성공이나 결품 검증으로 세지 않는다.
- STOP·모형 벨트 밖 보관을 새로 확인한 후 위 제품 문맥만 기존 유지보수 경로로 종료했다. 원본/이전 결과/오류를 보존했고 승인 발급·결과 재송신·가짜 이탈은 없었다. 이후 실제 결품→정상 복원 사이에는 추가 Reset·권한·서비스 전환이 없었다. 부품 조작 때 물리 STOP은 있었다.

따라서 **정상/결품/복원 세 판정은 검증됐지만, START 한 번·무중단3회 또는 모든 다음 요청 준비 성공으로 보고할 수 없다.**

마지막 복원 완료 후 실제 Runtime 연속프레임12243→12244에서 상자 폭이0.426125→0.476263으로 늘었다. 기존 폭 증가 허용0.05를 1280폭 기준 약0.176픽셀 초과해 `PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY`가 됐다. 같은 epoch/generation·sequence+1·약100ms이며 중심은 왼쪽으로24.77픽셀 이동했다. HTTP 표본 누락, 카메라 재시작, 통신 timeout이 이 최초 거부 원인은 아니다. 검출 상자 흔들림과 실제 실물 궤적을 더 대조해야 하므로 임계값만 늘리거나 이탈을 TRUE로 만들지 않았다. **현재 이 문맥이 남아 다음 제품 접수는 준비 완료로 표시하지 않는다.**

## 저장·통신 및 남은 범위

949개 상태 표본과 기존 bounded 진단을 보존했다. 정상/결품/복원 저장 commit은 각각503.48/337.41/436.59ms였다. 서비스 기동 이후 health 갱신 최대281.48ms, IPC snapshot 수신 간격 최대128.63ms. 시험 구간 기록에 ready=false가 없고 Worker/Assembly/C 연결이 유지됐다. C 처리/IPC poll 최대18.06ms, 비동기 디스크 쓰기 최대1.293초는 서로 다른 지표다. 장기 Class1 안정성과 장애복구 성능을 이 짧은 관측으로 확정하지 않는다.

카메라 복구 소프트웨어 경계는 회귀 통과했지만 이번 현장에서 카메라 오류를 주입하거나 자동 복구를 실물 재현하지 않았다. 조립 정렬, 모든 부품/오조립 정확도, 마지막 제품 이탈 추적, 중단 없는 반복운전과 무인 장애복구는 미해결/미검증이다.

비공개 원본/Journal/실행 증거: `runs/v1_line_completion_001/`. GitHub에는 코드·합성 회귀·보고서만 보관한다. PLC·EDS·카메라·조명·모델·C 바이너리·현장 설정은 변경 대상이 아니다. 신규 제품별 권한 없음.

복원은 서비스 정상 종료 후 검증된 노트북 직전 백업의 current/config/unit만 사용한다. 최신 Journal·PNG·ABORTED·승인 소비 원장은 되돌리지 않는다. 직전 코드는 V2이므로 V1 현장 성공으로 표시하지 않는다.

사진·검출 표시·요청별 비교: 비공개 `runs/v1_line_completion_001/V1_FIELD_RESULTS.html`. 결정적 확인: `VERIFIED_V1_FIELD_SEQUENCE.json`, `FIELD_HEALTH_SUMMARY.json`, `RESTORED_PASSAGE_CAUSE.json`, `FINAL_STOP/`. 이 작업에서 운영 복원은 수행하지 않았고 V1 판정 수정본을 유지한다. 추가 START나 새로운 정렬 연구는 진행하지 않는다.

종료된 Jetson 임시 검증 폴더126파일(630,589,682바이트)은 노트북으로 전부 회수해 SHA를 대조한 뒤 정리했다. 보존 manifest SHA `d0669568d10a9e7cd5d2c8da741c05987a1dbb413c665cc6872d353438531dd0`. 운영185파일을 다시 확인했고 current/설정/모델/Journal/사진은 삭제하지 않았다.

## 추가 현장 요청과 추적 보완 진행

사용자가 직접 START해 왼쪽 파이프 결품을 시도한 요청7 `66596ea1a0f94dcdbdbec07d448fd386`은 실제 촬영 없이 기존 제품 식별 차단 ERROR로 끝났다. 약30.07초 뒤 기존 계약에 따른 NG/Done·요청 해제는 관측했지만 왼쪽 파이프 결품을 검출한 FAIL이 아니다. 이후 사용자 요청에 따라 왼쪽/오른쪽 파이프·문양 결품 검증까지 같은 V1 작업에서 계속한다.

`product_passage.py`의 폭 변화만으로 영구 invalid를 만드는 분기를 최소 보완했다. 해당 상자는 근거에서 제외하고 마지막 신뢰 상자를 보존하며 기존 Track 재관측 한도 안에서 후속 관측을 연결한다. 한도 초과·실제 역방향/불연속·다중 물체·영상 식별/품질 오류는 그대로 차단한다. 허용 폭이나 시간 임계값을 확대하지 않았고 검출 누락으로 이탈 proof를 만들지 않는다. 실제 Runtime133프레임 재생에서는12244를 제외하고12245부터 이어졌으며, 별도의 후속 진입이 없어 분리 proof는 만들지 않았다. 집중 PC125/ARM64125 통과, 보완본 현장 적용 및 추가 세 결품 시험은 아직 진행 전이다.

최종 읽기 중 시험 이후 대기 구간에서 `WORKER_HEARTBEAT_LOST`가11795.887에 발생하고11796.003에 READY로 돌아온 것도 추가 보존했다. C는 새 Done 없이 DISARMED 후11796.069에 정지 기준 상태로 복귀했다. 실제 검사 구간의 저장 health 유지와 구분한다. 한 번의 일시 Worker 갱신 누락 원인은 아직 확정하지 않았다. 근거는 비공개 `FINAL_READONLY_STATUS.json`, `POST_TRIAL_IDLE_C_EVENTS.jsonl`, `OPERATOR_ADDITIONAL_MISSING_STATUS.json`이다.
