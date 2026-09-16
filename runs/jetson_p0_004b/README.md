# P0-004B candidate source publication

This directory contains the candidate-only backend factory/package architecture and
selected synthetic verification summaries. It is **not a Jetson deployment**.
TensorRT requests explicitly fail with `TENSORRT_BACKEND_NOT_IMPLEMENTED`.

The exact 32-file P0-003 runtime baseline is published in
`../jetson_p0_003/runtime/`; the 33-file P0-004B snapshot is in `candidate_runtime/`.
Their bytes and identities are recorded in `baseline_candidate_inventory.json` and
`candidate_changed_files.json`. Narrow `.gitattributes` rules disable newline
conversion for these snapshots so checkout does not change the audited SHA256 values.

The repository still ignores `runs/` by default. Only these explicitly reviewed source
snapshots, two task-local test files and selected verification summaries are tracked.
Raw hardware measurements, SSH/process dumps, model binaries, camera images,
databases, package self-test images and installed third-party source copies stay local.
References to such files in reports describe retained local evidence, not missing
publicly distributed runtime dependencies.

The recorded results are 114 baseline regression semantics and 28 new backend tests
passing on Windows. The Worker mock in the copied regression module was adapted to
the new metadata contract; original assertions were preserved. Reproduction requires
the approved local model package and P0-003 diagnostic test fixtures referenced by
the reports. These protected artifacts are not distributed in this source publication.
Do not manufacture replacement weights or treat the historical PASS as a test run on
another machine.

See `../../docs/jetson/JETSON_TRT_BACKEND_CONTRACT.md` and
`../../docs/verification/JETSON-P0-004B.json` for the scope and remaining decisions.
P0-003 raw measurements remain frozen. P0-004C is not started.
