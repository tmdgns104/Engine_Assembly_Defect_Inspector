Task ID: V0-T02
Title: ML Environment + Tiny GPU Smoke Test
Status: TODO
Depends On: V0-T01

## Purpose
- Verify the local ML environment (Python + CUDA + PyTorch + GPU) is usable.
- Run exactly one tiny smoke test on a public dataset (COCO8).
- COCO8 is smoke only and is not the V0 training dataset.

## Dependencies
- V0-T01 completed.
- GPU/driver setup available.

## Allowed Changes
- Install/validate the framework stack needed for smoke testing.
- Execute a minimal object-detection smoke run on COCO8.
- Record environment and smoke-run logs.

## Forbidden Changes
- Do not start Proxy dataset capture, labeling, splitting, or tuning here.
- Do not create V1/V2 specific constants.
- Do not download large training assets for this task.

## Implementation
- Run one minimal train/validate smoke iteration on COCO8.
- Record versions: Python, CUDA, Torch, GPU.
- Save reproducible command notes in `T02-smoke-notes.md`.

## Verification
- Smoke run succeeds at least once.
- No proxy learning dataset artifacts were created.

## PASS Criteria
- Environment reproducible and documented.
- V0-B still starts at T04.

## Artifacts
- `T02-smoke-notes.md`
- `env-smoke-log.txt`
