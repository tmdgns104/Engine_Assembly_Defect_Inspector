Task ID: V0-T17
Title: Failure / Recovery Tests
Status: TODO
Depends On: V0-T16

## Purpose
불안정 상황에서 PASS/REVIEW/ERROR 처리가 일관되게 동작하는지 검증한다.

## Dependencies
- V0-T16

## Allowed Changes
- 실패 주입 케이스(카메라 미사용 가능, 프레임 불량, detector 예외, 저장 실패, 중복요청, timeout 등) 추가
- 재시작/복구 동작 체크

## Forbidden Changes
- 실제 물리 장치 고장 주입 또는 PLC 하드웨어 변경
- 불완전 상태에서 PASS 허용

## Implementation
- 최소 실패 시나리오 8종 수립
- each scenario에 대한 기대 상태 map 작성

## Verification
- 모든 시나리오가 REVIEW/ERROR 경로를 유도
- PASS는 불완전 상태에서 유출되지 않음

## PASS Criteria
- 실패 인젝션 케이스 문서와 테스트 체크리스트 완성
- Recovery 로그가 남음

## Artifacts
- failure test suite
- recovery matrix
