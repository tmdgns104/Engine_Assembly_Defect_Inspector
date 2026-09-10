Task ID: V0-T02
Title: ML Environment + Tiny GPU Smoke Test
Status: DONE / VERIFIED
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
- `training/experiments/t02-smoke/T02-smoke-notes.md`
- `env-smoke-log.txt`
- `training/experiments/t02-smoke/verification.json`
- `docs/learning-notes/V0-T02.md`

## Result / Evidence (V0-T02-RESUME, 2026-09-10)

- Baseline: `486ed34`; existing Windows PC `.venv` reused without installation.
- Python 3.13.5, torch 2.11.0+cu128, CUDA 12.8, CUDA available=True,
  RTX 5070 Laptop GPU, driver 610.71, Ultralytics 8.4.146 verified.
- Exactly one retained COCO8 smoke training result: yolov8n.pt, 1 epoch,
  device=0, imgsz=320, batch=8, workers=0; no new training during resume.
- Existing stdout confirms CUDA:0, GPU_mem=0.207G, TRAIN_DONE,
  duration_sec=17.97, and completed best.pt validation (4 images / 17 instances).
- Existing results.csv has one epoch row with finite validation metrics.
- best.pt and last.pt exist under `runs/detect/training/outputs/t02_smoke/weights/`;
  file sizes and hashes are recorded in verification.json.
- Failed module launch attempts: 1 (user handoff); successful Python API training: 1.
- `.venv/`, runs/checkpoints, other `.pt` files, datasets and caches are ignored;
  no Git-tracked ML binaries. Original stdout retained locally before cleanup.
- No proxy dataset artifacts, Jetson access, TensorRT work or architecture changes.
- PASS: environment and smoke evidence documented; V0-B still starts at V0-T04.
- Next: V0-T03 Core Contracts / Camera + Detector Interfaces, TODO; not started.
