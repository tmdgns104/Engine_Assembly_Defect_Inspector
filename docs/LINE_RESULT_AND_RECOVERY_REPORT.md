# 부품별 결과와 재시험 복구 화면

상태: 실제 Jetson 적용 및 읽기 전용 화면 검증 완료. Reset 실행·새 START 시험은 수행하지 않음.

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

## 실제 적용 결과 — 2026-10-15

- 소스 commit: `ba6b9be9b5bb75e074c9e1db2243a7e7b61a6f30`, 공식 master Push 확인.
- 실제 Release: `engine-integrated-63ac009827142f1e`. 전체 185개 파일 SHA 일치. C SHA `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4` 유지.
- 첫 UI 적용 뒤 재시작 이력이 비어 보임을 실제 화면에서 발견했고, Journal 표시 전용 복원으로 수정했다. 이후 사용자 지시로 Reset 코드 의존성을 제거했다. 최종 변경은 HTML/JS/웹 라우트 3개이며 카메라/추론/PLC 경로는 그대로다.
- 서비스 active, NRestarts 0. MainPID 83147, OpENer 83164, 카메라 Worker 83190, 카메라를 소유하지 않는 Assembly Worker 83168. 카메라 및 조립기 ready, IDLE/저장·최종판정 pending 없음.
- 현재 PLC: Request=0, Mc_Run=0, Stop_PB=1, EStop_OK=1, Assembly100=`00000000`, 새 request/result/done count 모두 0. 연결 신선 상태. 현재 과거 제품 문맥 차단은 남겨 두었으며 실제 Reset을 임의 실행하지 않았다.
- 실제 브라우저 확인: 16건 이력, 최근 0프레임 ERROR의 촬영 미실행 표시, 과거 3프레임의 네 부품 존재 확인·몸체 정렬 0/3·분류 미실행·원본 이미지·실패 이유 표시. JavaScript 오류 로그 없음. Reset 창은 코드/담당자/사유/체크박스 없이 정지·모형 정리 확인 버튼을 제공하며, 현재 읽기 전용 사전 검사는 eligible이었다. 최종 실행 버튼은 누르지 않았다.
- Worker 처리 미리보기 지표 약 5.42 FPS, 실제 웹 이미지 갱신 확인. 새 브라우저 표시 FPS 벤치마크나 실제 검사 중 부하 시험은 이번 적용에서 수행하지 않았다.

노트북 증거 위치: `runs/line_result_recovery_024/`. 최종 적용 직전 백업 `final_ui/PRECHANGE_BACKUP.tar.gz` SHA `27b1bbaea973564c769cb650473f1306a37f460b92ed69de1d05344daf7c2a1d`, 170개 파일 전부 재읽기 검증 및 SQLite integrity OK. TASK-024 이전 백업은 상위 경로의 동명 archive, SHA `87cf9e612ec7550d31a6b6c21ebd2a0eb7c6fe158b76b145ce910555a40560e7`, 169개 파일 검증 완료. 백업 자체는 공개 저장소에 포함하지 않는다.

최종 패키지 SHA `3b8b591547726edc0feb7ef61cba5bf3ab62b8247ae54eb6788008a50a9ce7fb`. 실제 파일과 패키지의 정합성은 확인했고 복원 자료는 읽기 검증했다. 실장치 롤백은 필요하지 않아 수행하지 않았다. 복원 시 직전 코드·설정만 정상 정지 중 복구하고 최신 Journal/사진/ABORTED/승인 기록은 되돌리지 않는다.

Reset의 actual field mutation 및 그 뒤 새 제품 START는 미검증이다. 기능 검증은 격리 36건과 실제 UI/사전 조회까지이며 실제 복구 성공으로 보고하지 않는다. 조립 정렬·모델 판정 문제는 여전히 별도 미해결이다. 마스크/대응점 이미지가 기존 저장 결과에 없다는 한계도 유지한다.
