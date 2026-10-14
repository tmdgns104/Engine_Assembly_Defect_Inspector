# TASK-020 — PLC 주도 반복 검사 및 IPC 검증

상태: **ISOLATED_VERIFIED / STOP_FOR_FIELD_DEPLOYMENT_APPROVAL**. 운영 배포·실제 3제품 시험은 수행하지 않았다.
기준 소스: `45c36945928cdcbf04fa667d123a7b5342184adc`.
실제 운영: `engine-integrated-4920568fe3750b64` (이번 작업으로 변경하지 않음).

## 결과 정책 — 사용자 결정 유지

| 저장된 통합 판정 | PLC Result | Done |
|---|---:|---|
| PASS | 0 (OK) | Result-only 송신 다음 cyclic 패킷에서 1 |
| FAIL | 1 (NG) | 동일 |
| REVIEW | 1 (NG) | 동일 |
| ERROR | 1 (NG) | 동일 |

화면과 Journal에는 원래 REVIEW/ERROR와 이유를 보존한다. 제품 구분이 불확실한 **유효한 접수 요청**은 제한시간 후 ERROR와 `NO_ACTUAL_INSPECTION`을 저장하고 NG·Done으로 완료한다. 이를 실제 AI 검사 성공 또는 제품 이탈 성공으로 표시하지 않는다. 이전 결과를 재사용하지 않는다.
STOP/E-STOP, 연결·요청 신선도 상실 또는 저장 실패로 취소된 요청에는 늦은 결과를 보내지 않는다. 이 경우 임의 ERROR를 만들어 벨트를 재가동하지 않는다.

## 승인 의존성 제거

기존 FIRST_PRODUCT_ONLY/EXPLICIT_ONE_SHOT_V1은 초기 현장 1회 시험, SUPERVISED_REPEAT_TEST는 제품별 감독 시험 범위를 제한하기 위해 추가됐다. TASK018 자동 경로도 AutomaticAdmission이 매번 ID를 생성하고 IPC automatic_arm을 보내야 하므로 사용자가 요구한 PLC 주도 구조와 달랐다.

정상 `PLC_AUTOMATIC_REPEAT`에서 다음을 제거했다.

- `AutomaticAdmission` 구현과 인스턴스, `automatic_arm` 및 C `CommAutomaticArm`, IPC command 6.
- 제품별 approval/admission ID·challenge·request.json·승인 원장 접근과 수동 재무장.
- `initial_authorization`을 자동 정책과 일치시켜야 한다는 조건.

과거 승인/ABORTED/Journal은 보존한다. InitialApproval/SupervisedApproval, CLI와 유지보수 인증은 과거 시험 및 유지보수 호환 경로에만 남으며 자동 모드에서는 생성·사용하지 않는다. 자동 모드의 C는 기존 one-shot/supervised arm도 거부한다. `runtime_session`, 연결 ID, 요청 번호 및 검사 ID는 결과의 출처를 묶는 식별자이며 사람이 발급하는 검사 권한이 아니다.

## 정상 상태 전이

1. 서비스·카메라·저장소 정상, 새 연결의 실제 PLC 정지 기준(Request=0/Mc_Run=0/출력=0)을 관측한다.
2. 현장 START 이후 RUN 상태에서 Request LOW를 보고 새로운 HIGH를 접수한다.
3. 현재 연결/요청에 새 검사 ID를 연결한다. 실제 Worker → 원시 Journal → AssemblyInspector → 통합 최종판정 저장 후에만 결과를 발행한다.
4. Result-only가 실제 송신된 다음 cyclic 패킷에서 Done을 올린다.
5. Request 해제 후 Result/Done 4바이트를 모두 0으로 내리고 reset 송신을 확인한다. 다음 PLC Request를 자동으로 받는다.

이전 취소 요청 때문에 누적 request_count와 completed_count가 다를 수 있다. 새 IPC snapshot의 `transaction_settled` 비트는 **현재 연결·요청의 완료**를 나타내며 누적 수치가 같다는 가정을 제거한다. IPC 길이/버전(v3/160B), PLC Assembly/EDS/RPI는 유지한다. Python과 C는 같은 Release로 적용해야 한다.

