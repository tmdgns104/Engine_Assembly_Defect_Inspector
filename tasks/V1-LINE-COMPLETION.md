# V1 실제 판정·복구·반복 검사

## 최신 완료 범위 — 2026-10-15 추가 현장 시험

- source `7ec9d25e204f60a0e2ec7825f1d1560968510611`, Release `engine-integrated-32d132a4256d4ef8`, 185 SHA 일치. 폭 전용 검출 outlier를 마지막 신뢰 상자에서 기존 한도 내 재관측하며 임계값·PLC·모델·C 계약 변경 없음. PC125/ARM64125 및 실제 소비133프레임 재현 검증.
- 실제 START 한 번/중간 STOP·START·Reset·권한 없이 네 사이클: 왼쪽a489d5fa LEFT_PIPE_MISSING, 오른쪽5d1aa003 RIGHT_PIPE_MISSING, 문양86131de3 PRODUCT_ENVELOPE_NOT_FOUND, 추가 문양caabb4cb SYMBOL_MODULE_MISSING. 모두 실제3원본·Journal·finalFAIL·NG→다음Done·요청해제, 사용자 불량LED/재가동 확인. 후속3회는 이전 이송+신규 상류진입 근거로 자동 접수.
- 첫 문양은 한 프레임 엔진점수0.484<0.5로 부품미평가, 나머지2문양MISSING. 재시험3장문양MISSING 확인. 첫 검출 불안정을 성공으로 덮지 않고 보존. 오조립 참고REVIEW·장기무인/장애복구는 별도 미검증.
- 최종 사용자STOP 및 실제PLC McRun/Request/Result/Done0, WorkerIDLE/Assembly유휴/SQLite정상. 새12원본SHA·frameID/PTS·C단일송신 검증. 저장277~421ms, 시험health최대255.45ms/readyfalse0. 같은서비스12092/Worker12135/C연결1/timeout0.
- 노트북 직전 백업170파일 및SQLite 확인(SHA74a80da9...), 원본 이력 보존. 보고서 docs/V1_LINE_COMPLETION_REPORT.md와 기존 사진 viewer 최신 절 참조. 새 알고리즘·다음TASK·추가START 자동 진행 없음.

아래 내용은 위 완료 범위에 이르기 전의 작업·관측 이력이다.

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
- 노트북 집중 영향 회귀147개 PASS(환경 조건2skip), ARM64 집중 회귀147개 PASS(플랫폼 조건1skip), UI 검사 PASS.
- 일관된 노트북 백업170파일 SHA 및 SQLite 무결성 확인 후 `engine-integrated-9f6abef5e3c00168` 적용. 소스 `6a9dd7a6bea26bbd0f1fbb1e3e251655d5167078`, 실제185파일 SHA 일치. 서비스9609/C9626/Worker9652/Assembly9630, 재시작0, 연결1.
- 신규 정상 `b57e91faa06549b1a6a74665f9356f90` 기본PASS/조립REVIEW/최종PASS→OK/Done/요청해제. 정상 LED·재가동 사용자 확인. 추가 정상 재투입 `109fe4afce494563b2654b46ec4d3b5f`도 새3원본/PASS/OK/Done. 사이에 소프트웨어 승인·Reset 없음.
- 이후 `2622483389b24be0bcbbddc0fce8a256` PASS 원본에는 배기 부품이 존재. 사용자는 결품을 앞으로 투입할 예정이라고 설명했으므로 이 기록을 결품 성공/오판으로 단정하지 않음. 추가 요청 `d9d903c35f274614a830453ec9d750eb`는 제품 식별 근거 부족으로 실제촬영0/ERROR, 기존계약NG/Done, 별도 보존. 새 STOP·모형 벨트 밖 보관 근거로 이전 제품 문맥만 종료.

## 최종 검증 상태: 판정 실물 검증 PASS / 연속운전 완성 미달

- 실제 결품 `6d0b4101c116434dbc807bd55a234d36`: 새3PNG/basicFAIL EXHAUST_TOP_MISSING/finalFAIL/NG18192→Done18193/요청해제. 사용자 불량LED·재가동 확인. 요청→Result9.134초.
- 실제 복원 `9aeab7d71b944392b93851eae1e90244`: 새3PNG/basicPASS/finalPASS/OK22530→Done22531/요청해제. 사용자 정상LED·재가동·현재STOP 확인. 요청→Result9.231초. 결품→복원 사이 소프트웨어 Reset·권한 없음, 같은 서비스/C/카메라 유지.
- 최종185SHA일치/SQLite정상/PLCSTOP·출력0/WorkerIDLE/Assembly유휴. 실제5건15PNG SHA·픽셀·식별 검증, 별도촬영0 오류1건도 그대로 보존.
- 기본 정상/결품/복원 PASS/FAIL/PASS는 확인했으나 추가투입·물리STOP·중간문맥복구가 있어 무중단3회로 세지 않음.
- 마지막 완료 후 실제Runtime sequence12243→12244의 bbox폭 증가가 기존허용0.05보다0.00013766 커져 PRODUCT_PASSAGE_TRAJECTORY_DISCONTINUITY. 영상/epoch 연속, 약100ms. 다음제품 대기 차단이 남음; 허용치변경/가짜이탈/추가시험 없음. V1 전체 완성으로 표시하지 않음.
- 보고서 `docs/V1_LINE_COMPLETION_REPORT.md`, 사진 비교 `runs/v1_line_completion_001/V1_FIELD_RESULTS.html`. 운영 V1 수정본 유지, 다음 TASK 자동 시작 없음.

## 같은 V1 작업 계속: 제품 궤적 차단 및 추가 결품

사용자가 왼쪽/오른쪽 파이프와 문양의 실제 결품 확인을 추가했다. 직접 START한 요청7 `66596ea1a0f94dcdbdbec07d448fd386`은 남은 제품 문맥 때문에 촬영0/ERROR로 끝났으며 결품 성공으로 세지 않는다. STOP·모형 벨트 밖 보관을 다시 확인했다. 임시 Reset 반복보다 영구 차단 원인을 먼저 수정하라는 지시에 따라 기존 ProductPassage의 폭 변화 한 프레임을 조사했다.

- 기록된12244 폭 outlier 뒤12245는 마지막 신뢰 상자와 정상 연결된다. 폭 전용 이상은 근거에서 제외하고 기존 missed-frame/time 한도 안에서 같은 제품을 재관측한다. 역방향·서로 떨어진 상자·모호한 다중 물체·epoch/품질 변경은 계속 차단한다. 폭/시간/검출 임계값은 변경하지 않는다.
- 실제 소비133프레임 재생에서 outlier를 근거로 쓰지 않고 추적을 재개했다. 새 진입 영상이 없는 기록이므로 제품 분리 proof는 여전히 없음. 격리 PC125/ARM64125 PASS; 현장 적용·왼쪽/오른쪽/문양 결품은 진행 대기다.
- 최초 PC 실행은 옛 root src가 import돼 실패했고, sandbox 임시 SQLite 접근 및 redirection 실행에도 문제가 있었다. 올바른 jetson 우선 경로·프로젝트 임시 폴더·직접 테스트 러너로 최종125개를 실행 확인했다. 운영 코드를 이 환경 문제에 맞춰 변경하지 않았다.
- 시험 종료 후 대기 중11795.887에 Worker heartbeat false,11796.003에 READY 복귀가 관측됐다. C는 추가 결과 없이 DISARMED→STOPPED_BASELINE으로 돌아왔다. 새 시험 중 저장 health 성공과 구분하며 순간 Worker 갱신 원인은 미확정이다.
