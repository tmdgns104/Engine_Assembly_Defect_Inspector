Task ID: V0-T12
Title: Image Quality + Recipe + Decision
Status: TODO
Depends On: V0-T11

## Purpose
Implement image-quality checks, recipe thresholds, and decision logic that preserves uncertainty handling.

## Required Semantics
- Detection present with good quality -> present.
- Detection missing with good visibility -> may be candidate `FAIL`.
- Detection missing with poor visibility -> `REVIEW`.
- System/camera/processing error -> `ERROR`.

## Allowed Changes
- Define DEMO/PROXY thresholds for brightness, blur, frame age, frame validity.
- Mark these thresholds explicitly as `DEMO/PROXY ONLY`.
- Add reason-code matrix for final `PASS/FAIL/REVIEW/ERROR`.

## Forbidden Changes
- Do not treat “not detected” as absolute missing without visibility context.
- Do not claim final production thresholds in V0.

## Verification
- Decision matrix covers the failure semantics above.

## PASS Criteria
- Threshold file labels scope clearly.
- Decision outcomes are traceable to rules.

## Artifacts
- `quality_config.yaml`
- `recipe.yaml`
- `decision_matrix.md`
