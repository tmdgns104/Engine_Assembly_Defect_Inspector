Task ID: V0-T03
Title: Core Contracts / Camera + Detector Interfaces
Status: TODO
Depends On: V0-T02

## Purpose
Define framework-backend-neutral runtime contracts before adapter implementation.

## Required Contract Concepts
- `DetectionResult` must be framework neutral.
  - `class_id`, `class_name`, `confidence`, `bounding_box`
  - optional metadata only when needed (frame id, model version)
- `CameraFrame` must be backend neutral.
  - `image`, `frame_id`, `captured_at`, optional source tags
- `InspectionRequest`
  - `request_id`, `run_mode` (`manual`/`plc`), optional control hints
- `InspectionResult`
  - `status` (`PASS`/`FAIL`/`REVIEW`/`ERROR`)
  - `reasons`, `evidence_refs`, `frame_meta`

## Allowed Changes
- Create contracts for detector, camera, request, and result in `src/contracts`.
- Add explicit reason codes and error states.

## Forbidden Changes
- Do not expose raw YOLO/ONNX/TensorRT objects to recipe/decision/journal/API.
- Do not bind contracts to a specific adapter implementation.

## Implementation
- Document contracts and invariants in `docs/contracts.md`.
- Add simple contract compliance checks.

## Verification
- Contracts can be serialized without framework types.
- Both replay/camera adapters consume the same contracts.

## PASS Criteria
- T03 contracts are complete and reviewed.

## Artifacts
- `docs/contracts.md`
- `src/contracts`
