Task ID: V0-T09
Title: Evaluation + Error Analysis
Status: TODO
Depends On: V0-T08

## Purpose
Baseline+튜닝 결과를 평가하고 오류 유형을 분류한다.

## Dependencies
- V0-T07, V0-T08

## Allowed Changes
- precision/recall/mAP50/mAP50-95 계산
- 클래스별 오류, FP/FN 분석, 시각적 실패 예시 정리

## Forbidden Changes
- 새로운 모델 구조 도입
- 실패 분석 없이 모델을 임의 전환

## Implementation
- 공통 지표 집계
- false positive/false negative 분석
- 실패 사례 이미지와 사유 분류

## Verification
- 평가 지표와 오류 분석 결과가 동일 기준으로 재현
- 다음 단계의 export 후보가 문서화

## PASS Criteria
- 모델 선택을 뒷받침하는 평가 보고서
- 실패 분석과 우선 보완 포인트 기록

## Artifacts
- evaluation report
- error analysis
