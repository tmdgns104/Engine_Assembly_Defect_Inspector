Task ID: V0-T08
Title: Small Tuning Experiments
Status: TODO
Depends On: V0-T07

## Purpose
기본 baseline을 기반으로 2~3개 튜닝 실험을 수행해 변화 추이를 학습한다.

## Dependencies
- V0-T07 baseline

## Allowed Changes
- epoch/image size/LR/augmentation 조합 실험
- 실험 비교표 작성

## Forbidden Changes
- 광범위 탐색(HPO)
- Proxy 데이터셋 외부에서 성능 비교

## Implementation
- 2~3개 실험만 수행
- 각 실험에서 변경 이유와 결과(precision, recall, mAP50, mAP50-95, latency, runtime)를 기록
- best candidate 선택 근거 작성

## Verification
- 실험 단위별 결과표 작성
- 가장 적합한 후보 1개를 결론으로 기록

## PASS Criteria
- 2~3개 실험 완료
- 변경 이유/효과/선정 근거가 있는 비교표 존재

## Artifacts
- tuning experiment table
- tuning conclusion note
