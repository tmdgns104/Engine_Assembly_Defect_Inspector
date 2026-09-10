Task ID: V0-T17
Title: Web HMI
Status: TODO
Depends On: V0-T16

## Purpose
검사 결과/이력/상태를 확인할 수 있는 간단한 Web HMI 초기 동작을 준비한다.

## Dependencies
- REST API 스펙

## Allowed Changes
- 상태 조회 화면/조회 API 호출
- 결과 카드 및 이미지 링크 표시

## Forbidden Changes
- 복잡한 실시간 스트리밍 UI 과도 확장

## Implementation
- PASS/FAIL/REVIEW/ERROR 표시 화면 구성
- 최근 이력, health, 수동 검사 트리거 버튼

## Verification
- API 응답 기반 화면 렌더링 확인

## PASS Criteria
- Runtime 계약을 반영한 최소 기능 화면 존재

## Artifacts
- HMI 화면 설계 문서
