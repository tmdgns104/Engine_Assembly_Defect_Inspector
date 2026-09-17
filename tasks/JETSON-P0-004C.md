# JETSON-P0-004C — CPU TensorRT adapter candidate

Status: CPU_CANDIDATE_TESTED. Parent HEAD: 25b47124cb779553de2b7d67f9bc5f0d4a127447.

## Scope and approved exceptions

Implement only in runs/jetson_p0_004c/candidate_runtime, descended byte-exactly
from P004B (33 files, canonical SHA
1946d3b95f9c3e8608e210005c04d4489146265e726b6f95d82e4b2e91a91db1).
The Human's C instruction supersedes C-0's same-relative-path plan: B stays frozen;
C uses a new exact descendant. C-0 documents and docs/STATUS.md stay unchanged.

Human approved two exceptions on 2026-09-17:
- Preserve original B tests; change only two old NOT_IMPLEMENTED error expectations
  in the C-specific regression copy to CONTRACT_NON_EXECUTABLE.
- Temporary SQLite writes in isolated C tests are allowed. Existing/operational
  DB writes remain zero. Report temporary writes separately from device execution.

The latest Human Git instruction authorizes Jetson-only GitHub updates after
verification. Dataset Wizard/hardware/unrelated changes remain excluded. No Git
publication has yet occurred; implementation acceptance is a separate gate.

## Execution plan

1. Freeze parent/C-0/original workspace hashes; verify exact initial copy.
2. Resolve preprocessing, raw head, NMS and argument defaults from static installed
   source; no framework import. Missing semantics block implementation.
3. RED/GREEN additive schema/provenance/factory tests; preserve null non-executable branch.
4. RED/GREEN pure CPU preprocessing/postprocessing and high-level detector with
   injected executor only at native boundary. Native provider remains unimplemented.
5. RED/GREEN close/fatal FIFO/Service recovery and terminal-result invariants.
6. Run 114 existing + 28 approved-adapted B regressions against C origins, and new
   C tests; preserve per-test RED/GREEN evidence and forbidden-import guard results.
7. Inspect changes, frozen hashes, JSON evidence and git diff --check; report CPU
   acceptance only, then obtain the designated ChatGPT review.

## Prohibited execution

No actual torch/Ultralytics/TensorRT import, GPU/CUDA, camera, native deserialize,
export/build/trtexec, deployment/activation, actual inspection, environment changes,
PLC/MQTT. Read-only SSH static source collection only. No root runtime, P003, B,
protected models/packages, existing DB/assets or mirror modifications.

## Acceptance

Source-grounded semantics; strict executable schema and provenance; null branch
fail closed before adapter import; no fallback; stable DetectionResult and PyTorch
method AST; real CPU preprocessing/postprocessing tests; idempotent lifecycle;
ERROR-before-fault with at-most-one terminal; 142 regression PASS and new tests
PASS with skip 0; C import origins; preservation and whitespace PASS.

Completed: source gates and five RED/GREEN groups; 114 existing + 28 backend
regressions and 45 new tests PASS, skip0. The first 114 run's one missing staging
fixture skip is preserved; final harness points only fixture ROOT to the original
approved staging. No further old-test expectation changes. Framework imports,
GPU/camera/build/deploy/PLC/MQTT and existing DB writes 0. Temporary C SQLite writes
were observed under the approved exception.

Final candidate: 36 files, SHA
a2ea34eb73309b6488e10b450c197271db24b81e9bcbd4285c8a06bca686cb16.
Five files modified, three created. Original tracked474, C0 three documents,
PC mirror86 and B33 all hash-unchanged. HEAD unchanged at acceptance.

Evidence: docs/verification/JETSON-P0-004C.json and runs/jetson_p0_004c/.
Contract and limits: docs/jetson/JETSON_TRT_ADAPTER_CANDIDATE.md.
Human-approved Jetson archive/cleanup is complete, separately recorded in
D:/Jetson_Backup_20260917; it is not C deployment. No native runtime readiness claim.
Next recommendation: JETSON-P0-004D-0 static native-binding/artifact preflight.
No automatic GPU/build/deployment.

ChatGPT report review accepted CPU_CANDIDATE_TESTED, including the explicit 8400
candidate limit and production close requirement. Next recommendation is D-0 static
preflight. Jetson-only Git publication is a separate approved phase; .gitattributes
is extended only to preserve reviewed C/C0 byte identities in future checkouts.
