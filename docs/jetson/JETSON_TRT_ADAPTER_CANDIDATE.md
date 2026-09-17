# JETSON-P0-004C — CPU TensorRT adapter candidate

Status: **CPU_CANDIDATE_TESTED**, 2026-09-17. This implements and tests the host
contract, not a native TensorRT runtime or a Jetson deployment.

## Lineage and scope

The only implementation root is `runs/jetson_p0_004c/candidate_runtime/`.
It began as a byte-exact 33-file copy of P004B, canonical inventory SHA256
`1946d3b95f9c3e8608e210005c04d4489146265e726b6f95d82e4b2e91a91db1`.
Final 36-file inventory SHA256:
`a2ea34eb73309b6488e10b450c197271db24b81e9bcbd4285c8a06bca686cb16`.
Canonical inventory is SHA256 of sorted compact JSON mapping relative paths to
individual file SHA256 values. Parent, initial and final inventories are in the C
raw evidence directory. Parent B, C-0's three documents and root runtime stay frozen.

Changed: `src/contracts/interfaces.py`, `src/recipe/package.py`,
`src/vision/detector_factory.py`, `src/vision/pytorch_detector.py`,
`src/vision/inspection_worker.py`.
Created: `src/vision/tensorrt_preprocess.py`, `tensorrt_postprocess.py`,
`tensorrt_detector.py`. DetectionResult, Service, Journal, camera and Fresh Frame
implementation files are unchanged.

## Static source evidence before implementation

Installed source was read and hashed without importing frameworks. Full path,
size, SHA and line references are in `runs/jetson_p0_004c/source_evidence.json`.
Thirteen retained source files passed final SHA comparison. Key sources:

| Meaning | Installed source | SHA256 |
|---|---|---|
| LetterBox | ultralytics/data/augment.py | c9475db798443f99534f5ff9370f1ee1421999bc8dc40020fb8d256180cdb2e3 |
| BGR/RGB, contiguous, float and /255 | ultralytics/engine/predictor.py | a398a8ce75fcb4aebeb046a84ead92fd3a375b02542de309d7d1e2af52469e13 |
| Raw Detect head | ultralytics/nn/modules/head.py | c5c880204fe6dc31a01018e189482441fa20ddf3cf892c5b2826d664da138ccf |
| Defaults and NMS | ultralytics/utils/nms.py | d336cff44861dd5c84e7b7020428d9f64b408d7c21cd4b3b17d772f4b455ef83 |
| Restored coordinates | ultralytics/utils/ops.py | 79426eed013e1bb36936b52943c3c158b838e442843438d6fb811a624a039a92 |
| Torchvision suppression semantics | torchvision/ops/boxes.py | d3f35e53bd69cf2775a79842942c07a439da0dbd80ad658b68990d1e82e5c5e2 |

Checkpoint reset/predict argument merging and default config resolve class-aware
NMS (`agnostic_nms=False`), single-label argmax, `max_det=300`, no class filter.
Adapter kwargs do not override these. Confidence uses strict `>`; suppression is
same-class IoU `> threshold`. Equal IoU survives. This is source resolution, not a
new installed-framework execution. Safe ZIP/pickle opcode inspection, without
unpickling, identifies the proxy Detect head, nc=3 and `_end2end=False`.

Head source decodes xywh in letterbox pixels and concatenates sigmoid class scores;
there is no objectness field. Feature axis=1, candidate axis=2. Static640/8400 is an
explicit supported contract, never a detector inferred from an arbitrary tensor shape.
Actual artifact names, types and outputs still need native and numeric parity checks.

## Additive schema and provenance

Legacy schema1 PyTorch packages and results retain their previous semantics.
Schema2 `output=null` with `nms_location=null` remains load-contract valid but
factory activation rejects `TENSORRT_CONTRACT_NON_EXECUTABLE` before adapter import.

The executable branch requires `backend=tensorrt`, `nms_location=adapter`, source
ONNX provenance and this exact output object (example with three classes):

