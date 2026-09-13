Task ID: V0-T07
Title: Baseline Training
Status: DONE / VERIFIED — one 100-epoch Windows CUDA baseline completed
Depends On: V0-T06

## Purpose
Run one fixed-reference baseline and capture full traceability metadata.

## Required Baseline Record
- dataset version, split version
- model name and pretrained checkpoint
- seed
- epochs, image size, batch size
- optimizer and augmentation config
- hardware and framework version
- training duration
- best checkpoint path
- Precision, Recall, mAP50, mAP50-95

## Allowed Changes
- One deterministic baseline run.
- Save config, logs, and artifact paths.

## Forbidden Changes
- No large search or broad hyper-parameter sweeps.

## Verification
- Baseline artifacts load and replay with same config.

## PASS Criteria
- Baseline metrics and manifest are complete.

## Artifacts
- `training/experiments/<id>/baseline`
- `training/baseline_config.yaml`

## Result (2026-09-13)

`training/experiments/earbud_case_v0_20260913_v001/` contains the immutable run-start
record, `baseline_result.json`, `BASELINE_REPORT.md`, and validation error analysis.
`baseline/` contains effective args,100-epoch CSV/log plots, best.pt and last.pt.
Console log: `training/outputs/earbud_baseline_20260913_v001.log`.

Train120 / B03 val60 / B04 test0 reserved. YOLOv8n COCO pretrained SHA
f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36;
this is not the COCO8 smoke checkpoint.100epochs,640,batch16,seed42,AdamW lr0.001,
FP32,RTX5070 Laptop cuda:0, torch2.11.0+cu128, Ultralytics8.4.146.
Full augmentation and framework options are in `baseline/args.yaml`.

Process exit0. Training-call wall313.4217s including initialization/final validation;
epoch-loop CSV300.78s. Both artifacts reloaded on CUDA and best replayed on60 B03
images with saved prediction config. P0.9981466083/R1.0/mAP50 0.995/mAP50-95 0.8334960747.
At prediction conf0.25 and matching IoU0.5:TP120/FP0/FN0.12 new focused tests PASS.
No additional training/tuning run. B04 is not evaluated; deployment/end-to-end inspection remains outside this result.
