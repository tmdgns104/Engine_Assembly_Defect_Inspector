Task ID: V0-T04
Title: Proxy Inspection Dataset Plan + Capture Tool
Status: TODO
Depends On: V0-T03

## Purpose
엔진 전환 rehearsal를 위해 일반 물체 기반 proxy 검사 데이터셋 캡처 방법과 실행 시나리오를 정한다.

## Dependencies
- V0-T03 계약 정의 완료
- V0-T02 환경 점검 완료

## Allowed Changes
- 촬영 세션/시나리오 템플릿 작성
- 객체 구성(예: A, B, C) 메타 정의
- 캡처 메타데이터 항목 추가(조도, 거리, 포즈, occlusion, blur, 실패 라벨)

## Forbidden Changes
- 실제 엔진 부품명/slot 수/좌표를 선행해서 고정하지 않음.
- V1 엔진 학습 규격의 고정값을 가정하지 않음.

## Implementation
- `fixed inspection area` 기준 세션/시나리오 템플릿 정리
- 정상/불량/예외 케이스 구성
- 캡처 도구 요구사항(명명 규칙, 저장 경로, 수집 속성) 정리

## Verification
- 촬영 프로토콜이 재현 가능 문서로 존재
- V0-B 데이터 파이프라인 시작점으로 사용 가능

## PASS Criteria
- Proxy Dataset Capture Plan 확정
- `dataset capture` 재실행 가능한 가이드 완료

## Artifacts
- proxy_capture_plan.md
- session template
