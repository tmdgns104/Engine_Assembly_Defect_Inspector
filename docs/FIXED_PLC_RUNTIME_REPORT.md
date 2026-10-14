# 기존 PLC 고정 — 반복검사 Runtime 수정

상태: 소프트웨어 검증 PASS, 운영 전환 및 실제 최대 3제품 시험 진행 중.
PLC/EDS/4·8·10B/RPI/모델/판정 임계값은 변경하지 않았다.

## 수정 근거와 범위

- 정상 운전 준비와 무인 장애 복구 자격을 분리했다. `_profile_ready()`는 현재 calibration 일치, 명시적 좌/우 출구, 기존 passage 정책을 확인한다. 온라인 PLC 동등성·독립 timeout·현장 이탈·Class1 장기 안정성은 미검증 제한으로 따로 표시한다. 미검증 값을 TRUE로 만들지 않는다.
- 기존 PLC 주도 상태기계를 유지한다. 새로운 Request는 C의 boot/connection/request 토큰으로 구분한다. 제품별 웹·CLI 승인, 파일 생성 또는 automatic_arm 호출은 추가하지 않았다.
- `product_context_recovery.py`는 과거 마지막 제품 문맥에만 독립적인 `MAINTENANCE_PRODUCT_CONTEXT_CLOSED` 영수증을 추가한다. 정지 신호·유휴 소유자·DB 무결성·원본/최종판정 해시·현장 제품 처리 확인을 검증하고 commit 직전 PLC 문맥을 다시 비교한다. 정상 제품마다 쓰는 경로가 아니다. 원래 검사·ABORTED·승인 기록은 보존한다.
- 유지보수 호출은 기본 비활성인 단일 인증 POST이며 정상 `/line` 운전과 분리된다. 웹 승인 UI가 필요하지 않다. 다른 POST 보호는 유지한다.
- `consumed_frames.py`는 Runtime이 실제로 소비한 프레임 1,024개 이하의 ID/sequence/시간/epoch/generation/bbox를 기록한다. HTTP 표본의 누락을 Runtime 누락으로 해석하지 않는다. 이미지·tensor 복사나 별도 카메라 실행은 없다.
- OpENer의 JSON 파일 I/O를 단일 writer thread로 옮겼다. cyclic 소유자는 고정 크기 event queue와 status snapshot에 복사만 한다. event 순서, 상한, 저장 실패 차단은 유지한다. 중간 status snapshot만 병합할 수 있다. 출력·Run/Idle·Result→다음 패킷 Done·lease는 그대로다.

## 재현 및 검증

실제 application callback을 컴파일한 무 NIC fixture에서 파일 fclose에 250ms 지연을 넣었다. 기존 callback 두 번은 0.501630s, 수정 후 0.000058s였다. 비동기 파일 저장 실패는 `EVIDENCE_WRITE_FAILURE` 및 무출력으로 차단됐다. 이는 callback blocking 재현·수정의 근거이며 현장 Class1 timeout 전체 원인 확정은 아니다.

- ARM64 Runtime 회귀: 297개 PASS, 93.806s.
- ARM64 배포 회귀: 31개 PASS, 6.786s.
- C 초기/감독/자동 상태기계, ASan/UBSan, AF_UNIX IPC clock 및 Result/Done 순서 검사 PASS.
- 실제 Worker/저장/Assembly/IPC 소유자를 쓰는 격리 fixture의 네 판정·지연 저장·3제품 서로 다른 ID 검사 PASS. 카메라/PLC 입력은 fixture이며 현장 성공이 아니다.
- calibration 불일치, 실제 미완료 Journal, 낮은 디스크, 조작된 복구 영수증, commit 중 PLC 문맥 변경, 인증 없는 유지보수, STOP/lease/중복 출력 차단 유지.
- `INTEGRATED_AI_OFFLINE` 설치 확인: 174파일, 네 조립 classifier 및 기존 TensorRT/Pose 포함. `CORE_MOCK_ONLY`는 운영에 사용하지 않는다.
- 검증 중 운영 current/config/unit/PID/검사 목록/승인 원장 불변 확인.

새 ARM64 C SHA-256: `63ca4b16db530eecc9f95155a40cf758b291a590d85894dc8e9faf7aa0b2f4a4`.

