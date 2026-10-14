# TASK-018 PLC 자동 반복 정책 재검토

2026-10-14. 개발 소스 구현·격리 검증 범위이며 **운영 적용 및 무인 연속운전은 비활성**이다.
이 문서가 TASK-018의 현재 요구를 설명한다. 이전 감독형 시험 결과는
`SUPERVISED_REPEAT_INSPECTION_REPORT.md`에 이력으로 보존한다.

## 변경한 기준

`PLC_AUTOMATIC_REPEAT`는 정상 운전에서 웹 연결 코드·체크박스·제품별 승인 없이
PLC의 실제 START와 검사 요청을 사용한다. `FIRST_PRODUCT_ONLY`와
`SUPERVISED_REPEAT_TEST`는 별도 정책으로 보존한다. 기본 운영 설정을 자동 모드로
바꾸지 않았으며, 현장 자격 설정도 승인된 값으로 만들어 넣지 않았다.

Area Clearance의 `UNKNOWN` 또는 전체 화면의 제품 존재는 자동 반복의 절대 차단
조건이 아니다. `_clear()`는 이 정책에서 False를 반환하고, C에 가짜 CLEAR를 주지 않는다.
자동 **통신 요청 접수 준비**와 **새 제품의 AI 검사 허용**을 나눴다.

1. 이전 요청의 내구성 있는 최종 Journal 결과, 동일 boot/connection/request token,
   Result/Done/완료 카운터 일치, Request LOW와 출력 0, 유휴 검사 소유자를 확인한다.
2. 현재 카메라·모델·통신·디스크·DB가 정상이고 현장 자동 정책이 검증됐으면
   기계 내부 admission을 한 번만 IPC로 전달한다. 브라우저나 사람의 승인 원장은 사용하지 않는다.
3. 최초·정상 STOP 후에는 정지 기준 상태와 새로운 물리 START를 요구한다.
   정상 완료 후 반복은 Mc_Run을 유지한 채 다음 Request를 기다린다.
4. 이전 제품의 연속 이송·출구 이탈 근거가 있으면 기존 Track 문맥을 종료한다.
   새 tracking session과 source-time cutoff 이후의 현재 Track을 다음 요청에 고정한다.
5. 요청 이후 새 프레임으로 기존 AI 검사를 수행하고 실제 판정·증거를 저장한다.
   PASS는 PLC 0, FAIL/REVIEW/ERROR는 PLC 1이다. 기존 Result-only → 다음 cyclic Done 순서를 유지한다.
6. 제품 구분이 부족한 새 요청은 이전 결과를 재사용하지 않는다. AI 검사는 시작하지 않고
   기존 도착 기한 내 별도 검사 ID로 ERROR와 이유를 저장해 NG·Done으로 종료한다.
   `source=NO_ACTUAL_INSPECTION`으로 실제 AI 검사와 구분한다.

## 현재 장비에서 알 수 있는 것과 없는 것

기존 4/8/10B 계약과 EDS는 그대로다. Assembly150에는 Inspection_Request,
EStop_OK, Mc_Run, Stop_PB만 있다. PhotoSensor 원신호, Sensor_Ready, Move_pending,
Inspecting, Cycle_Done, 모터 피드백, 출구센서 값은 이 cyclic 데이터에 없다.

선택된 PLC v3 저장본 SHA는
`9f491ee447dd5736858d07d2174a033a1654501b18f4c53fa641b4bf29b97806`이다.
저장본에는 2.7초 이송과 Sensor_Ready latch가 있다. 제품 감지 시 latch를 소비하고
완료 뒤 센서 OFF와 Done OFF를 확인해 다음 감지를 허용하는 구조다.
따라서 **온라인 PLC가 이 저장본과 같다는 검증 및 실제 센서 순서 검증을 전제로**
새 요청을 새 센서 사이클의 근거 중 하나로 쓸 수 있다. 센서 재감지만으로 새 제품을 확정하지 않는다.
과거 센서 상승 4회·요청 1회 관측은 참고 근거이며 현재 연속운전의 증명이 아니다.

현재 코드의 센서 근거 표식은 `QUALIFIED_PLC_REQUEST_LATCH`다. 원신호를 직접
관측한 것처럼 표시하지 않는다. 현재 온라인 동등성은 NOT_VERIFIED다.

## 제품별 이탈 관측

`ProductPassage`는 기존 모델의 bbox와 검증된 frame packet을 사용한다. 새 모델,
전처리·추론 임계값 변경, 전체 화면 빈 배경 이미지가 없다.

- 실제 완료 제품의 inspection/cycle/Track 문맥에서 시작한다.
- 같은 epoch/generation/model, 서로 다른 frame ID, 연속 sequence와 source time을 요구한다.
- 확인할 수 있는 수평 출구 방향으로 겹치는 bbox가 전진하고, 화면 안에서 출구 경계로
  이동하는 장면과 줄어드는 꼬리 영역을 순서대로 관측한다. 처음부터 경계에 붙은 bbox는 이탈 근거가 아니다.
