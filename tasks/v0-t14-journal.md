Task ID: V0-T14
Title: Journal and Persistence
Status: TODO
Depends On: V0-T13

## Purpose
검사 결과를 추적 가능한 SQLite Journal로 저장하고 조회 인터페이스를 정의한다.

## Dependencies
- V0-T13 완료

## Allowed Changes
- 검사 이벤트 스키마 정의
- 실패/리뷰/에러 이력 저장

## Forbidden Changes
- 로그 저장을 모델 추론 루프에 동기화로 결합

## Implementation
- SQLite schema v1 정의(inspection_id, timestamp, status, reasons, artifacts)
- 간단한 조회/백업 경로 설계

## Verification
- 최소 1건 저장/조회 동작 확인

## PASS Criteria
- 결과 이력이 손실 없이 누적

## Artifacts
- journal schema 문서