## 현장 적용 원칙

사용자가 현장 정지·작업 영역·방호·STOP/E-STOP·감독과 서비스 전환 후 최대 3제품 시험을 승인했다. 카메라 화면의 실제 이동 방향은 오른쪽→왼쪽으로 확인했다. 실제 START는 현장 사용자가 누른다.

기존 current가 Git `45c36945928cdcbf04fa667d123a7b5342184adc`와 일치함을 확인했다. 서비스 정상 종료 후 current/설정/unit/SHA와 SQLite backup API의 Journal·승인 원장을 노트북에서 읽어 검증한 뒤 전환한다. 복원은 코드·설정만 대상으로 하며 검사/사진/ABORTED/소비 이력을 되돌리지 않는다.

독립 PLC 응답 timeout과 온라인 전체 로직 동등성은 미검증이다. 저장/통신 장애에서는 늦은 결과를 차단하며 현장 STOP·진단이 필요하다. 이것을 정상 제품마다 소프트웨어 권한을 발급하는 조건으로 사용하지 않는다. 실제 ProductPassage·3제품 자동 반복·Class1 장기 안정성은 현장 증거가 확보되기 전 PASS로 표시하지 않는다.

원본 증거는 노트북 `runs/.../tag_data_link_008/deployment_readiness_021/fixed_plc_followup/`에 보존한다. 운영 DB·사진·개인 설정·인증정보는 이 저장소에 포함하지 않는다.

## 첫 현장 실패와 조립 프로세스 분리

실제 원시 3프레임 저장은 383.552ms에 완료됐다. 조립 검사 중 Runtime health 갱신이 484.036ms 지연돼 기존 400ms lease가 만료됐다. C는 PYTHON_NOT_READY로 결과 발행을 취소했다. 이후 나타난 JOURNAL_UNFINISHED_INSPECTION은 취소의 결과이므로 미완료 차단을 제거하지 않았다. 이 요청에는 Class1 timeout이 없었다. 조립 결과는 뒤늦게 REVIEW로 저장됐으며 통합 최종판정과 Result/Done은 생성되지 않았다.

카메라를 하나만 소유하는 실제 Runtime과 보존된 3프레임 조립 검사를 함께 실행한 격리 재현에서 frozen feature matching의 knnMatch 동안 interpreter 전체 지연을 관측했다. `assembly_process.py`는 같은 동결 조립 코드를 별도 spawn 프로세스에서 실행한다. 부모는 완료 ID와 fsync 이후 DURABLE 응답을 확인한 뒤 결과를 읽는다. 자식은 카메라와 PLC를 열지 않으며 종료·실패·ID 불일치 시 readiness를 내린다. 모델, 임계값, 판정 정책, 400ms lease는 유지한다.

실제 카메라/저장 원본을 사용한 동일 조건 재처리의 health 최대 간격은 변경 전 306.927ms, 변경 후 134.582ms였다. 단일 재현 측정이며 전체 Class1 안정성이나 현장 성공의 증거는 아니다. ARM64 집중 회귀 84개가 통과했고 비공개 PNG fixture 1개는 해당 테스트 경로에서 제외됐다. 실제 저장 원본은 별도의 재처리에 사용했다. 별도 프로세스의 native GIL을 프레임마다 550ms 점유시킨 3제품 C/IPC 종단 테스트도 요청/결과/Done 각 3회, 승인 0회로 통과했다.

`aborted_recovery.py`는 PLC_AUTOMATIC_REPEAT의 실제 요청·취소 이벤트, 무출력, 다른 adapter boot, 현재 STOP·유휴 소유자를 검증하는 경로를 추가한다. 존재하지 않는 승인 기록을 만들지 않는다. 원래 inspection/사진/조립 결과와 승인 원장은 그대로 보존한다. 복구는 독립 ABORTED 영수증만 추가하며 결과 재전송이나 새 검사 권한을 생성하지 않는다.

서비스 종료 상태의 직전 current/설정/unit/원장/실패 증거 158파일을 노트북에서 해시·SQLite 무결성으로 검증했다. 백업 SHA-256: `b6f8bf95a9e58988679d3751dcb51949eed985fbb6a925d4f7cb40dea7f4f10d`. 복원 시 코드·설정만 복원하고 현재 Journal/사진/복구 이력은 되돌리지 않는다. 수정본의 실제 PLC 재시험은 진행 전이며 결과는 별도로 기록한다.

