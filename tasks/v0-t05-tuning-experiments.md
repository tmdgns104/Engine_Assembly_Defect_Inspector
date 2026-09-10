Task ID: V0-T05
Title: Small-scale Tuning (2~3 Runs)
Status: TODO
Depends On: V0-T04

## Purpose
과도한 탐색 없이 Epoch/이미지 크기/LR/증강/Confidence 중 2~3개 실험을 수행해 성능 변화를 이해한다.

## Dependencies
- V0-T04 완료

## Allowed Changes
- 소규모 하이퍼파라미터 조합 추가
- experiment 메타데이터 기록

## Forbidden Changes
- 무작위 대규모 search
- 데이터셋 대규모 재구성

## Implementation
- 실험 세트를 2~3개로 제한
- 각 실험 항목에 `experiment_id`, `dataset_version`, `model`, `epochs`, `image_size`, `hyperparameters`, `precision`, `recall`, `mAP50`, `mAP50-95`, `inference_latency`, `artifact_path`, `conclusion` 필수 기록
- 성능/실행시간 비교

## Verification
- 최소 2개 실험 완료
- 비교표에 모든 필수 컬럼 존재

## PASS Criteria
- tuning 전후 차이 분석 문서화
- 최종 채택 실험 1개 제시

## Artifacts
- 실험 로그 및 비교표
