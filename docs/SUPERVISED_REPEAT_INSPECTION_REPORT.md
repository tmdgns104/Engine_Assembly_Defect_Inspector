# TASK-018 감독형 반복 검사 구현

> 2026-10-14 후속 사용자 지시로 정상 운전은 PLC 자동 반복 정책으로 변경했다.
> 현재 구현·격리 검증·남은 현장 조건은 [PLC 자동 반복 보고서](PLC_AUTOMATIC_REPEAT_REPORT.md)를 따른다.
> 아래는 감독형 후보를 만들 당시의 기록이다. 해당 감독형 Release는 이후 별도 승인으로
> 실제 설치되었으며 현재 운영본은 `engine-supervised-c6f5b94e8adb4e2e`다.
> 새 자동 반복 변경은 아직 운영에 배포하지 않았다. 정상 UI와 유지보수 인증을 분리했다.

상태: **ISOLATED_PASS / STOP_FOR_DEPLOY_APPROVAL** (2026-10-14).

공식 `jetson/`에 감독형 반복 승인을 구현했다. 실제 Jetson 운영본은 아직
`engine-integrated-90a914423826735a`이며 서비스와 PLC 설정을 바꾸지 않았다.
준비한 배포 Release는 `engine-supervised-c6f5b94e8adb4e2e`다.
이 문서를 포함하는 Git commit이 개발 소스 식별자이며, 운영 적용 증거와 구분한다.
TASK-017 integrity 수정은 개발 소스 및 배포 차분에 포함한다.

## 반복 승인의 동작

`FIRST_PRODUCT_ONLY`의 한 번 제한은 유지한다. 설정으로 명시적으로 선택한
`SUPERVISED_REPEAT_TEST`에서만 다음 흐름을 사용한다.

1. 이전 결과가 Journal에 저장되고, 해당 요청의 Result/Done 송신 및 Request 해제와
   Done 초기화가 확인되어야 한다. 검사 Worker와 조립 검사 작업도 종료되어야 한다.
2. Request와 Mc_Run이 LOW이고 연결·카메라·저장이 정상일 때 현재 문맥에 묶인
   준비 challenge를 만든다. PLC 비트는 물리 정지의 증거를 대신하지 않는다.
3. 감독자가 실제 정지, 감독 상태, 이전 제품 정리, 새 제품 한 개 배치·손 뗌,
   REVIEW/ERROR의 NG 반환 후 벨트 재가동 가능성을 확인한다.
4. 새 승인 ID를 기존 승인 원장에 먼저 예약한다. 별도 evidence에 사람의 확인과
   당시 소프트웨어 상태를 저장한다. 실패한 승인도 지우거나 재사용하지 않는다.
5. 이전 관측·Track 문맥을 종료하고 새 tracking session과 frame cutoff를 만든다.
   C가 승인을 접수하면 화면에 현장 START 대기를 표시한다. 웹은 모터를 시작하지 않는다.
6. 새 실제 START와 Request 이후 현재 제품을 검사한다. 결과를 내구성 있게 저장한 후
   기존 Result-only → 다음 cyclic 패킷 Done 순서로 전달한다.
7. 완료 후 다시 감독자의 준비 확인을 기다린다. 자동 재무장·자동 CLEAR는 없다.

Track의 고유 식별자는 기존 `(tracking session, local track ID)`이며 숫자 Track ID만
전역 고유값으로 취급하지 않는다. Request token은 adapter boot/connection/request ID로
구분한다. 승인·Cycle·Inspection도 각각 새 식별자를 갖는다.

C의 사용 승인 ID는 프로세스 내 최대 4096개까지 보존하며 한도에 도달하면 유지보수를
요구한다. Python 원장은 서비스 재시작 후에도 보존한다. 부팅·연결·카메라 문맥 변화는
기존 승인을 폐기한다. 미완료 시험은 단순 확인란으로 해제할 수 없다.

## 변경 파일과 역할

