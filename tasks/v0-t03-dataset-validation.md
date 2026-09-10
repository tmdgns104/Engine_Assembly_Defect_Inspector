Task ID: V0-T03
Title: Core Contracts / Camera + Detector Interfaces
Status: TODO
Depends On: V0-T02

## Purpose
`Detector`, `Camera`, 검사 요청/결과 계약을 먼저 확정한다. 계약이 먼저 존재한 후 구현체가 추가되도록 만든다.

## Dependencies
- V0-T02 smoke 검증 완료

## Allowed Changes
- Detection Result, Inspection Request, Inspection Result 스키마 정의
- Camera interface (`capture`, `status`, `close`) 정의
- Detector interface (`detect`, confidence, bbox format, reason codes) 정의
- 상태 enum: `PASS / FAIL / REVIEW / ERROR` 고정

## Forbidden Changes
- 구현체 중심의 하드코딩
- 품질 임계치/조명 값 같은 V1 확정 기준 선입력

## Implementation
- `src/contracts`에 공통 스키마/타입 문서화
- Mock/Stub 계약 테스트 시나리오 정의
- `docs/ARCHITECTURE.md`와 Task 의존성에서 인터페이스 선행성 반영

## Verification
- 최소 1개 가상 계약 테스트 시나리오 작성
- Detector/Camera 구현이 계약만 의존하여 호출되는지 점검

## PASS Criteria
- 계약 항목이 문서와 Task에 반영
- 구현체 추가 이전에도 계약 단위 문서가 명확히 존재

## Artifacts
- Contracts 문서 및 인터페이스 스키마
