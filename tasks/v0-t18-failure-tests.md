Task ID: V0-T18
Title: Jetson Packaging / Startup
Status: TODO
Depends On: V0-T17

## Purpose
재현 가능한 Jetson 배포 패키지 구조와 서비스 시작 절차를 정비한다.

## Dependencies
- V0-T17

## Allowed Changes
- deployment manifest 구성
- config/bootstrap/check readiness 설계
- service startup 시퀀스 문서화

## Forbidden Changes
- 검증되지 않은 프로덕션 설정 고정
- runtime 외부 설정을 숨긴 채 배포

## Implementation
- deployment 경로(모델, class, recipe, runtime config, version metadata) 정의
- 최소 startup validation 설계

## Verification
- start-up checklist가 재현 가능한지 확인

## PASS Criteria
- 반복 실행 가능한 배포 항목이 문서화
- 준비/기동 상태가 확인되는 체크리스트 존재

## Artifacts
- deployment manifest
- startup guide
