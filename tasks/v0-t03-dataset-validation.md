Task ID: V0-T03
Title: Dataset Validation Pipeline
Status: TODO
Depends On: V0-T02

## Purpose
데이터셋 구성, annotation 무결성, split 구조(Train/Val/Test)를 자동 검증한다.

## Dependencies
- V0-T02에서 후보 선택
- training/configs/*.yaml

## Allowed Changes
- 데이터셋 구조 검사 스크립트 작성
- 누락 파일/라벨/포맷/중복 검사 추가
- Split 비율 검증

## Forbidden Changes
- 학습 코드 핵심 로직 변경
- 대용량 데이터셋 이동

## Implementation
- manifest 또는 annotation parser 기반 검사 루틴 추가
- 경로/클래스 id/바운딩박스 유효성 검사
- split 파일 존재 및 비율 확인

## Verification
- 샘플 케이스로 pass/fail 로그 확인
- 실패 케이스 예외 처리를 문서화

## PASS Criteria
- 유효하지 않은 샘플이 정확히 reject
- 정상 split가 통과

## Artifacts
- 데이터셋 validation 스크립트
- validation 리포트
