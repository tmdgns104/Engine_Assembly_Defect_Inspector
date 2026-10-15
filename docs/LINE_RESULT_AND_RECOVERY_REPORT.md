# 부품별 결과와 재시험 복구 화면

상태: TASK-024 첫 UI 적용 후, 사용자 요청에 따른 코드 없는 Reset 및 재시작 이력 표시 보완 검증 완료. 최종 적용 확인은 아래에 기록한다.

## 표시와 동작

`/line`은 최근 결과 카드 아래에서 네 부품의 **존재 여부**와 **방향·조립 분류**를 별도로 보여 준다. 최근 이력을 선택하면 그 검사 ID의 Journal, 필수 조립 검사 기록 및 통합 최종판정만 읽는다. 원본→몸체 전체 정렬→네 crop을 저장된 범위에서 표시한다. 점수는 모델 분류 점수이며 정답 확률로 표현하지 않는다. 프레임 간 불일치·미평가·촬영 없음은 정상/결품으로 대체하지 않는다.

현재 `PREVIOUS_PRODUCT_IDENTITY_OR_EXIT_UNPROVEN`의 0프레임 기록은 **ERROR · 검사 미실행**이다. 실제 정렬 실패 기록에서는 원본과 실패 이유만 보이고 부품 분류는 미실행이다. 고정 몸체 마스크·대응점 표시 영상은 현재 저장 계약에 없어 그 한계를 명시한다. 미채택 진단 crop을 운영 증거로 사용하지 않는다.

**재시험 준비 (Reset)**는 기존 `close_previous_product_context()`의 현장 복구 화면이다. 현재 STOP·Request LOW·Result/Done 0·신선한 연결·Worker/Assembly/저장 유휴·실제 미완료 없음과 대상 원장 해시를 다시 검증한다. 버튼을 누르면 정지·모형 정리 안내와 실행 확인이 나온다. 코드·담당자·사유 입력이나 체크박스는 없다. 담당자의 확인 클릭은 `FIELD_HMI_OPERATOR`로 기록하며 인증된 개인 신원으로 주장하지 않는다. 일반 자동검사에는 이 버튼이 필요 없다.

초기 구현은 기존 `PreparationAccess`의 서비스별 무작위 코드를 재사용했으나, 사용자가 Reset에 불필요하다고 명시해 제거했다. Reset 경로는 코드 생성·파일 읽기·Bearer 인증에 의존하지 않는다. 과거 인증 파일·기록은 삭제하지 않는다. 허용 Host·같은 Origin·JSON 및 브라우저 same-origin 검사는 유지하며 다른 POST는 계속 차단한다. 이는 현장 LAN에서 접근 가능한 복구 기능이며 사용자별 접근 인증 기능은 제공하지 않는다. 실제 PLC 상태와 저장/작업 조건은 실행 시점에 재검증한다.

기존 검사·사진·통합판정·ABORTED·승인 기록을 수정/삭제하지 않는다. 독립 `MAINTENANCE_PRODUCT_CONTEXT_CLOSED` 영수증만 추가한다. AI CLEAR나 제품 이탈을 위조하지 않고 과거 Result/Done을 재발행하지 않는다. 미완료 검사·DB 손상·저장소·카메라·통신 장애는 복구 대상으로 위장하지 않는다. 상태 조회는 무변경이며 POST 순간에도 조건을 다시 검사한다. 실제 중단 검사 ABORTED 처리는 기존 별도 절차를 유지한다.

## 변경