| 파일 / 함수 | 변경 |
|---|---|
| `engine_commissioning.c/.h` / `CommSupervisedArm` | 명시적 반복 승인, 사용 ID 보존, 누적 카운터 일치와 정리 상태 확인 |
| `engine_ipc.c` 및 `opener_cyclic.py` | 양쪽 EAI1 IPC v3, 160B 유지, 새 command 5. 기존 command 4는 최초 전용 |
| `engine_callbacks.c.inc`, `opener_process.py`, `standalone_service.py` | 하나의 서비스가 정책을 자식 C 프로세스에 전달 |
| `supervised_approval.py` | 기존 InitialApproval/JournalAdmissionGuard 재사용, 새 challenge·예약·완료 확인 |
| `standalone.py` / `_supervised_settlement`, `_prepare_supervised_product` | 이전 결과·작업 종료 확인, 새 제품 문맥, 실제 결과 및 승인 연결 |
| `inspection_start.py` | 명시적 감독형 정책만 Full-Frame 요청 검사에 허용 |
| `assembly_inspection.py` | 조립 검사 active/pending/outstanding 관측. 모델 처리 의미는 동일 |
| `supervised_web.py`, `standalone_web.py`, `line_hmi.html` | 제한된 준비 POST, 실제 AI/PLC 판정 분리, 기존 화면에 준비 확인 추가 |
| `opener/OpENer`, `PROFILE.json`, `release.json` | 함께 검증한 ARM64 실행 파일, 정확한 프로필과 미배포 Release 표시 |

기존 카메라·검사·Journal·결과 발행 소유자를 재사용한다. 별도 전체 Candidate나
두 번째 검사 서버는 만들지 않았다. 추가 모듈은 승인 정책과 웹 접근 확인 두 개다.
FIRST_PRODUCT_ONLY와 공유하는 저장·무결성·발행 경로를 복제하지 않았다.

## 운영자가 사용할 화면과 절차

배포 승인 후 `/line`을 사용한다. 감독형 웹 기능을 켠 경우 `/auto`도 같은 화면으로
연결된다. 서비스 시작 때 생성되는 개인 연결 코드로 브라우저를 한 번 연결한다.
이 코드는 GET·URL·일반 로그에 노출하지 않으며 서비스 재시작 시 새로 발급한다.

매 제품: **현장 STOP → 이전 제품 정리 → 새 제품 한 개 배치하고 손 떼기 → 화면의
다섯 확인란과 ‘다음 검사 준비’ → 준비됨 표시 → 현장 START** 순서다.
검사 후 실제 벨트 정지·재가동·제품 이탈을 감독자가 확인한다. 다음 제품도 같은 순서로
확인하며 서비스 재시작이나 Codex 명령, 승인 원장 초기화가 필요하지 않다.

화면에는 실제 PASS/FAIL/REVIEW/ERROR와 PLC OK/NG, 검사 ID, 원본 이미지,
Journal 저장, 소요 시간, 오류 이유를 따로 표시한다. `PRODUCT_COUNT_NOT_ONE`을
숨기지 않는다. 요청 후 검사 자체가 불가능했던 ERROR는 실제 추론 성공으로 표시하지 않는다.
카메라·저장·통신 문맥이 불확실하면 승인을 차단한다.

`/api/v1/line/supervised/prepare` 한 경로만 Host allowlist, same-origin, 개인 Bearer
인증, 짧은 유효기간의 challenge와 전부 확인된 항목을 요구한다. 다른 변경 요청은
기존처럼 차단한다. 새로고침·GET·재접속은 승인이나 START를 만들지 않는다.
UI에서 반환하는 202는 예약 요청 접수이며 C 승인 완료가 아니다.

## 검증 결과

