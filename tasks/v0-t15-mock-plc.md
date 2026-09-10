Task ID: V0-T15
Title: Mock PLC Adapter
Status: TODO
Depends On: V0-T14

## Purpose
PLC 연동 경로를 mock 인터페이스로 분리해 V2 전환 시 실제 PLC Adapter로 교체할 수 있도록 한다.

## Dependencies
- control/ 인터페이스 구조

## Allowed Changes
- mock 어댑터 상태/요청 모델 정의
- 인터럽트/응답 시뮬레이션

## Forbidden Changes
- Runtime 판정 로직에서 PLC 신호를 직접 생성

## Implementation
- `IPlcAdapter` 유사 추상화 설계
- 요청/응답 플로우 및 타임아웃 정책 샘플화

## Verification
- Mock 동작에서 요청-응답 스텁 테스트

## PASS Criteria
- PLC Adapter 교체 지점이 문서화됨

## Artifacts
- Mock PLC adapter 스펙