```json
{
  "layout": "BCN",
  "box_format": "xywh",
  "coordinate_space": "letterbox_pixels",
  "class_score_semantics": "sigmoid_probabilities",
  "objectness_semantics": "absent",
  "number_of_classes": 3,
  "tensor_shape_contract": {
    "name": "output0",
    "dtype": "float32",
    "shape": [1, 7, 8400],
    "batch_axis": 0,
    "feature_axis": 1,
    "candidate_axis": 2
  }
}
```

`name` is a required declaration, not a hardcoded actual-engine claim. Shape must
match package class count. Supported declared input/output types are float32 or
float16; engine precision declaration and binding dtype are distinct. FP16 is not
automatically selected or accepted. INT8 remains outside scope.

`detector.provenance.source_onnx` requires SHA256, `export` with tool/version/options,
and `export_environment` with python/torch/ultralytics/onnx/host_architecture strings.
The snapshot preserves source PT SHA -> declared ONNX SHA -> hashed artifact bytes
-> raw manifest SHA -> snapshot manifest_sha256. Synthetic fixtures verify identity,
shape, path and hash contracts only; they cannot prove that one real artifact was
derived from another. Build/environment null values remain unobserved declarations.
No DB migration or protected package modification occurs.

Package validation still recognizes `trt_plan` and
`ultralytics_metadata_prefixed_engine`. C activation accepts only explicit
`trt_plan`; the wrapped form fails before executor creation. Neither extension nor
bytes trigger format autodetection. Future wrapped readers must validate header
presence, bounded length, JSON shape and nonempty engine bytes; no reader exists here.

## Host implementation and execution boundary

`preprocess` accepts uint8 HWC BGR. It applies static 640x640 linear LetterBox with
auto=false, scale_fill=false, scaleup=true and centered pad114. Gain is
min(640/h,640/w), resize uses round, and split padding uses round(half-0.1/+0.1).
It returns contiguous batch1 RGB NCHW /255 and original/resized shapes, gain and
integer padding. Landscape, portrait, square and odd geometry are tested.

`postprocess` validates exact names, dtype, shape and finite probabilities; performs
single-label decode, strict confidence filtering, class-aware NMS, max300; then
subtracts padding, divides gain and clips. Confidence thresholds are compared in
the declared output dtype. CPU geometry/NMS uses float64. Equal-score order is
candidate policy: descending score, ascending class ID, ascending raw index.
This is deterministic, **not a claim of PyTorch/GPU tie or numerical parity**.
Degenerate kept boxes after clipping are errors, preserving BoundingBox invariants.
No silent empty-result fallback or wall-clock truncation is introduced.

`TensorRTExecutor` defines execute(host array)->named completed host arrays,
runtime_metadata()->JSON-compatible dict and close(). Native completion/synchronization
belongs at that boundary. C provides no production executor. The only injected
implementations are CPU test fakes at this boundary; real preprocess, postprocess,
DetectionResult, Recipe, evidence encode, Worker and Service are exercised.

`create_detector(package, latency_enabled=False, executor_factory=None)` preserves
legacy PyTorch selection. An executable TRT package with the default provider fails
`TENSORRT_NATIVE_RUNTIME_NOT_IMPLEMENTED`. It never falls back to PyTorch and does
not import torch, Ultralytics or TensorRT. No real engine is deserialized.

TensorRTDetector propagates frame_id and source PT SHA as model_version. Manifest
model_version stays the logical human label. Detection tuple, original-image xyxy,
finite confidence and empty-valid semantics stay unchanged. `inference_ms` is host
preprocess + executor completion + postprocess, never pure GPU kernel time. Optional
detector_host_total_ms defaults OFF; independent H2D remains null. Runtime metadata
separately contains plan/PT/ONNX identity, IO contracts, precision, declared provenance
and observed executor state; returned data is detached and contains no native object.

## Lifecycle and terminal results

