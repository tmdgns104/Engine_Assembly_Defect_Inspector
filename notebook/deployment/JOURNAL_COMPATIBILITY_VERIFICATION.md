# 과거 완료 이력과 최초 제품 승인

운영 소스 기준 commit: `bb3632120e5dda2d161ef38d25fa87a760e9b576`.
적용 Release: `engine-integrated-90a914423826735a` (113개 파일 해시 확인).
후속 시험 자료 보완 commit `866be0a9ae32092e87065b936cfb1cefcc8252fc`는 운영 `jetson/` 바이트를 변경하지 않았다.

## 변경과 보존

`jetson/src/runtime/initial_approval.py`의 `count_unfinished_inspections`는 `ACCEPTED`를 항상 차단한다. `COMPLETE`는 완료 시각과 저장 성공이 필요하다. 신규 통합 계약은 기존처럼 통합 최종판정이 필요하다.

최종판정 키가 없는 과거 기록은 `legacy_terminal_identity`로 기존 요청 계약을 적극 확인한다. 두 기존 authority 중 하나이고, 요청과 결과의 inspection ID·Runtime session·request token이 일치하며, 신규 계약/사이클/시작 정책 표식이 없어야 한다. 날짜나 특정 35개 ID 허용 목록으로 구분하지 않는다. 미확인 계약과 불완전한 기록은 차단한다.

실제 기존 완료 35건은 MOCK 요청 13건과 PLC 요청 22건이었다. 각 완료 이벤트와 저장 근거 136개 파일의 해시를 확인했다. 당시 Runtime release는 행에 기록되지 않아 확정하지 않았다. 기록 삭제·수정·가짜 final 삽입 없이 모두 보존했고, 시험 후에도 기존 전체 inspection 행이 동일했다.

`JournalAdmissionGuard`는 연결 내부 변경 수와 SQLite `data_version`으로 조회를 캐시하고, 새 운영자 승인 제출 때 무조건 재검사한다. 디스크 검사는 매번 유지한다. 승인 원장의 예약·소비 상태는 초기화하지 않는다.

## 검증 결과 (2026-10-14)

- PC 관련 회귀: 204개 중 203 PASS, Linux 전용 1 SKIP. 실행 파일 권한 묶음 검사 1 PASS.
- 시험 경로 이식 및 화면 회귀: 26 PASS (위 회귀와 중복 포함).
- Jetson: 204개 항목 PASS. 처음 누락된 시험 예제·기준 파일·모델 경로를 보완했으며, 최종 203개 PASS와 남은 1개 재검사 PASS를 합친 결과다. 운영 구현을 바꾸거나 실패 조건을 완화하지 않았다.
- 검사 전: 미완료 차단 0, 최초 승인 challenge READY, 카메라·필수 조립 모듈 준비, Request/Result/Done LOW.
- 현장 감독하 실제 제품 1건: 새 원본 3프레임, Journal 저장, Result 다음 Done, PLC 요청 해제·불량 기억·컨베이어 출력 재개를 확인했다. 작업자도 정지 후 재가동과 최종 STOP을 확인했다.
- **AI 정상 판별은 실패했다.** 기존 검사 FAIL, 필수 조립 모듈 `KeyError: 'integrity'`로 ERROR, 최종 ERROR였다. 승인된 `PASS_OK_OTHER_NG_V1` 정책에 따라 PLC NG로 보냈고, 내부 ERROR를 FAIL로 덮어쓰지 않았다. 합성 시험 결과는 사용하지 않았다.
- 결과 송신과 Done 송신은 각각 1회였다. 소비 전용 ACK 변수가 없는 계약이므로 C 전송 ACK와 PLC 공정 상태 변화 증거를 구분한다.
- 시험 후 통신 재접속으로 사용한 승인이 폐기됐다. 추가 승인/검사/결과 재발행은 하지 않았다. 단일 사이클 성공은 연속 운전 신뢰성의 증거가 아니다.

## 운영 및 남은 범위

전체 Runtime은 `current/`에서 `engine-inspector.service` 하나가 감독한다. Python과 OpENer를 같은 Release로 보존한다. TASK-015 전체 화면 추적 및 TASK-011 통신 경로는 포함·활성이다. TASK-013 가로 관측과 TASK-014 원본 진단은 포함됐지만 현장 승인/자격을 자동 부여하지 않는다. 단일 제품 허가는 연속 자동 재승인이 아니다.

이번 수정 범위에서는 조립 모듈 오류, 통신 재접속 원인, 가로 clearance 현장 자격, 연속 제품, 실제 재부팅 및 노트북 OFF 검증을 해결했다고 하지 않는다. 운영 DB·장치 개인 설정·승인 기록·현장 원본은 이 저장소에 게시하지 않는다.

복구는 노트북에 검증된 이전 `current` 전체 패키지·설정·unit을 이용하고 현장 정지 상태에서 정상 서비스 중지/전환/시작 순서로 한다. 기존 Journal과 이미 소비한 승인 원장은 과거 snapshot으로 덮어쓰지 않는다. DB 스키마 변경은 없다.
