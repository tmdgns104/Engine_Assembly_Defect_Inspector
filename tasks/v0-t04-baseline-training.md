Task ID: V0-T04
Title: Baseline Training
Status: TODO
Depends On: V0-T03

## Purpose
선정한 Demo Dataset으로 baseline 모델을 학습해 기본 성능 baseline을 확보한다.

## Dependencies
- V0-T03 완료

## Allowed Changes
- train/val/test 설정 적용
- 기본 하이퍼파라미터로 학습 실행
- 실험 아티팩트 메타 기록

## Forbidden Changes
- 대규모 하이퍼파라미터 탐색
- 데이터셋 자체를 임의 교체

## Implementation
- 실험 ID 채번 및 결과 디렉터리 생성
- baseline config 기반 학습 실행
- mAP/precision/recall 등 기록

## Verification
- 최소 1회 학습 완료
- best/checkpoint 경로 기록

## PASS Criteria
- reproducible한 baseline 결과 저장
- 모델/학습 로그 요약 저장

## Artifacts
- training/experiments/<id>/ 결과
- baseline 메트릭 요약
