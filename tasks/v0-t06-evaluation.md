Task ID: V0-T06
Title: Evaluation
Status: TODO
Depends On: V0-T05

## Purpose
Baseline/Tuning 결과를 비교 평가하고 Error Case를 분석한다.

## Dependencies
- V0-T04, V0-T05

## Allowed Changes
- confusion 분석/예측 결과 저장
- error case 카테고리 분류(누락/오탐/오정렬 등)

## Forbidden Changes
- 새로운 모델 구조 변경
- 평가 코드 무결성 훼손

## Implementation
- 공통 metric 집계
- precision/recall/mAP50/mAP50-95, inference latency 계산
- 오류 샘플 시각화/분류

## Verification
- 동일 테스트셋 기반 재현성 확인
- 지표 비교표 작성

## PASS Criteria
- 최종 채택 모델 판단 근거 존재
- 실패 케이스 로그 존재

## Artifacts
- evaluation 리포트
- 오류 샘플 목록
