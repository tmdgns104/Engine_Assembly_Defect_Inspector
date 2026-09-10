Task ID: V0-T15
Title: Manual Request + Mock PLC Adapter
Status: TODO
Depends On: V0-T14

## Purpose
Share one inspection contract for manual UI requests and Mock PLC control.

## Required Principle
Manual button and Mock PLC must emit the same `InspectionRequest` and consume the same `InspectionResult`.

## Allowed Changes
- Define shared control adapter interface.
- Implement Mock PLC adapter that calls runtime with shared request/result models.

## Forbidden Changes
- No duplicated logic between manual and PLC paths.
- No real PLC maps/registers in V0.

## Verification
- Manual and Mock PLC traces match schema and output format.

## PASS Criteria
- Adapter boundary is replaceable for V2.

## Artifacts
- `control_adapter_contract.md`
