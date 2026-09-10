Task ID: V0-T13
Title: Journal / Evidence Persistence
Status: TODO
Depends On: V0-T12

## Purpose
Persist all inspection artifacts before emitting final status.

## Allowed Changes
- Build persistence schema with evidence references.
- Define publish sequence: capture -> detect -> decision -> persist -> publish.

## Forbidden Changes
- Do not publish PASS before persistence succeeds.
- Do not allow evidenceless status to be treated as PASS.

## Implementation
- Add persistence transaction and retry strategy.
- Store evidence pointers for each inspection.

## Verification
- Inject persistence failure and confirm safe ERROR/REVIEW output.

## PASS Criteria
- Final status depends on successful persistence.

## Artifacts
- `journal_schema.sql`
- `persistence_sequence.md`