제품 구분에는 기존 ProductPassage의 연속 Track 이동·출구 통과·1.2초 출구 관측을 사용한다. 화면 전체가 비었는지나 가로 Area Clearance UNKNOWN을 접수의 절대 조건으로 사용하지 않는다. 새로운 Request만으로 새 제품이라고 단정하지 않는다. Assembly150에는 포토센서 원신호가 없다.
서비스 재시작 시 마지막 실제 제품에 대한 기존 `AUTOMATIC_PRODUCT_SEPARATED` 기록이 없으면 `PREVIOUS_RUNTIME_PRODUCT_EXIT_UNPROVEN`을 유지한다. 재시작 자체를 이탈 근거로 삼지 않는다. 과거 제품 보류를 해제할 유지보수 근거가 없는 상태에서 실제 AI 반복검사를 가능하다고 보고하지 않는다.

## Class1/IPC 조사 결과

- 운영 수신 파일 400개 샘플/약 20.27초 읽기 관측에서는 연결 번호 8과 무출력이 유지됐다. 짧은 상태 파일 관측이며 패킷 캡처 또는 장시간 안정성 검증이 아니다.
- 기존 기록에서 IPC_DISCONNECTED의 health age 약 980ms와 약 0.52ms 뒤 Class1 timeout이 확인됐다. 선후관계만으로 최초 원인을 확정할 수 없다.
- C의 IPC poll이 수신 전 호출자의 오래된 시각으로 명령 freshness를 비교하는 오류를 격리 재현했다. 실제 수신 시각을 다시 읽어 비교하도록 수정했다. 진짜 미래/오래된/다른 연결 명령은 계속 거부한다. 이 오류가 과거 현장 ValueError의 유일 원인이라고 단정하지 않는다.
- bounded 진단에 IPC poll/snapshot 최대 간격, 명령 age·거부 분기, IPC 단절 원인, 상태/이벤트 파일 쓰기 지연을 추가했다. Python은 최초 IPC 실패 이유를 재접속 뒤에도 보존한다.
- Class1 최초 원인, 실제 UDP 누락·스케줄링 지연·PLC 온라인 오류는 **미확정**이다. RPI·timeout·lease를 늘리지 않았다.

## 검증 범위

- 최종 Jetson ARM64: Python **287개 PASS / 92.418초**. 기존 TASK017 무결성, TASK019 저장/health/ABORTED 회귀 포함.
- C: 초기 22개·감독형/자동형 상태기계(ASan/UBSan), IPC 시각·실제 AF_UNIX 손실 및 freshness/context 거부, 전체 OpENer 빌드 PASS. 기존 C 변환 경고는 남아 있으며 warning-free 빌드라고 표시하지 않는다.
- 승인 없는 3제품: 서로 다른 요청/검사 ID, 각 3개 PNG 및 SHA, 실제 소프트웨어 소유자 전체 경로, PASS/REVIEW/FAIL 각각 1회 Result/Done/reset. ERROR는 별도 4판정 소유자·C/IPC 회귀에서 NG/Done 확인.
- 3제품 경로 원시 저장 609.49~621.02ms, health 갱신 최대 간격 130.95ms. 원시/최종 commit에 각각 550ms 지연을 넣었다. 4판정 저장 회귀의 최대 health 간격은 149.28ms. 단일 격리 실행의 관측이며 현장 부하 보장은 아니다.
- 정상화한 최종 소스와 ARM64 실행 파일의 SHA를 대조했다. 산출물 `CANONICAL_RESULTS.tar.gz` SHA-256: `572c24024c10ff250ba5e3f533b866874fc567a006488761628360550233c4f7`.
- 개발 바이너리 SHA-256: `127cedc473705479f6c135b513b6f9e8f86733b0eb89b50361a53f7ef1be98ac`.
- 실제 운영 바이너리 SHA-256: `8506ffc28970ae731f02a5aab97b98e8d1d0b199c51b060450facfffc842b82e`. 서비스 PID/재시작 횟수, current/config/unit 파일 SHA, 검사 행 상태 및 승인 행 해시 전후 동일.
- 상세 증거는 노트북 `runs/engine_standalone_plc_autostart_001/v001_20261007T052746Z/tag_data_link_008/class1_ipc_020/`에 보존한다. 운영 DB·현장 이미지·원시 상태 로그는 GitHub에 포함하지 않는다.
실제 소프트웨어 소유자(Worker 프로세스, Runtime, SQLite Journal, AssemblyInspector, Python/C AF_UNIX)는 실행했다. 카메라·검출기·모델·PLC는 합성 경계로 대체했으며 실제 카메라를 열거나 실제 PLC 패킷을 보내지 않았다. 이 결과는 현장 AI 정확도·실물 이탈·컨베이어 성공이 아니다.