- `jetson/apps/edge_service/line_hmi.html`: 결과·단계·네 부품·과정·이력 선택·예외 복구 dialog.
- `jetson/apps/edge_service/line_details.js`: 검사 ID별 증거 읽기/표시와 확인 버튼의 단일 복구 요청. 같은 ID는 반복 조회하지 않으며 실패 시 수동 재조회. 인증 코드를 요구하거나 저장하지 않는다.
- `jetson/src/runtime/standalone_web.py`: 읽기 전용 복구 사전 상태, 정적 JS, 정확한 Reset POST·Origin·허용 Host·JSON 검증. 서비스당 한 번 최대 30건의 저장 이력을 표시 전용으로 복원하며 발행 상태기계에는 주입하지 않는다. 요청 토큰이 일치하는 저장 이벤트만 Done/요청 해제 근거로 사용한다.
- `jetson/src/runtime/standalone.py`: 기존 복구의 현재 상태 증거 수집을 공용 함수로 분리; 사전 조회 추가. 정상 검사·PLC 상태기계 불변.
- `jetson/src/runtime/product_context_recovery.py`: 현재 상태 검증과 현장 확인 검증을 분리하되 실제 기록은 두 검증을 모두 요구.
- `jetson/runtime_allowlist.json`: 새 JS 포함.

운영 설정 차이는 `line_profile.maintenance_recovery.allowed_hosts`에 현장 화면의 `192.168.50.2:18771` 한 곳 추가뿐이다. 기존 `127.0.0.1:18771` 유지, wildcard·일반 POST 허용 없음. 사용자 지시로 Reset의 개인 인증 코드는 제거했다. PLC/EDS/C 바이너리/모델/정렬/카메라/조명/결과 정책은 변경하지 않는다.

## 검증

- Windows 집중 30건 PASS: 유지보수/새 제품 자동 요청/STOP·기존 원장/화면 의미. 초기 sandbox TEMP·namespace 충돌은 workspace TEMP와 명시적 import 경로로 해결했다.
- ARM64 격리 최종 36건 PASS: 코드 없는 Reset 경로, 잘못된 Origin/Host/콘텐츠 형식·cross-site 거부, 예고 없는 PLC 상태 변경 시 복구 거부, 실제 미완료·저장 부족 차단, 미리보기 snapshot/304, 이력 복원과 요청 토큰 동일성. 카메라·PLC는 fixture이며 현장 결과 송신 성공을 의미하지 않는다.
- Node UI 계약 PASS: 결품·오조립·상충·미실행, 다른 frame ID 거부, 페이지 로드 시 쓰기 0, 현장 확인 버튼, 중복 클릭 POST 1회, 코드/토큰 의존성 없음.
- 실제 노트북 SQLite 백업에서 저장 이력 16건·최신 촬영 없는 ERROR·과거 3프레임 검사·동일 토큰 완료 이벤트를 읽기 전용으로 확인. DB 변경 0. 최초 테스트 fixture의 이벤트 envelope와 Content-Type 누락은 실제 저장/브라우저 계약에 맞춰 수정 후 재검증했다.
- 미리보기 3시나리오 PASS: 상태 조회와 독립, 이미지 한 요청만 진행, 같은 JPEG를 새 프레임으로 세지 않음.
- 기존 실제 정렬 실패 JSON과 0프레임 기록은 적용 후 읽기 전용 화면에서 대조한다.

## 적용·복원

사용자가 현재 실제 STOP 유지와 UI 서비스 전환을 확인했다. 운영 전 current·config·서비스 정의·Release/SHA 및 SQLite backup API의 Journal/승인 원장을 노트북에 저장하고 모든 파일을 다시 읽어 검증한다. `INTEGRATED_AI_OFFLINE` 패키지의 기존 자산을 모두 보존하며 서비스 정상 종료 후 일치하는 소스·설정·Release를 적용한다. 정상 기동/해시/단일 소유자 확인 실패 시 정지한 상태에서 직전 코드·설정으로 복원한다. 최신 Journal·사진·ABORTED·승인 소비 기록은 되돌리지 않는다.

운영 적용 및 실제 화면 결과는 아래에 추가한다. 이번 작업은 새 START·원장 복구 POST·PLC 결과 송신 시험을 자동 실행하지 않는다. 조립 정렬·모델 판정 문제의 해결 여부와 UI 개선은 별개다.
