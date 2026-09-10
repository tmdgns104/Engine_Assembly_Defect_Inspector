Task ID: V0-T16
Title: Jetson Camera End-to-End
Status: TODO
Depends On: V0-T15

## Purpose
실제 Jetson + USB Camera + V4L2로 전체 V0 runtime chain을 통합 실행한다.

## Dependencies
- V0-T15 request/adapter 설계

## Allowed Changes
- Jetson capture 경로 정리
- runtime sequence test (camera -> quality -> detector -> recipe -> decision -> journal -> api/hmi)
- 실패 시 ERROR 상태 동작 확인

## Forbidden Changes
- 임계치/정확도 정책을 엔진 기준으로 간주
- V2 PLC 제어 동작 추가

## Implementation
- Jetson의 실기기 연동 스텝 문서화
- 실제 카메라에서 최소 1회 통합 실행
- Proxy thresholds로 결과 분류

## Verification
- 연동 순서가 단절 없이 실행
- 결과가 journal/API/HMI로 전달됨

## PASS Criteria
- V0-C 핵심 통합 흐름이 실제 장비에서 확인

## Artifacts
- Jetson E2E run log
- integration checklist
