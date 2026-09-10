Task ID: V0-T17
Title: Failure / Recovery Tests
Status: TODO
Depends On: V0-T16

## Purpose
Validate safe behaviors for abnormal and degraded inputs.

## Allowed Changes
- Build at least 8 scenarios (timeouts, blur, exposure, frame loss, inference error, etc.).
- Define explicit recovery strategy for each.

## Forbidden Changes
- Do not map `EMERGENCY STOP` into PASS/FAIL/REVIEW/ERROR.

## Verification
- Recovery matrix executed and logged.
- No unsafe PASS under ERROR conditions.

## PASS Criteria
- Failure handling is repeatable and documented.

## Artifacts
- `failure_scenarios.md`
- `recovery_matrix.md`
