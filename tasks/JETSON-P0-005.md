# JETSON-P0-005 — Mock PLC

Status: **DRAFT / NOT_STARTED**. 앞 Task: P0-004. 다음: P0-006.

## 문제와 목표

MockCell/ServiceMockPort 및 RESULT_ACK/CYCLE_ACK는 이미 있다. 이를 다시 구현하기보다 실제 PLC 교체에 필요한 명시적 adapter 계약·가상 I/O·장애 주입을 추가한다. Mock 결과를 실제 모터/배출 결과로 기록하지 않는다.

## 예정 범위

기존 `src/control/mock_cell.py`, `apps/edge_service/mock_port.py`, request/session/cycle ID와 durable journal을 재사용한다. connect/status/request/result/ACK/reset/recovery의 의미·data ownership·재시도·멱등성·호출 timeout·프로토콜 오류를 명시한다. `REQUEST_ACK`, `RESULT_ACK`, `CYCLE_ACK`, PC event/asset ACK를 구별한다. 최초 구현은 메모리 또는 명시적으로 격리한 emulator다.

## 수용 초안

- START 유지/중복 request/중복 result/ACK 유실·재전송/순서 역전/오래된 session/재접속/재시작/terminal pending을 deterministic clock으로 시험한다.
- 저장되지 않은 결과, 취소 후 PASS, 오래된 session 결과는 release하지 않는다. 동일 결과 소비·가상 RELEASE는 한 번만 기록한다.
- FAIL/REVIEW→HOLD, ERROR→FAULT, 명시 복구 후 자동 START 없음이라는 현재 동작을 보존한다.
- 실제 camera/model 없이 fake worker·임시 DB로 계약 검증을 끝내고 기존 Mock/Service/Journal/PC 회귀와 원본 hash를 확인한다.

산출물 예정: adapter 계약, 기존 Mock 확장과 장애 주입 시험, `docs/verification/JETSON-P0-005.json`. 실제 PLC socket/레지스터/코일·모터·센서 제어0. UI mock 실행도 현재 운영 DB에 자동 수행하지 않는다.
