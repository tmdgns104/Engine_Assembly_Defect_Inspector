# JETSON-P0-004B — Backend Factory & Package Contract

Status: DONE / BACKEND_CONTRACT_IMPLEMENTED_CANDIDATE_ONLY. User authorized candidate-only architecture implementation.

Baseline: exact P0-003 local runtime bytes must match its deployed SHA inventory.
Changes only in `runs/jetson_p0_004b/candidate_runtime`, task-local tests/evidence,
this Task, new contract/verification documents and STATUS. Root runtime, old evidence,
packages/models/DB/assets/PC mirror and all Jetson source/environments remain protected.

Implement explicit factory selection, strict legacy-compatible package branch, neutral
runtime metadata and Worker integration. Keep DetectionResult and P003 timing semantics.
TRT selection must fail NOT_IMPLEMENTED without imports, model load or PyTorch fallback.
Synthetic artifact validation is schema/path/hash only; no engine reader/deserialize.

Verification: tests first; rerun existing114 against actual candidate origins; add backend
contract tests, preservation SHA and git diff --check. No hardware/deploy/export/build,
dependency/settings changes, commits or pushes. P004C needs separate authorization.

Pending: EXPORT_PATH/PRECISION/DECODE_NMS DECISION_PENDING; PARSER/PLUGINS UNKNOWN;
PARITY tolerance TBD; final engine-product model NOT_EVALUATED.

## Verified result

P003 exact32-file snapshot; candidate3 modified+factory1 added. Original Detector methods/DetectionResult unchanged.
114/114 baseline regression semantics (one task-local mock class adapted; existing assertions unchanged)
and28/28 new contracts PASS, no skips. All runtime import origins candidate; real framework import0.
Legacy package/snapshot preserved; schema2 synthetic artifact is CONTRACT_VALID_NON_EXECUTABLE.
TRT factory explicitly NOT_IMPLEMENTED without fallback/read/import. Protected local/remote SHA identical,
HEAD unchanged, git diff --check PASS. GPU/camera/export/build/inference/deploy/commit/push0.
Report: docs/jetson/JETSON_TRT_BACKEND_CONTRACT.md; verification: docs/verification/JETSON-P0-004B.json.
P004C NOT_STARTED; pending choices above remain unresolved.
