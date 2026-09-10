Task ID: V0-T11
Title: Runtime Detector Integration
Status: TODO
Depends On: V0-T10

## Purpose
Integrate detector backends behind the normalized contract.

## Allowed Changes
- Add detector adapters for fake, PyTorch (if available), ONNX.
- Ensure downstream runtime receives only normalized `DetectionResult`.

## Forbidden Changes
- No raw framework object leakage into Recipe/Decision/Journal/API.

## Implementation
- Implement adapter factory and contract-safe mapping.

## Verification
- Run contract checks for each adapter.
- Validate runtime chain behavior with swapped adapters.

## PASS Criteria
- Backend can be changed without runtime logic edits.

## Artifacts
- `detector_adapter_map.md`
- `src/runtime/detector`
