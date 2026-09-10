Task ID: V0-T16
Title: REST API
Status: TODO
Depends On: V0-T14

## Purpose
검사 호출/상태 조회/Health Check를 제공하는 최소 API 사양을 정리한다.

## Dependencies
- Journal, Decision Engine

## Allowed Changes
- 엔드포인트 계약 설계
- 응답 스키마, 상태코드 정의

## Forbidden Changes
- 장치 제어/파라미터를 API에서 직접 하드코딩

## Implementation
- health, trigger, history, image snapshot endpoint 설계
- 입력 유효성 검사 및 에러 응답 규격 정의

## Verification
- 스키마 문서와 예시 요청/응답 정합성 확인

## PASS Criteria
- Web HMI와 결합 가능한 API 계약 초안 존재

## Artifacts
- API 계약 문서
