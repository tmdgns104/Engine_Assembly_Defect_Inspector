Task ID: V0-T06
Title: Grouped Train / Validation / Test Split
Status: TODO
Depends On: V0-T05

## Purpose
Proxy 데이터셋을 data leakage 없이 grouped split한다.

## Dependencies
- V0-T05 라벨/유효성 확보

## Allowed Changes
- 세션 단위/장면 단위 분할 규칙 설정
- train/val/test 비율과 제약 조건 저장

## Forbidden Changes
- 유사 장면 프레임을 임의로 train/val/test에 분산
- split 기준을 기록 없이 변경

## Implementation
- 동일 장면/동일 물체 조합이 다른 split로 흩어지지 않도록 분할
- `data leakage` 방지 체크리스트 작성
- 분할 결과 manifest 저장

## Verification
- 그룹 기준 분할 위반이 없는지 검사
- split 통계가 요구 범위에 맞는지 확인

## PASS Criteria
- 누수 방지 규칙이 반영된 분할
- split manifest가 재현 가능

## Artifacts
- split manifest
- leakage check report
