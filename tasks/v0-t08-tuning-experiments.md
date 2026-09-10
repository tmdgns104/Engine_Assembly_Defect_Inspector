Task ID: V0-T08
Title: Small Tuning Experiments
Status: TODO
Depends On: V0-T07

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
