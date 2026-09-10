Task ID: V0-T16
Title: Jetson Camera End-to-End
Status: TODO
Depends On: V0-T15

## Purpose
Run complete runtime on Jetson with real camera and V0 runtime artifacts only.

## Allowed Changes
- Build Jetson E2E chain: capture -> quality -> detector -> recipe -> decision -> journal -> api/hmi.
- Keep dataset/chkpt copying out of runtime unless explicitly needed for benchmark sample checks.

## Artifact Boundary for Jetson
- `deployment/model/model.onnx`
- `deployment/classes.yaml`
- `deployment/recipe.yaml`
- `deployment/camera.yaml`
- `deployment/runtime.yaml`
- `deployment/manifest.json`

## TensorRT Rehearsal in V0
- If feasible, rehearse `ONNX -> TensorRT -> inference` on Jetson using proxy ONNX.
- This ONNX/ONNX->TRT proxy path is rehearsal only; do not reuse TRT artifact for engine model in V1.

## Verification
- One successful end-to-end run on Jetson.
- Startup and result publishing logs captured.

## PASS Criteria
- Jetson runtime boundary is clean and documented.

## Artifacts
- `jetson-e2e-log.md`
- `jetson_startup_checklist.md`
