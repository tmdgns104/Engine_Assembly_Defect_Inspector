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
