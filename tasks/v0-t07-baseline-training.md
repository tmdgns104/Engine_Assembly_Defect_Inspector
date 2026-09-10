Task ID: V0-T07
Title: Baseline Training
Status: TODO
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
