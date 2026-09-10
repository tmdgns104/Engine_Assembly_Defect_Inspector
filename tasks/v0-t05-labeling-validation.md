Task ID: V0-T05
Title: Labeling + Dataset Validation
Status: TODO
Depends On: V0-T04

## Purpose
Finish pilot labeling and validate dataset quality before splitting.

## Allowed Changes
- Build a simple label taxonomy for proxy objects.
- Run label consistency and completeness checks.

## Forbidden Changes
- Do not split before labeling validation.
- Do not tune model while labels are incomplete.

## Implementation
- Create labeling rubric for V0 placeholder classes.
- Produce `label_audit.md` and resolve obvious mistakes.

## Verification
- No required object annotations are missing in the pilot set.
- Label quality checks pass the project threshold.

## PASS Criteria
- Labeling complete.
- Labeling report approved.

## Artifacts
- `label_audit.md`
- `label_schema.json`
