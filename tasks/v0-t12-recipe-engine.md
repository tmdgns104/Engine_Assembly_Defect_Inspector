Task ID: V0-T12
Title: Recipe Engine
Status: TODO
Depends On: V0-T11

## Purpose
`Recipe`(required/optional/forbidden)와 Detector 결과를 비교해 규칙 기반 상태를 계산한다.

## Dependencies
- Detector 출력 스키마
- recipes/ 디렉터리

## Allowed Changes
- 클래스별 규칙 파일 스키마 정의
- recipe 결과 집계 로직

## Forbidden Changes
- 모델 출력 직렬화 포맷과 결합

## Implementation
- `recipes/demo.yaml` 기반 로딩
- 결과 매핑으로 `missing / unexpected / low_confidence` 상태 산출

## Verification
- 필수 부품 누락 및 미검출 scenario 테스트

## PASS Criteria
- recipe-driven 판정이 DETECTION 결과와 분리되어 동작

## Artifacts
- recipe schema, 샘플 recipe
