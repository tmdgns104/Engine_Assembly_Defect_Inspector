Task ID: V0-T10
Title: Camera Adapter
Status: TODO
Depends On: V0-T09

## Purpose
Replay, SampleImage, V4L2 카메라 소스를 같은 Camera 인터페이스로 통합한다.

## Dependencies
- src/camera 초기 구조

## Allowed Changes
- 공통 `Camera` 인터페이스 정의
- 각 Adapter 기본 구현

## Forbidden Changes
- 하드웨어 종속 코드를 Runtime 핵심으로 침투
- 플랫폼별 분기 무한 확장

## Implementation
- `capture()`, `status()`, `close()` 기반 인터페이스 정의
- Mock/Replay 기반으로 V0에서 동작 테스트 가능

## Verification
- Replay source 샘플 캡처 동작 확인

## PASS Criteria
- V4L2 미연결 환경에서도 인터페이스 계약이 깨지지 않음

## Artifacts
- Camera adapter 인터페이스 문서
