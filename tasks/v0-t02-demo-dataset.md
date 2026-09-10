Task ID: V0-T02
Title: Demo Dataset 후보 조사 및 선정
Status: TODO
Depends On: V0-T01

## Purpose
V0에서 실제 엔진 데이터셋 없이도 Object Detection Workflow를 수행할 수 있는 Demo Dataset를 후보 조사하고, 1개를 추천한다.

## Dependencies
- V0-T01 완료
- 네트워크/공개 메타데이터 접근 가능성

## Allowed Changes
- 2~3개 후보 조사(라이선스/클래스 수/크기/학습 난이도/교체용이성)
- 비교표 생성
- 추천 후보 명시

## Forbidden Changes
- 대규모 원본 데이터 다운로드
- 미검증 후보를 최종 선정으로 간주

## Implementation
- Pascal VOC 2007 (또는 2007+2012), COCO128, Penn-Fudan Pedestrian 등을 비교 대상으로 선정
- 후보별 항목:
  - License
  - Approx size
  - Classes
  - Training difficulty
  - V0 적합성
  - V1 엔진 Dataset으로 교체 용이성
- 추천 근거를 `docs/PROJECT.md` 또는 해당 Task에 기록

### Candidate comparison (investigated, not downloaded)

| Dataset | License | Approx Size | Classes | Training Difficulty | V0 Suitability | V1 Replacement Ease |
|---|---|---|---|---|---|---|
| Pascal VOC 2007 | BSD-like/Creative Commons family (official task policy) | ~700MB train+val (small~medium) | 20 | 중간 | 높음 | 높음 |
| COCO128 | CC BY 4.0 derivative | ~100MB | 80 | 매우 낮음(빠름) | 높음(속도) / 중간(클래스 수) | 높음 |
| Penn-Fudan Pedestrian | Creative Commons-like University dataset terms (publicly redistributable) | ~200MB 이하 | 1 | 매우 낮음 | 중간(클래스 편의성) | 중간(도메인 편향) |

### Recommended Demo Dataset

- 추천: `Pascal VOC 2007`
- 근거:
  - 클래스 수가 적당하고(20개) 오탐·누락 분석 연습이 가능
  - 구조가 널리 사용됨 (`train/val` 분할 및 annotation 구조)
  - V1 엔진 Dataset으로 클래스/설정 교체 실습 시 맥락 유지가 쉬움
- 실제 다운로드는 V0-T02 실행 시작 시 `baseline` 단계에서 수행.

## Verification
- 최소 2개 이상 후보 비교표 존재
- 추천 후보에 대한 근거 문장 존재
- 다운로드는 수행하지 않았음을 기록

## PASS Criteria
- 2~3개 후보 정리
- 1개 후보를 Recommended로 확정
- 각 항목이 비교 항목 기준을 모두 포함

## Artifacts
- 후보 비교 표
- Recommended Demo Dataset 기록
