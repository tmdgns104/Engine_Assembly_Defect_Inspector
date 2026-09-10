Task ID: V0-T06
Title: Grouped Train / Validation / Test Split
Status: TODO
Depends On: V0-T05

## Purpose
Create leakage-safe split based on capture acquisition boundaries.

## Core Rule
- TRAIN: updates model weights.
- VALIDATION: used during development, thresholding, hyper-parameter comparison.
- TEST: sealed final evaluation used once after final model selection.
- Never use TEST for repeated tuning decisions.

## Allowed Changes
- Split by session / setup / arrangement episode / sequence grouping.
- Keep near-duplicate frames in same split.
- Create split manifests and seeds.

## Forbidden Changes
- No random per-frame split for primary dataset.

## Verification
- Leakage check confirms no group appears in multiple splits.

## PASS Criteria
- Train/val/test manifests are published and auditable.

## Artifacts
- `split_manifest.json`
- `leakage_check_report.md`
