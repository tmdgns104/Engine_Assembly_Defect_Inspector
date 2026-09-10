Task ID: V0-T18
Title: Failure Injection & Automated Tests
Status: TODO
Depends On: V0-T17

## Purpose
주요 실패 모드(카메라 오작동, 품질 실패, 추론 예외)에서 시스템의 REVIEW/ERROR 동작을 자동화한다.

## Dependencies
- V0-T11~V0-T17

## Allowed Changes
- 실패 케이스 fixture 추가
- pytest 기반 smoke test 구성

## Forbidden Changes
- 실제 하드웨어 제어로의 테스트 의존

## Implementation
- Detector/Camera/Quality/Decision 경로별 fail 케이스 작성
- health/결과 consistency 테스트 추가

## Verification
- 최소 각 1개 실패 시나리오 통과

## PASS Criteria
- REVIEW/ERROR 경로가 예측 가능하게 동작
- 테스트가 CI 없이 로컬 실행 가능

## Artifacts
- tests 디렉터리 테스트 스켈레톤
