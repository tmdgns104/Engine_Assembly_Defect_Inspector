Task ID: V0-T19
Title: Jetson Deployment Preparation
Status: TODO
Depends On: V0-T08

## Purpose
V1/Jetson 전달용 배포 산출물(ONNX, labels, recipe, runtime config, version metadata)을 준비한다.

## Dependencies
- V0-T07, V0-T08

## Allowed Changes
- 배포 체크리스트 작성
- build/run 스크립트 템플릿 추가

## Forbidden Changes
- Jetson에서 동작 불확실한 코드 강제 병합

## Implementation
- Windows training -> ONNX 전달 경로 명시
- TensorRT build 준비 스크립트(대상에서 실행)
- 배포용 폴더/매니페스트 생성

## Verification
- 배포 산출물 목록이 누락 없이 존재

## PASS Criteria
- Jetson 전달 항목이 문서로 고정
- TensorRT 단계는 대상 장비에서 빌드 가능하도록 정리

## Artifacts
- 배포 스크립트 템플릿
- runtime manifest