RuntimeDetector adds close(); generic Detector does not. PyTorch adds only an
idempotent no-op close; its existing constructor, input observer, detect and metadata
method ASTs are unchanged. TensorRT close calls the executor once, even when it fails.

Worker cleanup sets stopping, closes camera, then closes detector. Legacy structural
objects lacking close are tolerated; both factory production adapters implement it.
Cleanup attempts both resources, logs failures, preserves the primary fault and emits
a cleanup fault if there was no primary failure. Early initialization failures are safe.

Input rejection before execute is recoverable. Unknown executor errors invalidate
the adapter conservatively; output-contract failure also invalidates it. This is a
usability policy, not a diagnosis of CUDA failure. FatalDetectorError causes ERROR
result, then fault on the same FIFO, no next job, and cleanup. Service's unchanged
monitor durably finishes ERROR, clears active, then enters RECOVERY on fault.
Cancellation/deadline/old session/wrong context take precedence; a second terminal
result is quarantined. Temporary SQLite tests verify one terminal event and commit
visibility from a second connection before fault handling.

## Verification and preservation

| Suite | Final result |
|---|---|
| Existing runtime + latency | 114/114, skip0 |
| P004B regression | 28/28, skip0 |
| New C behavior tests | 45/45, skip0 |
| Native framework import attempts | 0 |
| GPU, camera, export, build, deployment, PLC, MQTT | 0 |
| Existing/operational DB writes | 0 |
| Temporary C SQLite writes | Observed and explicitly approved |

RED/GREEN evidence names each test and its actual failure reason. Six Service
integration/baseline behaviors already passed at their first run; no fabricated RED
is claimed. Earlier regression evidence preserves one missing-worktree-staging skip.
The final run reads the original approved staging fixture via its existing ROOT
variable, without changing tests/data or runtime import origins.

The original B tests are unchanged. Only two placeholder error expectations in the
C copy changed under explicit Human approval. C's Fresh Frame worker regression copy
is byte-identical to B. All candidate-provided imported modules resolve to C; root
modules outside the 33-file snapshot remain the existing baseline dependencies.

Final checks: original repository 474 tracked file hashes unchanged, C-0 documents
3/3 unchanged, PC mirror 86/86 unchanged, B parent 33/33 unchanged, HEAD unchanged
at acceptance, git diff --check PASS. Existing untracked frozen raw was not written;
no blanket before/after hash claim is made for files absent from the initial inventory.

Separately, Human-authorized Jetson maintenance backed up 4,351 files and removed
1,158 archived files from 35 paths. Its remaining 3,193 files/7 protected roots are
unchanged; two guide/manifest files were added. Old removed candidates/diagnostics
are recoverable in `D:/Jetson_Backup_20260917`, not in C evidence. This is not a C
deployment, and **not all Jetson files are unchanged across that separate cleanup**.

## Remaining native blockers and next task

Native CUDA binding/provider, engine reader, deserialize, binding inspection,
allocation, transfers, synchronization and execution are not implemented. Real PT/
ONNX/plan derivation, parser/plugins, numerical tolerances, memory behavior, device
parity, production thresholds and physical conveyor acceptance remain unverified.
The previous OpenCV5/NumPy1 metadata conflict and NvMap root cause remain unresolved.

Recommend exactly one next task: **JETSON-P0-004D-0 — Native executor binding and
artifact staging preflight**, static read-only availability/API inventory and exact
execution plan. Reconcile the CPU candidate with the preserved C-0 artifact/parity
sequence before any separately scoped native implementation or Jetson execution.
C completion alone authorizes none of those device actions.

The designated ChatGPT conversation reviewed this report and accepted the CPU-only
status, including a follow-up clarification that the validator explicitly limits
candidate count to 8400. Arbitrary output families are not supported. This was
advisory review of the report, not independent code execution; see
`runs/jetson_p0_004c/chatgpt_review.json`.

READY_FOR_CHATGPT_REVIEW=true