## 두 번째 현장 시도: 요청 접수 전 health 지연

조립 프로세스 분리본 `engine-integrated-82d677f3208eaa27`을 실제 적용했다. 기존 실패 검사에는 실제 무출력·취소·정지 근거에 따라 독립 ABORTED만 추가했다. 원래 결과/PNG/승인 이력은 보존했고 미완료 차단은 1건에서 0건이 됐다.

다음 실제 START에서는 제품이 처음 보인 뒤 health 간격이 669.586ms로 늘어났다. IPC는 410.085ms 시점에 HEALTH_LEASE_EXPIRED를 기록했다. 이후 PLC Request가 들어왔지만 C는 이미 DISARMED였다. 새 검사 ID/AI 검사/Result/Done은 모두 0건이며 현장 성공이 아니다. 사용자는 STOP과 실제 정지를 확인했고 서비스는 정상 종료했다.

VISION_PASSAGE_STARTED와 PRODUCTION_TRACK_STATE 기록 사이에 403.985ms가 있다. 정지 카메라 재현에서는 전체 670ms가 재현되지 않았다(최대 239.599ms). 복사 SQLite의 실제 commit 측정에서는 WAL 자동 checkpoint 시 166.566ms, 이후 readiness 재검사 100.195ms가 측정됐다. 따라서 동기 추적 로그와 반복 기록 검사가 주기 갱신을 방해할 수 있다는 근거는 있으나, 현장 670ms 전체를 하나의 확정 원인으로 단정하지 않는다.

최소 수정은 PLC_AUTOMATIC_REPEAT의 세 관측용 이벤트(VISION_PASSAGE_STARTED, PRODUCTION_TRACK_STATE, PRODUCTION_DEPARTURE_EDGE_ASSESSED)를 기존 크기 제한 메모리 trace로 옮긴 것이다. 각 frame의 검사 ID/요청 결합, 실제 요청/검사/최종판정/제품 이탈 확정/중단의 durable 기록은 유지한다. 특히 AUTOMATIC_PRODUCT_SEPARATED는 여전히 Journal에 저장한다. 과거 기록은 지우지 않으며 모델/판정/STOP/통신 lease와 C 바이너리는 바꾸지 않는다. 추적 진단이 SQLite를 변경하지 않으므로 정상 관측마다 과거 원장을 재검사하는 연쇄 비용도 사라진다.

개발 재현 스크립트와 회귀 테스트는 운영 current에 배포하지 않는다. 노트북 및 장치의 임시 verify 폴더에서만 실행하며, 모의 입력은 실제 PLC/AI 성공으로 세지 않는다. 500ms 저장 지연을 넣은 테스트는 수정 전 1.619s로 실패했고 수정 후 통과했다. 요청/최종판정/이탈 확정/중단 이벤트의 durable 저장과 메모리 상한도 검증한다. 실제 현장 재시험은 아직 필요하다.

이번 정상 종료 후 백업 159파일은 노트북에서 모두 해시 및 SQLite 무결성을 확인했다. SHA-256: `ceba32b37fe0e28266088c0f35db83aff7b36b836342b37513f830be155b2a48`. 복원 대상은 코드·설정·서비스이며 최신 검사/사진/ABORTED/소비 이력은 되돌리지 않는다.

최종 집중 ARM64 회귀: 64개 실행, 실패 0, 비공개 PNG fixture 1개 skip. C/IPC 합성 3제품은 request/result/done/completed 각각 3, 별도 승인 0을 확인했다. install --check-only --require-assembly 및 INTEGRATED_AI_OFFLINE 패키지 생성도 통과했다. 패키지 175파일, SHA `1a962d3582de4a030d99b13f4a293fa7ab2e37f09690e8f51c18bcdb207c95d3`. 실제 카메라 단일 소유자·PLC 미연결 정지 진단에서 추적 처리 최대 2.639ms, 상태 갱신 최대 206.802ms였다. 이는 실제 PLC 재시험 성공 근거가 아니다. 배포 변경은 standalone.py 한 파일과 release 메타데이터이며 C/현장 설정은 그대로 유지한다.