- bbox 폭·높이 증가, 역이동, 다중/모호한 후보, 품질 실패, 관측 누락은 해당 근거를 무효화한다.
  꼬리 단계에서도 역이동·증가 검사를 계속한다.
- 꼬리 폭은 최초 폭의 20% 이하이며 출구 경계에 닿아야 한다. 이후 해당 출구 띠에
  제품 검출이 없는 연속 관측 6개 이상·1.2초 이상을 요구한다. 전역 화면에는 분리된
  상류 제품 하나가 보여도 된다. 이것은 명시적인 **미검증 기하 정책**이며 AI 임계값이 아니다.
- 관측 간격 최대 0.5초, 관측 age 최대 1초다. 단순 Track 소실이나 Request 해제는 이탈이 아니다.
- 근거는 요청 한 개에만 소비한다. 이미 접수한 모호한 요청을 나중에 다른 Track으로 바꿔 검사하지 않는다.

이 정책은 현재 현장에서 검증되지 않았다. bbox가 레일을 포함하거나 제품이 경계에
처음부터 잘려 있는 현재 사례에는 근거가 만들어지지 않을 수 있다. 가림·검출 누락·제품 역행이
물리적으로 발생하지 않았다는 것을 영상만으로 일반적으로 증명하지 않는다.
따라서 실제 출구가 보이는 연속 영상, 방향·속도·간격, 잔존물/가림/역행 시험이 필요하다.
이 관측을 확보할 수 없으면 출구센서 또는 별도 제품 식별/이송 관측이 필요하다.
센서 하나의 재상승만 추가해도 같은 제품인지 문제는 해결되지 않는다.

## 대기 교착 및 복구 한계

| 상황 | 구현된 처리 | 남은 한계 |
|---|---|---|
| 접수된 새 요청, 이전 제품 구분 부족 | 도착 기한(시험 설정 8초) 후 새 Journal ERROR → NG·Done 1회 | 정상 연결·저장과 PLC 운전 허가가 유지돼야 함 |
| SYNC_LOW 등 접수 전 HIGH 잔류 | 2초 후 admission 취소·오류 표시·현장 STOP 요구 | 유효한 요청 token이 없어 가짜 Done을 보내지 않음 |
| admission 응답 불명확 | 2초 뒤 오류, 무조건 재시도 안 함 | 감독하 기록 대조 필요 |
| 정상 완료·이탈 후 STOP/해제 | 기존 완료 ID를 Journal에서 다시 검증, 정지 기준과 새 START 대기 | STOP 자체를 제품 이탈 근거로 쓰지 않음 |
| STOP/E-STOP·lease/통신 이상 | 기존 C 차단과 늦은 결과 폐기 유지 | 원격 모터 정지 명령을 만들지 않음 |
| DB 손상·저장 실패·disk 부족 | 결과 발행 차단·오류 유지 | Journal 없이 Done을 만들어 보내지 않음 |
| 완료 후 connection token 변경 | 이전 결과를 새 연결로 옮기지 않고 보류 | 재연결 정합성의 자동 복구는 미검증; 현장 STOP과 감독하 유지보수 필요 |

기존 C 요청 timeout 120초와 health lease는 변경하지 않았다. 이 timeout은 adapter를
비활성화할 뿐 PLC의 Inspecting latch를 강제로 해제하지 않는다. 저장된 PLC 로직에는
독립 검사 timeout이 확인되지 않으므로 **모든 장애에서 PLC Done 대기가 자동 해소된다고 주장할 수 없다**.
PLC STOP으로 Request/Inspecting 해제를 확인하고 실제 정지 후 미완료 Journal과 출력을
대조하는 복구 절차가 필요하다. Move_pending의 STOP 잔류 가능성도 현장 확인 대상이다.
이 검증이 없으면 `plc_timeout_stop_recovery_verified`를 True로 설정할 수 없다.
영구적인 identity/DB/연결 오류는 일반 START만으로 근거를 초기화하지 않는다.

## 운영자 연결 코드와 UI

기존 코드는 감독형 준비 API의 쓰기 권한을 브라우저 한 세션에 부여하려고 추가했다.
EtherNet/IP 연결이나 정상 검사 시작에 필요한 PLC 코드가 아니다.

- 생성: `src/runtime/supervised_web.py::PreparationAccess.__init__`의
  `secrets.token_urlsafe(32)` → private `web_pairing.json`.
- 검증: 같은 파일 `permits()`의 허용 Host·동일 Origin·Bearer 상수시간 비교.
- 적용: `standalone_web.py::configure_line_web()`의 제한된 prepare POST.
- 화면: 기존 입력·체크박스·POST JavaScript를 `supervised_panel.html/.js`로 분리했다.
  명시적인 감독형 시험 모드의 `/maintenance/supervised`에서만 제공한다.
- 정상 `/line`, `/auto`는 GET 모니터다. `/auto`는 `/line`으로 연결한다.
  실제 AI 판정과 PLC OK/NG, 사진, 최근 기록, 오류를 표시하며 입력·form·POST 호출이 없다.
  자동 admission 실패는 제품 대기 문구보다 우선해서 현장 STOP 복구를 표시한다.

