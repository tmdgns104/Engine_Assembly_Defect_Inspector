Task ID: V0-T05
Title: Labeling + Dataset Validation
Status: TODO
Depends On: V0-T04

## Purpose
Proxy 데이터로 바운딩 박스 라벨링과 annotation 무결성을 연습한다. 클래스, 프레임, 라벨 오류를 조기에 잡는다.

## Dependencies
- V0-T04 capture plan

## Allowed Changes
- 라벨 스키마 정의 및 리뷰 루프 정의
- 바운딩 박스 누락/오류 검출 규칙 정리
- 이미지-라벨 일치성 검증 스크립트

## Forbidden Changes
- 모델 학습 코드 변경
- Proxy 클래스 정의에서 엔진 고정 규격(부품명/좌표/slot)을 가정하지 않음

## Implementation
- object 클래스 설계(필수/보조/예외 개념)
- 라벨링 및 리뷰 절차(검토/수정/승인) 문서화
- annotation integrity 검사 규칙 반영

## Verification
- 이상 라벨링 케이스를 검출해 실패 처리
- 정상 케이스를 통과 처리

## PASS Criteria
- Proxy dataset annotation 기준이 일관되게 문서화
- Validation 실패/성공 케이스가 확인됨

## Artifacts
- labeling spec
- validation report
