Task ID: V0-T11
Title: Runtime Detector Integration
Status: TODO
Depends On: V0-T10

## Purpose
인터페이스 기반 detector adapter를 runtime에 탑재한다.

## Dependencies
- V0-T03 인터페이스 계약
- V0-T10 ONNX export 완료

## Allowed Changes
- FakeDetector, trained PyTorch detector, ONNXDetector 구현체 어댑터 정리
- Detector contract 위반 없는 호출 구조 정리

## Forbidden Changes
- 모델 형식에 따라 런타임 분기 로직을 직접 확장
- Quality/Decision 로직을 detector 내부에 결합

## Implementation
- Detector adapter registry 또는 팩토리 설계
- 최소 3개 구현체 최소 스텁/연동 규격 정리
- contract 기반 주입 포인트 문서화

## Verification
- `detect` 호출에서 동일한 응답 스키마가 보장되는지 확인

## PASS Criteria
- Fake / trained / ONNX detector를 runtime에서 교체 실험 가능한 형태

## Artifacts
- detector adapter map
