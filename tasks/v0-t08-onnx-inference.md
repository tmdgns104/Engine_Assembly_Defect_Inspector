Task ID: V0-T08
Title: ONNX Runtime Inference
Status: TODO
Depends On: V0-T07

## Purpose
ONNX Runtime으로 동작하는 추론 경로를 검증한다.

## Dependencies
- V0-T07 ONNX model

## Allowed Changes
- preprocessing/postprocessing 일치 실험
- latency 측정 스크립트

## Forbidden Changes
- 학습 코드 변경
- 레이블맵 재정의 무단 변경

## Implementation
- sample image inference 실행
- batch size 1 고정 추론과 latency 측정
- 예측 포맷을 Detector 인터페이스에 맞춰 정규화

## Verification
- 동일 이미지에 대한 출력 포맷/클래스 일관성 검증
- latency 로그 저장

## PASS Criteria
- Runtime에서 추론 성공
- 지표/속도 값 수집

## Artifacts
- ONNX inference 샘플 결과
