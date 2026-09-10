Task ID: V0-T07
Title: ONNX Export
Status: TODO
Depends On: V0-T06

## Purpose
학습 모델을 Runtime 친화적인 ONNX로 변환한다.

## Dependencies
- V0-T06에서 선택된 모델

## Allowed Changes
- ONNX export 코드/스크립트 작성
- 입력 크기/연산자 호환성 점검

## Forbidden Changes
- 모델 구조 대폭 변경
- 학습 가중치 재학습

## Implementation
- 체크포인트 로드 후 export 실행
- dynamic axes, opset, preprocessing 일치성 명세
- export 로그/버전 메타 저장

## Verification
- ONNXRuntime 간단 추론 검증
- export 경고/오류 없음

## PASS Criteria
- ONNX 파일 생성 완료
- Runtime에서 추론 가능한 형태로 저장

## Artifacts
- ONNX model path
- export 매니페스트
