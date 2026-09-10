Task ID: V0-T03
Title: Core Contracts / Camera + Detector Interfaces
Status: DONE / VERIFIED
Depends On: V0-T02

## Purpose
Define framework-backend-neutral runtime contracts before adapter implementation.

## Required Contract Concepts
- `Detection` must be framework neutral.
  - `class_id`, `class_name`, `confidence`, `bounding_box`
- `DetectionResult` groups detections by frame_id, with optional model version and inference time.
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
  - At T03, verify this shape with test-local dummy classes; actual adapters and hardware are deferred.

## PASS Criteria
- T03 contracts are complete and reviewed.

## Artifacts
- `docs/contracts.md`
- `src/contracts`
- `tests/test_contracts.py`
- `docs/learning-notes/V0-T03.md`
- `docs/verification/V0-T03.txt`

## Result / Evidence

- Baseline: `44ae2c4`; Windows PC, existing Python 3.13.5 project venv.
- Standard-library frozen dataclasses, StrEnum and structural Protocols define
  BoundingBox, Detection, DetectionResult, CameraFrame, FrameMetadata,
  InspectionRequest, InspectionResult, Reason, Camera and Detector.
- ResultStatus is exactly PASS / FAIL / REVIEW / ERROR. Generic ReasonCode values
  contain no engine-specific definitions; manual and PLC share RunMode/request_id.
- Explicit JSON projections exclude image payload; timestamps reject naive values
  and normalize to UTC. Numeric and nested-field invariants are checked at construction.
- PASS structural guards require frame metadata and evidence references; actual
  evidence sufficiency, uncertainty and persistence checks remain T12/T13 duties.
- Verification: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
  completed 19 tests, all PASS, including test-local dummy interface calls and a
  separate Python -S process with no site-package dependency.
- Static import audit: only standard-library and local contract imports.
- Preservation: 23 baseline file hashes and 42 installed distribution versions
  unchanged; T02 evidence/checkpoints and environment preserved.
- Review: code fields, documented invariants and tests cross-checked; no change to
  ARCHITECTURE.md or DECISIONS.md. No real adapters, training, camera access,
  Jetson, TensorRT, Recipe/Decision/Persistence/API/PLC implementation.
- PASS evidence: `docs/verification/V0-T03.txt`.
- Next: V0-T04 Proxy Inspection Dataset Plan + Capture Tool, TODO; not started.