## 변경 파일과 배포 준비

- C `engine_commissioning.c/.h`: PLC 기준/요청 상태기계, 결과 reset 및 요청별 완료 표식.
- C `engine_ipc.c/.h`, `engine_callbacks.c.inc`: arm 제거, 시각 비교 수정, bounded 진단.
- Python `opener_cyclic.py`, `inspection_start.py`, `standalone.py`, `standalone_web.py`: 승인 없는 요청 처리, 실제 상태 점검, 제품/Journal 보존, 모니터 상태.
- `automatic_admission.py`: 삭제. 과거 DB·원장 삭제는 하지 않는다.
- 자동/IPC/실제 소프트웨어 소유자 회귀 테스트 추가·수정.
- `runtime_allowlist.json`: 이미 존재하는 저장·복구·health·ProductPassage·유지보수·Assembly 증거 모듈 7개 누락을 보완. 새 알고리즘 추가가 아니다.
- `OpENer` 및 `source_profile/PROFILE.json`: 이번 ARM64 빌드와 일치하도록 개발 저장소에서 갱신. 실제 current는 교체하지 않았다.

승인 후 적용할 설정 차이는 cycle_admission=`PLC_AUTOMATIC_REPEAT`, 기존 제품별 initial_authorization 제거, 새 C SHA이다. 실제 운전 자격·PLC 온라인 동등성·STOP/timeout 복구·출구 관측 검증 값은 증거 없이 TRUE로 만들지 않는다. 이는 현장 채택 조건이며 매 제품마다 발급하는 권한이 아니다. 이번 작업에서 운영 설정은 변경하지 않았다.

배포 전 현장 정지를 새로 확인하고 current 전체·설정·systemd 정의·release/SHA·SQLite backup API로 일관된 Journal/승인 원장을 노트북에 회수하여 검증한다. 기존 배포 도구로 단일 패키지를 만들고 필수 파일 목록·새 binary SHA·manifest를 대조한다. 승인된 정상 서비스 종료 후 staging 전체를 current로 전환하고, 단일 서비스/카메라/OpENer·기준 PLC LOW·건강 상태를 확인한다. 실행 파일 일부를 섞어 덮어쓰지 않는다.
실패 시 정지 상태에서 노트북의 직전 전체 실행본과 설정을 복원한다. 운영 Journal/승인 소비 이력은 초기화하거나 이전 DB로 되돌리지 않는다. 재접속 후 새 물리적 정지 기준과 요청이 필요하며 과거 결과를 재송신하지 않는다.

## 현장에 남은 확인

새 승인 이후 감독하에 서로 구분되는 제품 3개를 순서대로 이송한다. 매 제품 웹 승인·코드·CLI 없이 신규 Request/검사 ID/3프레임/원시·통합 Journal/Result→다음 Done/Request 해제/실제 재가동을 대조한다. STOP/E-STOP·연결 장애·저장 장애에서는 취소 뒤 늦은 출력을 차단하는지 따로 확인한다.

실물 출구 관측, PLC 온라인 로직 동등성·검사 timeout/STOP 복구, Class1 장시간 안정성, 실제 3제품 검사, 재부팅·노트북 OFF는 이번 작업에서 NOT_RUN이다. 현재 관측 큐는 최신 프레임을 유지하면서 누락될 수 있고 ProductPassage는 연속 시퀀스를 요구하므로 실제 FPS/부하에서 이탈 증거가 충분한지 확인해야 한다. 부족하면 누락 없는 제품 궤적/출구 관측 또는 PLC에 연결되는 배출 센서 등 추가 근거가 필요하다. 이번에 검증 조건을 삭제하거나 새 관측 알고리즘을 개발하지 않았다.

최종 상태: **STOP_FOR_FIELD_DEPLOYMENT_APPROVAL**. 현장 배포·PLC 출력·새 START는 별도 승인 전 수행하지 않는다.
