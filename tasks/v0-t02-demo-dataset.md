Task ID: V0-T02
Title: ML Environment + Tiny GPU Smoke Test
Status: TODO
Depends On: V0-T01

## Purpose
COCO8 같은 매우 작은 공개 데이터셋으로 Python, PyTorch, CUDA, RTX 5070 환경에서 object-detection 훈련 루프를 확인한다.

## Dependencies
- V0-T01 completed.
- GPU/driver 상태 점검 완료.

## Allowed Changes
- Smoke test 계획 수립(데이터셋, 실행 스크립트, 기본 하이퍼파라미터)
- 최소 반복 학습 수행
- 체크포인트 생성 확인

## Forbidden Changes
- 본격 학습 지표 비교/튜닝
- Proxy dataset 설계 원칙을 대체하는 방식의 Dataset 사용 확정
- 데이터셋 다운로드를 포함한 대규모 학습 실행

## Implementation
- COCO8 또는 동급의 극소형 샘플셋으로 간단 훈련 루프 실행
- 데이터셋 읽기, loader, train/eval, 저장 경로를 확인
- 생성되는 체크포인트/로그 경로를 기록
- 성능은 환경 검증값으로만 처리

## Verification
- 환경에서 GPU/Framework가 정상 동작
- 1회 이상 smoke run 완료
- checkpoint 저장 경로 존재

## PASS Criteria
- 환경 smoke가 성공
- 체크포인트 생성과 로그가 남음
- V0-B로 진행 가능한 상태

## Artifacts
- V0-T02 smoke run log
- 환경 검증 체크리스트
