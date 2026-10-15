# V1 실제 판정·복구·반복 검사

사용자 요청 2026-10-15, 현재 작업 하나. 기준 source887ea3f2 / Release2719dff19eb79478, 문서 HEAD5defdb0. 현재 현장 STOP·방호·감독과 시험 범위 확인. 과거 사진·검사·승인 이력 보존.

## 순서와 완료 기준

1. 운영 코드 변경 전에 현재 FAIL 우선 정책의 실제 배기 결품1회: 새3PNG/basicFAIL/assembly개별/최종FAIL/durable/NG→다음Done/Request해제/LED/재가동.
2. 첫 시험 완료 후 V1 선택적 오조립 분석: 신뢰할 수 있는 확정FAIL 우선, 기본PASS+기하/분석불확실은PASS로 활용. 기본ERROR/무결성/취소를PASS로 만들지 않음. FAIL_CANDIDATE의 실제3프레임 근거 검사.
3. 최초 로그로 카메라Worker교체·프레임/epoch·저장·문맥 문제를 한 원인씩 조사. 누적0가정은 이미 수정했으므로 재구현하지 않음. 과거 요청 재전송/가짜CLEAR/DB초기화 금지.
4. 집중 회귀·노트북 일관된백업·최소current전환·185파일변경검증 후 정상/배기결품/복원3회: 각각 새검사/실제3프레임/최종PASS-FAIL-PASS/PLC/LED/재가동/다음요청자동접수.

PLC·EDS·카메라·조명·모델·임계값 유지. 새로운 정렬 알고리즘/권한제도/전체Candidate 금지. 운영 중 테스트도구 상주 금지. 종료 보고에서 단위·기존영상재생·신규현장 성공을 구분. 실패시 한 원인 수정 후 재검증; 최신증거를 보존하며 코드만 복원.

## 현재 증거

- 읽기전용 PRECHECK: 실제current185SHA일치, service7546/C1연결/Worker7590/Assembly7568 정상, STOP·Request/Result/Done0, SQLite정상. 소프트웨어 권한 필요없음.
- 이전 완료제품5a0708cf의 문맥은 사용자 실물 회수·STOP 확인 후 기존 유지보수 경로로 종료. 원본/final/승인/송신 보존, 신규 권한 없음.
- 새 실제 결품 검사 `0fd4458adf01458f8350283527e6e865`, token `fb1fb40f047c994c:1:1`: 3PNG → 기본 FAIL/EXHAUST_TOP_MISSING → 조립 REVIEW → V2 최종 FAIL. Result cyclic31667 → Done31668 → Request OFF/출력0/transaction settled. 요청→Result10.019초. 사용자가 불량 LED·재가동·현재STOP을 확인. Worker7590과 C 연결1 유지.
- private `runs/v1_line_completion_001/FAIL_V2_TRIAL/`에 일관된 DB 복사·원본·결과·C 이벤트 보존. 이 검사는 기존 V2의 새 실물 검증이며 아래 V1 정책 검증으로 세지 않음.
- 과거 Worker6099→6626의 최초 원인: monotonic6249.863 `CameraError: FRAME_INTEGRITY_REJECTED/BROAD_HORIZONTAL_CORRUPTION`, generation 변경6250.124, 새 정상 프레임6251.835. 기존 Runtime은 옛 프레임으로6251.462 stale 오류를 남김. 물리 카메라 고장 원인이나 검출의 오탐 여부는 이 로그만으로 확정하지 않음.

## 구현 중

- `BASIC_WITH_CONFIRMED_ASSEMBLY_FAIL_V1`: 유효 원본3장과 기본 판정 유지. 오조립 후보는 각 원본의 몸체 기하·안전 crop·저장 SHA·분류 argmax·3프레임 합의로 확인. 정렬 REVIEW/분석 불확실만으로 기본PASS를NG로 변경하지 않음. 원본/저장/취소 문제는 참고 분석으로 우회하지 않음.
- 카메라 복구: 존재하지 않는 V3 RunPermit 대신 실제 cyclic STOP·신선한 연결·출력0·저장/조립유휴 검사. 새 Worker 대기 동안 옛 프레임으로 stale 계산하지 않으며 새epoch로 대기 복원. 과거 제품 이탈/ABORTED를 만들어 내지 않고 기존 Journal admission을 유지.
- 노트북 집중 영향 회귀147개 PASS(Windows 전용 한계2skip), ARM64 및 실제 V1 정상/결품/복원3회는 아직 진행 중.
