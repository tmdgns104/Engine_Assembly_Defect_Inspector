Task ID: V0-T15
Title: Manual Request + Mock PLC Adapter
Status: TODO
Depends On: V0-T14

## Purpose
수동 검사 요청과 Mock PLC 경로를 동일 request contract로 연결한다.

## Dependencies
- V0-T14 API/HMI 기본 구성

## Allowed Changes
- inspection request schema 정리
- MockPLC adapter 스텁 및 상태 전이 정의
- V2로의 adapter 교체 지점 정리

## Forbidden Changes
- V2 제어 동작을 V0에서 실제 PLC로 구현
- request contract와 PLC 동작을 분리

## Implementation
- request/response 공통 구조 정리
- manual trigger + mock control flow 문서화

## Verification
- mock request가 동일 계약으로 처리되는지 점검

## PASS Criteria
- 요청/제어 계약이 분리 없이 문서화
- V2 교체 포인트 명확

## Artifacts
- mock plc adapter spec
