Task ID: V0-T12
Title: Image Quality + Recipe + Decision
Status: TODO
Depends On: V0-T11

## Purpose
이미지 품질 게이트와 Recipe/Decision를 통합해 AI 판정 결과를 형식화한다.

## Dependencies
- V0-T11 detector runtime 통합

## Allowed Changes
- 품질 점수(밝기/블러/해상도/프레임 유효성) 계산
- Recipe rule 설계(demo/proxy 규칙)
- Decision 우선순위(불완전 시 REVIEW/ERROR 선행) 반영

## Forbidden Changes
- V1 최종 임계치를 V0 임계치로 오인
- 품질 결함을 곧바로 FAIL로 단정

## Implementation
- proxy threshold를 명시한 상태값 정의
- recipe 결과와 quality 결과를 결합하여 PASS/FAIL/REVIEW/ERROR 생성
- 이유 코드(reason code) 정리

## Verification
- 가림/흐림/저조도 입력에서 REVIEW 처리 확인
- proxy 기준 decision matrix 확인

## PASS Criteria
- 모든 판정 상태가 이유코드와 함께 생성
- demo threshold로만 테스트한 상태 기록 존재

## Artifacts
- quality config
- recipe template
- decision rules
