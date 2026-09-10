Task ID: V0-T04
Title: Proxy Inspection Dataset Plan + Capture Tool
Status: TODO
Depends On: V0-T03

## Purpose
Define a manageable pilot proxy dataset workflow so the user learns capture, label, split, train, tune, and evaluate cycles.

## Allowed Changes
- Create capture/session templates.
- Define object names using ordinary placeholders (e.g., `OBJ_A`, `OBJ_B`, `OBJ_C`).
- Include scenario coverage: normal arrangement, missing one required object, missing another required object, extra object, position shift, occlusion, blur, poor exposure.
- Define pilot size based on sessions and scenarios (manageable first pass).

## Forbidden Changes
- Do not hardcode engine part names or final V1 dataset rules.

## Implementation
- `proxy_capture_plan.md`, `session-template.md`, collection metadata fields.

## Verification
- Capture protocol is executable and repeatable.
- Metadata schema is suitable for later grouping.

## PASS Criteria
- Proxy capture plan approved.
- Dataset capture tool requirements finalized.

## Artifacts
- `proxy_capture_plan.md`
- `session-template.md`
