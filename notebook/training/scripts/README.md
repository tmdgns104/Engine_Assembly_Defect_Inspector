# Training Scripts

Command wrappers for training, validation, evaluation, and export belong here.

## Reviewed VIA → YOLO candidates

`via_to_yolo.py` reads product classes from `label_schema.json`; capture states and
removed-object metadata remain in the provenance manifest, not detection classes.
Run from the repository root using the existing Python environment:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.via_to_yolo --project <reviewed.json> --schema <label_schema.json> --provenance <provenance.json> --review-record <human_review.json> --original-root <collection-folder> --output <new-output-folder> --purpose train_candidate
```

The human review record binds `reviewed_project`, `schema` and `provenance` via
`sha256`, enumerates `approved_image_ids` / `deferred_image_ids`, and records
`user_statement` and `recorded_at`. This record must represent actual human review;
the converter never grants approval. Later box edits require a new reviewed snapshot
and corresponding approval record. Historical uncertainty notes can remain when the
human explicitly accepts those bounds; retain that resolution in the record.

Only confirmed images with nonempty valid rectangles are exported. A pending region,
invalid class/box or incomplete review withholds the whole image with reasons. Broken
hashes, IDs, scope and filename collisions fail before output creation. Output must
be new and outside both the original collection and VIA workspace. A failure during
writing preserves the incomplete folder for inspection; use a new output for retry.

Outputs: unchanged PNG copies, ten-decimal YOLO labels, `candidate_manifest.json`,
`withheld_images.json`, and `conversion_validation.json`. Filenames use collection
and capture IDs; provenance rows retain source hashes, rounds and origin groups.
Actual labels are re-read and reversed to pixels with tolerance
`max(1e-6, max(W, H) * 1e-10)`. Geometry PASS does not establish semantic accuracy.
Exit 0 means conversion PASS; exit 2 means some images were withheld. No dataset.yaml
or split is produced. `validation_candidate` is supported; sealed final test is refused.

Focused checks (synthetic files only):

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p test_via_to_yolo.py -v
```

## Reviewed candidates → grouped dataset → one GPU baseline

`build_grouped_dataset.py` consumes two converter manifests with matching product
schemas. It checks approval-input hashes, original PNG hashes, image/label pairing,
classes, coordinates and disjoint origin/session/episode/capture IDs. It writes
absolute train/val lists pointing to existing original-image copies, without moving
images or renaming acquisition groups. Shared camera calibration is documented;
physical independence is limited to the existing acquisition evidence.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.build_grouped_dataset --train <train-candidate-manifest.json> --val <validation-candidate-manifest.json> --output <new-dataset-directory>
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.train_baseline --config training/baseline_config.yaml
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.evaluate_baseline --experiment <experiment-directory>
```

The product-specific YAML supplies paths/model/training parameters; class names come
from the dataset schema. For the earbud baseline, the evaluation command also uses
`--prediction-name b03_predictions`. Future engine data uses its own schema, candidate
manifests, dataset directory and config, with the same scripts.

The runner requires a local pretrained checkpoint and working CUDA, records the
effective framework args, preserves best/last weights, and refuses a previously
started run directory. An interrupted/failed run stays available for diagnosis;
there is no automatic retry, model replacement or tuning. Fixed seed/deterministic
flags do not promise identical results across hardware/framework versions.

Evaluation reads only val, saves every prediction, and reports class-aware greedy
matches at confidence 0.25 and IoU 0.5. These counts are distinct from the validation
P/R operating point and AP confidence integration. Test remains reserved.

Focused new checks:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p test_grouped_dataset.py -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p test_baseline_matching.py -v
```

## Analyze the saved first-baseline validation

`analyze_saved_validation.py` joins stored predictions to validation provenance,
recalculates matched IoU, summarizes groups and creates separate review cards/copies.
It does not load a model, rerun prediction/training, change labels or dereference test
images. The current pilot contract is B03 60 images / 120 objects. Existing analysis
outputs are protected against overwrite. The detailed report's confidence statistics
describe predictions retained at conf0.25, not discarded candidates or calibrated probabilities.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m training.scripts.analyze_saved_validation --experiment training/experiments/earbud_case_v0_20260913_v001 --split training/outputs/datasets/earbud_case_v0_B01_B03_20260913_v001/split_manifest.json
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -p test_saved_validation_analysis.py -v
```

The generated review is initially pending assistant visual inspection. Observations,
preprocessing rationale and proposals are recorded after inspecting actual images;
the generated draft alone does not establish a visual review or human label approval.
