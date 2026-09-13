Task ID: V0-T08
Title: Small Tuning Experiments
Status: ANALYSIS VERIFIED / TUNING NOT EXECUTED — current user scope complete
Depends On: V0-T07

## Current authorized scope and result (2026-09-13)

사용자가 이번 T08은 기존 baseline의 평가·오류 분석과 실험안까지만 진행하고 재학습은 하지 말라고 명시했다. 따라서 아래 기존 실행 계획은 후속 단계로 보존하며, 실제 튜닝 완료로 표시하지 않는다.

- 기존 B03 예측60장/120객체와 provenance를 재사용했다. condition/placement/scenario/class 및 condition×class 분포, IoU/confidence 최저10개, 원본좌표/출처ID를 저장했다.
- confidence 평균은 OPPOSITE0.9433, BASE0.9661, DIM0.9668. 동일 배치·상태·클래스40쌍 중36쌍이 OPPOSITE에서 낮다. DIM의 일관 악화는 없다.
- IoU 평균은 L0.87765/R0.87798/case0.95799. 최저0002 R0.75872, confidence최저0046 R0.88213. FP0/FN0, IoU<0.75는0, <0.85는13, <0.9는39개다.
- 최저 목록의18개 실제 사진/19객체를 원본·GT/pred·기존 예측으로 검토했다. 작은 부품의 세로 경계10~20px 차이, 반사/어두운 몸체와 케이스의 경계 불확실성을 관찰했다. 라벨 오류·해상도·조명의 인과 원인은 확정하지 않았다. 라벨 변경0.
- 다음 후보: A 기존baseline 유지, B 고정ROI만 변경(1순위), C 전체 프레임imgsz768만 변경(2순위). train 라벨 외곽+48px의 고정ROI[287,168,863,628]을 제안하고 B03 포함 여부만 감사했다. 실제 crop학습0. CLAHE/Gamma/sharpening/denoise는 현재 우선순위 낮음.
- 새 집중 테스트4개, 독립 벡터 IoU120개, 그룹 합계/가중평균, 최저10순위, 입력/모델/기존예측 해시, 검토 사본 및 보고서 링크 검사 PASS.
- 산출물: `training/experiments/earbud_case_v0_20260913_v001/ERROR_ANALYSIS.md`, `error_analysis_detailed.json`, `error_analysis_supplement.json`, `error_review_v001/`.
- Evidence: `docs/verification/V0-T08-ERROR-ANALYSIS-20260913.json`. 이번 실제 학습/추론 재실행0, B04 이미지 접근0, Jetson0. 실험 비교의 실측 KEEP/REJECT는 아직 대기다.

## Earlier tuning execution plan (not executed in this request)

## Purpose
Run 2-3 small, intentional tuning experiments and compare on Validation only.

## Allowed Changes
- Change a small set of variables per experiment.
- Record why each change was made and impact on metrics/speed.

## Forbidden Changes
- No blind AutoML.
- Do not change many knobs simultaneously.

## Experiment Record
For each experiment, record:
- WHY changed
- WHAT changed
- Metric impact (Precision, Recall, mAP50, mAP50-95)
- Resource impact (latency, memory)
- KEEP/REJECT decision and rationale

## Implementation
- Execute 2-3 runs.
- Compare with baseline on Validation.

## Verification
- Validation comparison table exists.
- Final candidate is selected from Validation.

## PASS Criteria
- At least one experiment logged with explicit decision rationale.

## Artifacts
- `training/experiments/tuning_matrix.md`
- `training/experiments/<id>/`
