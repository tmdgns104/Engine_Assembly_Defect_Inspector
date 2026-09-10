Task ID: V0-T14
Title: REST API + Web HMI
Status: TODO
Depends On: V0-T13

## Purpose
검사 상태, 최신 결과, 히스토리, 이력 이미지 등 공개 API와 UI를 최소 형태로 제공한다.

## Dependencies
- V0-T13 journal persistence

## Allowed Changes
- health, manual trigger, latest result, history, image evidence API 스키마
- Web HMI 최소 화면 설계

## Forbidden Changes
- 과도한 UI/라우팅 복잡화
- journal가 없는 결과를 노출

## Implementation
- API contract 문서화
- HMI에서 PASS/FAIL/REVIEW/ERROR 표현
- 시스템 상태와 최신 이력 표시

## Verification
- API contract와 화면 데이터 필드 일치
- 오류 상태 코드와 메시지 일관성

## PASS Criteria
- API + HMI 요구 범위가 최소 기능으로 수렴

## Artifacts
- API contract spec
- UI screen spec
