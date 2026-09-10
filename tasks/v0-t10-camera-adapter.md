Task ID: V0-T10
Title: ONNX Export + Parity Check
Status: TODO
Depends On: V0-T09

## Purpose
선정 후보를 ONNX로 export하고, 원 모델 추론과 동등성 비교를 수행한다.

## Dependencies
- V0-T09 평가 완료 및 후보 모델 선정

## Allowed Changes
- ONNX export 스크립트 및 설정 정리
- 동일 입력으로 original 대비 출력 비교

## Forbidden Changes
- 후보 선정 전 ONNX 단계 수행
- runtime contract를 ONNX 형식에 고정

## Implementation
- 선정 모델 export
- dynamic axis/opset/전처리 일치성 점검
- 동일 입력에서 출력 차이 보고

## Verification
- ONNX inference 성공
- parity check 기록 생성

## PASS Criteria
- ONNX 모델 artifact 경로 존재
- 동일 입력에서 기능 차이를 문서화

## Artifacts
- ONNX artifact path
- parity report
