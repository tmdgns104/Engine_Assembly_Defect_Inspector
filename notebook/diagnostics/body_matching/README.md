# Saved-image body matching diagnostics

These are **unqualified offline comparisons**, not an alternative operating
AssemblyInspector. No runtime module imports them. They never open a camera,
write PLC values, grant an inspection, download weights during inference, or
turn a classifier's CORRECT score into geometry validity.

- `shape_matcher.py`: one bounded, orientation-aware edge/chamfer search. Edges
  are computed before selecting physical body surfaces; mask boundaries are
  not matching evidence. Competing poses are retained.
- `loftr_matcher.py`: pinned Kornia 0.8.2 LoFTR, local `indoor_new` weights,
  CUDA FP32, predeclared whole-image quarter turns. Reference body endpoints
  select correspondences, but do not establish independence from image context.
  The reference-only mask ablation is separate from the full-image experiment.
- `geometry.py`: original-pixel coordinates, physical surface labels, exact
  quarter turns and a single global similarity. `BODY_GEOMETRY_CANDIDATE` means
  a proposal, **not** an accepted pose.
- `relative_lk.py`: small-motion forward/backward tracking of manually
  identified fixed surfaces within one saved inspection. A relative transform
  cannot certify its absolute anchor. It does not implement cross-request
  identity/admission; the caller must enforce matching inspection and epoch.
- `compare.py`: immutable input/profile hashes, correspondence/support/timing
  records, known-transform controls and optional held-point measurements.

Run from a separately prepared diagnostic environment with NumPy/OpenCV and,
for C only, compatible CUDA Torch and `kornia==0.8.2`, `kornia-rs==0.1.9`:

```text
python -B notebook/diagnostics/body_matching/compare.py PRIVATE_WORK --method B
python -B notebook/diagnostics/body_matching/compare.py PRIVATE_WORK --method C
python -B notebook/diagnostics/body_matching/compare.py PRIVATE_WORK --method C --synthetic
python -B notebook/diagnostics/body_matching/compare.py PRIVATE_WORK --method C --mode reference_body_only
python -B -m unittest notebook.tests.test_body_match_geometry -v
```

`PRIVATE_WORK` holds the private `PROFILE.json`, `MANIFEST.json`,
`MANUAL_CHECKS.json` and checkpoint. The profile contains the reference path and
SHA, physical body `polygon`/`annulus` regions, four unchanged `crop_regions`,
bounded shape search configuration, and LoFTR resize/turn/weight provenance.
The manifest contains `profile_sha256` and records with name/group/path/raw SHA,
frame ID and camera epoch. Optional manual check points are evaluation data,
never fit inputs. Images, checkpoints and field annotations are not published.

Use distinct work directories for controlled reference/resolution changes.
Synthetic and real per-image JSON remain separate; `RUN.json` describes the
last invocation, not every prior experiment. Results must be joined by raw SHA,
frame ID, profile and source hash. Adjacent frames and previously seen TRAIN
controls are not independent field acceptance or a held-out evaluation.

The October 15 comparison did **not** qualify B or C for production. See
`docs/ASSEMBLY_AI_FIELD_FIX_REPORT.md` for geometry failures, conditional LK
classification, native component timing and the unchanged operating release.
