# JETSON-P0-004C-0 — TensorRT Execution Contract & Candidate Lineage Freeze

Status: PASS / DESIGN_ONLY. Date: 2026-09-17.

## Authorization and scope

The Human reaffirmed continued work toward the final system in coordination with
the designated ChatGPT conversation. The previous read-only audit is complete;
this is its next bounded design task. External review is advisory and cannot
authorize equipment outputs, protected-environment changes, or publication.

Create exactly this task, `docs/jetson/JETSON_TRT_EXECUTION_CONTRACT.md`, and
`docs/verification/JETSON-P0-004C-0.json` in the isolated worktree. Do not edit
STATUS, runtime, tests, packages, previous evidence, or original workspace files.
No framework imports, SSH, camera/GPU execution, export/build, installations,
SQLite writes, PLC/MQTT, commit, or push.

## Baseline

- Original workspace: `D:/OneDevice_Team_project`; master at
  `25b47124cb779553de2b7d67f9bc5f0d4a127447`, existing tracked12/untracked75 entries.
- Worktree: `D:/OneDevice_Worktrees/jetson-p0-004c0`.
- Branch: `jetson-p0-004c0-contract`, same HEAD; initially clean, 474 tracked files.
- Sole runtime parent: P004B `runs/jetson_p0_004b/candidate_runtime/`, 33 exact files.
- Canonical parent inventory SHA256:
  `1946d3b95f9c3e8608e210005c04d4489146265e726b6f95d82e4b2e91a91db1`.
- Audit comparison: 440 protected local files still identical before worktree
  creation. No further Jetson connection is needed for a local design task.

## Acceptance

One selected input/precision/container/build/postprocess/ownership contract;
explicit error and self-test gates; preserved DetectionResult meanings; exact
parent/promotion path; product-swap invariants; final-system blockers recorded.
Only actual implementation/build/parity observations may remain deferred.

Verify JSON, links, contract consistency, source/inventory identities, original
status/content preservation, all worktree tracked bytes unchanged, exact three
new files, and git diff --check. Do not rerun runtime tests for document changes.

## Source conflict resolved

The external prompt describes `model_version` as a human label. Actual
PyTorchDetector.detect returns `self.model_hash` in DetectionResult.model_version.
Preserve that result meaning; keep the human label in package.manifest.model_version.
The contract distinguishes source PT SHA, human label, and engine artifact SHA.

## Result

The designated ChatGPT review accepted the source-model SHA correction and
identified additional lifecycle/provenance precision. The contract now preserves
the legacy null schema2 branch with Factory fail-closed, requires explicit ONNX
provenance, records load_package's raw manifest hash carried by snapshot, and
specifies fatal ERROR-before-fault sequencing with at most one durable terminal
result. Future close() is additive, idempotent; PyTorch close is a no-op.

Verified: original 442 protected files and status/HEAD unchanged; worktree 474
existing tracked files unchanged; P004B exact 33-file inventory retained; PC
mirror 86 files unchanged. Three new documents only, JSON/relative links and
whitespace checks pass. Both git diff --check pass. No runtime tests re-executed.
New branch/worktree Git metadata was created, with no original working-file edit.
Jetson SSH/framework/GPU/camera/build/export/DB write/commit/push: zero in C-0.

NMS defaults have source evidence; resolved NMS/output semantics still block
native activation. Parser/plugins UNKNOWN and numeric tolerance deferred remain.
This is contract completion, not TensorRT runtime acceptance.

Next recommended single task: JETSON-P0-004C TensorRTDetector Candidate
Implementation, beginning with source evidence and CPU synthetic tests.

See [contract](../docs/jetson/JETSON_TRT_EXECUTION_CONTRACT.md) and
[verification](../docs/verification/JETSON-P0-004C-0.json).
