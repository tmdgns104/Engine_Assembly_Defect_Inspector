Task ID: V0-T13
Title: Journal / Evidence Persistence
Status: TODO
Depends On: V0-T12

## Purpose
실제 판정 결과를 신뢰성 있게 저장하고 근거 이미지와 함께 추적 가능한 기록을 남긴다.

## Dependencies
- V0-T12 decision output

## Allowed Changes
- SQLite schema v1 정의(inspection_id, status, reasons, timestamps, artifacts)
- 이미지/근거 경로 보존 정책 정리
- publish sequence: result persist 후 publish

## Forbidden Changes
- 판정 생성 후 저장 실패를 무시
- 영속성 실패 시 API 노출

## Implementation
- 최소 persistence 정책과 회복 동작 정리
- 저장 실패 시 ERROR 상태 흐름 설계
- 추적 필드(retry_id, session_id 등) 정의

## Verification
- journal 쓰기/조회가 일관되게 수행
- 저장 실패 시 결과 publish가 차단되는지 확인

## PASS Criteria
- `result publication`이 evidence 저장 후에만 발생
- 최소 1회 저장-조회 시나리오 작성

## Artifacts
- journal schema
- persistence sequence doc
