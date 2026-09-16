# JETSON-P0-007 — OMRON Adapter

Status: **DRAFT / NOT_STARTED**. 앞 Task: P0-006. 다음 구현 Task는 미정.

## 문제와 목표

현재 실제 OMRON adapter는 없다. 검증된 Mock의 ID/ACK/heartbeat 계약을 합의한 OMRON 통신 규격으로 연결한다. 브랜드만으로 FINS/EtherNet/IP 또는 register map을 추정하지 않는다.

## 필수 입력 / 착수 경계

PLC 정확한 기종·firmware, 사용할 통신 프로토콜/endpoint, 노드/주소/메모리 영역, word/byte order, bit·register ownership, scan/timeout, request/result/ACK·session/cycle ID 표현, 동시 접근 주체, 단절/재부팅 시 처리, 물리 설비 안전회로를 확인한다. 이 정보 없이 장치 주소를 탐색하거나 출력하지 않는다.

## 예정 범위와 수용 초안

P0-005 명시 adapter를 구현하고 transport/encoding과 업무 handshake를 나눈다. emulator와 합성 패킷으로 framing/endian·범위·응답ID·오류코드·부분응답·timeout·재접속·중복·ACK 유실·counter wrap을 검증한다. P0-006 heartbeat가 기존 cycle 안전 경계를 유지하는지 확인한다. 실제 장치 연결은 별도 승인된 범위에서 먼저 읽기 전용으로 연결/주소를 대조하고, 출력·동작 시험은 구체적 I/O map과 복구 절차를 검토한 뒤에만 수행한다.

완료 증거는 emulator PASS, 실제 연결 관측, 실제 I/O/물리 동작 수용을 각각 분리한다. adapter 통신 성공만으로 모터·배출·비상정지 수용을 주장하지 않는다. app_v007·earbud package·모델·원장/이미지는 보존한다.

산출물 예정: 확정 프로토콜/I/O 명세, adapter와 합성 검증, 실제 수용 시 별도 evidence, `docs/verification/JETSON-P0-007.json`. 이번 P0-001에서는 실제 PLC 접속·제어0이며 이 초안은 장비 제어 승인서가 아니다.
