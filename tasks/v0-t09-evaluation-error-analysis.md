Task ID: V0-T09
Title: Evaluation + Error Analysis
Status: TODO
Depends On: V0-T07, V0-T08

## Purpose
Evaluate baseline and tuned models, select final model on Validation, then perform one sealed Test.

## Allowed Changes
- Generate Precision/Recall/mAP50/mAP50-95 and error buckets.
- Produce error categories: false positives, false negatives, miss with poor coverage, miss with good coverage.

## Forbidden Changes
- Do not use sealed Test to drive tuning decisions.
- Do not alter final config after viewing Test.

## Implementation
- Compare baseline vs tuning on Validation.
- Freeze final config.
- Run a single final Test pass and archive results.

## Verification
- Test manifest exists and is clearly sealed.

## PASS Criteria
- Final model selected from Validation only.
- Test run is single-use evidence.

## Artifacts
- `evaluation_report.md`
- `error_analysis.md`
