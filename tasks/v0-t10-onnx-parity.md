Task ID: V0-T10
Title: ONNX Export + Parity Check
Status: TODO
Depends On: V0-T09

## Purpose
Export the selected model to ONNX and compare parity with native inference.

## Allowed Changes
- Export ONNX with tracked settings.
- Run native and ONNX on the same fixed sample set.
- Same preprocessing, input size, class mapping, confidence threshold, post-processing assumptions.

## Forbidden Changes
- Do not require exact floating-point identity.
- Do not compare across different sample sets or transforms.

## Implementation
- Build `onnx_parity_manifest.json`.
- Record mismatch summary and acceptable variance.

## Verification
- ONNX model runs successfully.
- Parity report documents differences clearly.

## PASS Criteria
- ONNX artifact is valid.
- Parity report is explicit and signed off.

## Artifacts
- `deployment/model/model.onnx`
- `onnx_parity_manifest.json`
- `onnx_parity_report.md`