| 검증 | 결과 / 범위 |
|---|---|
| Jetson ARM64 Python 회귀 | **ISOLATED_PASS: 229개**. 전체 228개(45.884초) + 추가 no-product deadline ERROR 반복 1개 |
| 최초 한 제품 C 회귀 | **ISOLATED_PASS: 22 assertions**, Address/Undefined sanitizer |
| 감독형 C 상태 전이 | **ISOLATED_PASS**, sanitizer, Result-only/Done 순서·중복 승인·정지/통신 차단 |
| Python ↔ 실제 C AF_UNIX IPC | **ISOLATED_PASS**, 4개 합성 결과 PASS/FAIL/REVIEW/ERROR, 별도 Journal/원장. EtherNet/IP 소켓·PLC·카메라 사용 없음 |
| ARM64 OpENer 전체 빌드 | PASS, 공유 라이브러리 누락 없음. 필드 인터페이스로 실행하지 않음 |
| UI 브라우저 | **ISOLATED_PASS**, 로컬 fixture. 준비 POST 1회, 새로고침 재전송 없음, 모바일 390px overflow 없음, console error 0 |
| 배포 차분과 백업 | 18개 배포 파일 SHA 일치, 직전 운영 소스·설정 120개 SHA 일치, SQLite backup API/무결성 및 논리 해시 일치 |
| 현장 운영 적용 / 실제 반복 3회 | **NOT_RUN / 별도 승인 대기** |

회귀는 새 ID·제품 문맥, 이전 Worker 결과 거부, 중복/지속 HIGH/잔여 Result·Done,
STOP/EStop, 연결·카메라 문맥 변경, 재시작 후 승인 재사용, 미완료 Journal 및 저장 실패,
다섯 확인 누락, 잘못된 웹 인증·Origin, 기존 최초 승인 계약을 포함한다.
초기 격리 실행의 fixture 설정 누락, httpx 의존성 누락, fixture 원본 PNG 누락은
시험 준비에서 수정했다. 운영 패키지를 설치하거나 보호 조건을 완화하지 않았다.
실패 로그와 최종 성공 로그를 모두 노트북에 보존했다.

## 배포 경계와 보존

배포 차분 SHA-256:
`8dac9dc2274d30d415e15621e39ccd8bf92903d8a59276fb741b29d9823de905`

새 ARM64 OpENer SHA-256:
`896c4e69cdf246529ac5ca5bfc9e216dd17550d1459fb15fd123b84a4ab96837`

EDS SHA-256(변경 없음):
`78c0a78cb4f3e43da8090d41cdddfa14aa86dac7212f229104c0e75f02071b01`

노트북 증거 디렉터리:
`runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/supervised_repeat_018/`

여기에 `VERIFICATION.json`, native 로그, UI 증거, `DEPLOYMENT_DELTA_MANIFEST.json`,
`DEPLOY_APPROVAL_AND_ROLLBACK.md`, `OPERATING_BACKUP.tar.gz`를 보관한다.
운영 DB·개인 설정·사진·승인 원장·연결 코드는 GitHub에 올리지 않는다.
복원 시 소스·C 실행 파일·설정은 함께 복원하되, 소비된 승인을 되살리거나 Journal을
되감지 않는다. 상세 변경·SHA·복원 절차는 비공개 노트북 배포 계획을 따른다.

## 남은 검증

읽기 전용 관측에서 기존 서비스는 active/enabled, PID 24786, NRestarts 0이었다.
운영 파일과 설정·서비스 정의, Journal·승인 원장이 전후 동일했다. C request/result/
done/completed 카운터도 각각 1로 변하지 않았다. 종료 관측의 Request/Result/Done/
Mc_Run LOW는 소프트웨어 신호 확인이며 새 물리 정지 확인이 아니다.

같은 adapter boot에서 Class1 connection ID가 504.526초 동안 15→21로 증가했다.
재접속 6회의 원인은 미해결이며 timeout·lease를 늘리지 않았다. 이 현상이 실제 시험
중 발생하면 승인이 폐기될 수 있고, 통신이 불확실한 시험을 완료로 처리하지 않는다.

`PRODUCT_COUNT_NOT_ONE` 등 AI 미검출 원인은 이번 작업에서 수정하지 않았다.
새 UI·감독형 반복은 실제 카메라/PLC/벨트로 3회 확인해야 한다. cyclic Done과 Request
해제 관측만으로 PLC 프로그램의 결과 소비나 실제 벨트 재가동을 입증하지 않는다.
각 현장 시험에서 PLC 변수와 실제 움직임, Journal·이미지·AI 판정을 함께 대조한다.
