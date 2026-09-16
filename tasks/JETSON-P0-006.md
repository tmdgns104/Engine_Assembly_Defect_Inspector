# JETSON-P0-006 — Heartbeat

Status: **DRAFT / NOT_STARTED**. 앞 Task: P0-005. 다음: P0-007.

## 문제와 목표

현재 공유 메모리 Worker pulse와 5초 Service 감시는 있다. PLC peer heartbeat/watchdog는 없다. P0-005 adapter 계약에 peer 생존과 통신 freshness, session 변경·복구 handshake를 추가한다.

## 예정 계약

생산자/관찰자·counter 또는 toggle·증가/중복/역행·clock domain·주기·최대 지연·stale 판단·통신 단절 시 상태 전이를 명시한다. 주기/timeout은 PLC scan과 지연 예산을 확인한 뒤 고정한다. Worker 살아 있음, 카메라 새 프레임, inference 진행, PLC 통신 생존은 서로 다른 상태다. 원래 Worker heartbeat는 inference 멈춤을 단독으로 증명하지 못하므로 deadline/진행 여부를 함께 본다.

## 수용 초안

합성 clock으로 정상/지연/유실/중복/멈춘 counter/랩어라운드/재부팅/session 변경/한쪽만 살아 있는 상황을 시험한다. 반복된 오래된 heartbeat가 liveness를 갱신하지 않아야 한다. stale 상태에서 새 cycle을 막고 진행 중 취소/보류·늦은 PASS 거부·명시 복구·자동 START 금지를 검증한다. Mock에서 재현 가능 로그/metrics를 남긴다. watchdog은 안전 PLC/비상정지 기능의 대체물로 선언하지 않는다.

산출물 예정: heartbeat/watchdog 계약, Mock 시험, `docs/verification/JETSON-P0-006.json`. 실제 PLC 설정·출력, systemd 설치·재시작 정책 변경, MQTT는 제외한다. 하드웨어 단계는 P0-007의 별도 허가/검증 범위다.
