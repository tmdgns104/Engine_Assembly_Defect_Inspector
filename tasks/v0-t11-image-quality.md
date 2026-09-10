Task ID: V0-T11
Title: Image Quality Gate
Status: TODO
Depends On: V0-T10

## Purpose
가림/흐림/밝기/노이즈/초점 등으로 인한 판정 불신뢰를 조기에 분리한다.

## Dependencies
- Camera Adapter 기본 동작

## Allowed Changes
- quality score 지표 추가(블러/노출/크기/포커스)
- REVIEW/ERROR 임계치 정의

## Forbidden Changes
- 판정 모델 추론 결과를 과도하게 덮어쓰기

## Implementation
- 기본적인 품질 규칙 도입
- 낮은 신뢰 상태를 `REVIEW` 또는 `ERROR`로 매핑

## Verification
- 저품질 합성 샘플에서 게이트 동작 확인

## PASS Criteria
- 품질 게이트 결과가 판정에 반영됨

## Artifacts
- 품질 계산 모듈 및 규칙 문서
