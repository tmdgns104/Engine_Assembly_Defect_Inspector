Task ID: V0-T14
Title: REST API + Web HMI
Status: TODO
Depends On: V0-T13

## Purpose
Expose runtime status and manual trigger through API and thin UI.

## Allowed Changes
- Add endpoints for health, manual inspection, latest result, reason, and image evidence reference.
- Add Web HMI pages for status/history/evidence.

## Forbidden Changes
- Do not place core inspection logic in HMI.
- Do not require extra infrastructure (Kafka/Kubernetes/etc.) in V0.

## Implementation
- Build API contracts that call runtime only.
- HMI renders contract outputs only.

## Verification
- HMI/API observe the same request/result schema.

## PASS Criteria
- HMI is visualization/control interface only.

## Artifacts
- `api_contract.yaml`
- `hmi_screen_spec.md`
