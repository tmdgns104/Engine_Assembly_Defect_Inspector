# ML Learning Guide (V0)

This file defines the minimum learning record policy for hands-on ML workflow tasks (`V0-T02` to `V0-T10`).

## Purpose

- Make V0 a teachable workflow, not automation-only execution.
- Record what changed and why at each major ML milestone.
- Preserve V1 handoff value for future replacement.

## Required learning note format (per task)

Create one short note per task in `docs/learning-notes/<task-id>.md`:

- What I did
- Why I did it
- What changed
- What I observed
- What this means for V1
- Decision if retraining is needed

## Required record points

### T02
- Environment setup commands and GPU/torch version check
- smoke command and result

### T04~T06
- Capture scenario list used
- Labeling quality checks
- Split strategy and leakage checks

### T07~T10
- Baseline config + metrics
- Each tuning experiment with:
  - WHY changed
  - WHAT changed
  - Metric impact
  - Resource impact
  - KEEP / REJECT
- Evaluation + error analysis summary
- ONNX parity comparison summary

## Evidence retention rule

- Save notes as text/markdown so V1 reviewers can follow the workflow quickly.
- Final PASS in V0 tasks may only reference persisted evidence.
