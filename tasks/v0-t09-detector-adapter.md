Task ID: V0-T09
Title: Detector Adapter
Status: TODO
Depends On: V0-T08

## Purpose
Fake/PyTorch/ONNX/TensorRT 구현체를 하나의 Detector 인터페이스로 묶는다.

## Dependencies
- src/vision 초기 구조

## Allowed Changes
- Detector abstract contract 정의
- Adapter 래퍼 구현
- model/artifact/config 로딩

## Forbidden Changes
- 결정 로직을 Runtime과 결합
- 모델 포맷별 중복 처리

## Implementation
- `Detector` 인터페이스에서 `detect(image)->detections` 규격 고정
- FakeDetector, PyTorchDetector, ONNXDetector, TensorRTDetector 스텁/인터페이스 정의

## Verification
- 1개 구현체에서 최소 인터페이스 응답 검증
- 인터페이스 문서화

## PASS Criteria
- 같은 호출 규격으로 교체 가능한 구조

## Artifacts
- Detector contracts
