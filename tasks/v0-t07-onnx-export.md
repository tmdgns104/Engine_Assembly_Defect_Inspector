Task ID: V0-T07
Title: Baseline Training
Status: TODO
Depends On: V0-T06

## Purpose
Proxy dataset으로 1회 재현 가능한 baseline 학습을 수행해 실험 baseline을 만든다.

## Dependencies
- V0-T06 분할 완료

## Allowed Changes
- 모델/epoch/image size/batch 설정 고정 baseline 실행
- 실험 메타데이터 기록
- 체크포인트 및 지표 저장

## Forbidden Changes
- 대규모 tuning 탐색
- 프레임워크 교체

## Implementation
- baseline config 기반 실행
- `model`, `epochs`, `image_size`, `batch`, `learning_rate`, `precision`, `recall`, `mAP50`, `mAP50_95`, `inference_latency` 기록
- artifact 경로 수집

## Verification
- 정상 종료 확인
- baseline 결과를 baseline log에 정리

## PASS Criteria
- Baseline 성능 지표가 1개 이상 기록
- 모델 체크포인트 path가 남음

## Artifacts
- `training/experiments/<id>/` baseline result
- 실험 메타 데이터
