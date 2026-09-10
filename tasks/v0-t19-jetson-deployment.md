Task ID: V0-T19
Title: Benchmark
Status: TODO
Depends On: V0-T18

## Purpose
Inference latency, E2E latency, memory, 버전/장치 정보를 측정한다.

## Dependencies
- V0-T18

## Allowed Changes
- runtime latency measurement plan 수립
- 환경 메타 데이터 기록

## Forbidden Changes
- 임의 pass/fail 임계치 임의 정의
- 하드웨어별 편차를 무시한 단일 수치 고정

## Implementation
- 단일 입력 시나리오 기반 latency 측정
- FPS 또는 처리량 값 수집
- memory/disk/resource snapshot 기록

## Verification
- 벤치 결과 항목이 누락 없이 저장

## PASS Criteria
- 기준값은 수집되었으나 정식 pass 조건은 미설정
- V1 비교의 baseline 역할을 할 수 있는 측정치 존재

## Artifacts
- benchmark report