## 수정 범위 및 확인

- Python: `automatic_admission.py`, `product_passage.py`, `standalone.py`,
  `inspection_start.py`, `opener_cyclic.py`, `opener_process.py`, `standalone_service.py`.
- C: `engine_commissioning.c/.h`, `engine_ipc.c`, `engine_callbacks.c.inc`에
  opt-in 자동 admission을 추가했다. 기존 EAI1 v3 160B IPC command 6이며 PLC wire는 불변이다.
- UI: `standalone_web.py`, `line_hmi.html`, 분리된 유지보수 panel 2개.
- 기존 TASK017 무결성 검증과 3프레임/최종 판정 경로를 유지했다.
- 모델·가중치·EDS·sampleapplication·cipioconnection 송신 경로·PLC·Journal schema 불변.
- 검토에서 SYNC_LOW 잔류 HIGH 무한 대기, 정상 STOP 후 완료 문맥 손실,
  꼬리 역행의 잘못된 이탈 인정 세 경로를 재현하고 수정·회귀 테스트했다.

## 검증 증거와 배포 상태

최종 native Python 회귀 **259개 PASS**(52.305초), 최초 승인 C 22개 PASS,
감독형·자동 반복 C 상태 시험 및 ASan/UBSan PASS, 실제 AF_UNIX C↔Python의
한 START·4종 판정 반복 PASS다. 별도 검토자의 7개 집중 회귀도 PASS다.
로컬 모니터는 input/form 각 0, pairing 문구 없음, console 오류 0을 확인했다.
공개할 Git index에서 따로 내보낸 소스로도 관련 29개 회귀 PASS를 확인했다.
공개 대상 30개 경로만 검사·스테이징했으며 운영 자료나 다른 미커밋 변경을 포함하지 않았다.

Native 빌드는 `cmake --build --clean-first`로 재컴파일했다. 기존 타임스탬프가 0인
tar 차분과 이전 build 디렉터리만으로는 재컴파일을 보장할 수 없어 이전 결과를 최종 근거로 쓰지 않았다.
기존 unsigned long→uint32_t/time_t 변환 warning은 남아 있으며 오류를 숨기거나 옵션을 완화하지 않았다.

- 새 개발 OpENer SHA256: `5853964c8a891beeac6db7c2cb248532599444107427fa0ca53dafde2d116541`
- 회수한 최종 결과 archive: `10dc16579f3e3e72a6acbeecbd0e4402f58fc2c6fe8422328cf6c007adda2b6c`
- EDS 유지: `78c0a78cb4f3e43da8090d41cdddfa14aa86dac7212f229104c0e75f02071b01`
- 소스 전송 manifest와 native 테스트 입력·노트북 원본 일치 확인.
- 전후 운영 current/config/unit SHA, 검사 DB 행과 승인 원장 논리 SHA, service PID/상태 동일.
  service enabled/active, PID 31151, NRestarts 0. 운영 카메라/AI 준비 및
  Request/Mc_Run/Result/Done LOW를 읽기로 확인했다. 실제 벨트 정지는 이번에 새로 관찰하지 않았다.
- 상세 비공개 증거: 기존 `supervised_repeat_018/automatic_revision/`의
  `FINAL_VERIFICATION.json`, `native_evidence/`, `MONITOR_ISOLATED.png`.

격리 테스트는 합성 입력과 실제 Python Runtime/Tracking/Journal 및 C AF_UNIX IPC를 사용한다.
현장 PLC 송수신 또는 실제 AI 정확도 PASS로 해석하지 않는다.

이번 구현은 개발 소스에만 반영한다. 운영 Release
`engine-supervised-c6f5b94e8adb4e2e` 및 `engine-inspector.service`를 교체/재시작하지 않는다.
운영 DB, 개인 설정, 사진, 승인 원장은 GitHub에 올리지 않는다. Python+C 개발 변경은
같은 commit에서 관리하지만 운영 배포 Release는 별도다.

자동운전 적용 전: 온라인 PLC 동등성·센서 사이클, 실제 이탈·재등장·가림·제품 간격,
STOP 잔류/timeout, 재연결, 현재 AI 부하 IPC lease를 검증해야 한다.
정상 반복에는 웹 승인 조건을 되살리지 않는다. 현장 검증을 마친 설정과 배포 범위에
대한 별도 적용 승인을 받은 후 서비스를 전환한다.
이번 상태: **STOP_FOR_FIELD_VALIDATION_AND_DEPLOY_APPROVAL**.

운영본을 바꾸지 않았으므로 운영 롤백 작업은 없다. 노트북의 기존 TASK018 배포 백업과
원장은 보존한다. 추후 전환 전에는 현재 `current`·설정·unit·Release/SHA와 SQLite backup API
백업을 새로 회수·해시 확인하고, 실패 시 그 직전 운영본으로 복원한다. 이 문서는 배포 승인이 아니다.
