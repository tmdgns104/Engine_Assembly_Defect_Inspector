# P004C CPU candidate evidence

Acceptance: CPU_CANDIDATE_TESTED, not native TensorRT/Jetson readiness.
Read docs/jetson/JETSON_TRT_ADAPTER_CANDIDATE.md and
docs/verification/JETSON-P0-004C.json before reuse.

The candidate is an exact descendant of frozen B, not an executable Jetson release.
Its inherited launcher is not a C launcher. Do not deploy or activate it.

Windows reproduction in the recorded worktree:

```powershell
& D:/OneDevice_Team_project/.venv/Scripts/python.exe -B -X utf8 runs/jetson_p0_004c/run_tests.py new_check test_trt_schema test_trt_preprocess test_trt_postprocess test_trt_detector test_trt_lifecycle
```

Use a fresh evidence label; old test records must not be overwritten. The runner
requires existing local baseline fixtures in D:/OneDevice_Team_project and its
P003 latency harness, as well as the worktree root tests. Those protected models,
staging images, raw installed third-party source and databases are intentionally
not published. Missing local fixtures cannot be treated as a complete regression
PASS. No dependency install is performed by this runner.

The 114 final suite preserves its original assertions; two B placeholder errors
are updated only in the C copy under Human approval. The first 114 attempt's
staging skip is retained in evidence. The final fixture ROOT points read-only to
the original staging; candidate module origins remain C.

Local-only: source/, scratch/, preservation_before.json, model_static_evidence.json,
backup archives and raw maintenance inventories. Their exclusion from Git does
not delete them. source_evidence.json publishes only hashes and source meanings.

Git publication is a separately authorized Jetson-only phase after CPU acceptance.
The sole additional existing file changed for publication is .gitattributes, to
preserve C/C0 bytes on checkout. Root runtime and Dataset/hardware are excluded.
