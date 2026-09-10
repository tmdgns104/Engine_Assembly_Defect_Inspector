Task ID: V0-T13
Title: Decision Engine
Status: TODO
Depends On: V0-T12

## Purpose
이미지 품질, Detector, Recipe 결과를 결합해 최종 `PASS/FAIL/REVIEW/ERROR` 상태를 산출한다.

## Dependencies
- V0-T11, V0-T12 완료

## Allowed Changes
- 결정 규칙 우선순위 정의
- REVIEW/ERROR 안전 판정 보강

## Forbidden Changes
- 임계치 하드코딩 분산
- Detector/Camera 구현에 결정 로직 주입

## Implementation
- 정책 테이블 기반 점수/이유코드 반환
- 가림/흐림/어두움 등은 즉시 FAIL이 아닌 REVIEW 경로 우선

## Verification
- CAP/PIPE 예시 시나리오 3종 이상 검증

## PASS Criteria
- 네 상태가 명확히 구분되고 이유코드가 출력됨

## Artifacts
- decision 규칙 문서
