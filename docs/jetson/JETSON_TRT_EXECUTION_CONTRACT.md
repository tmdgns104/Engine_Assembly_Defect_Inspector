# TensorRT execution contract and candidate lineage

JETSON-P0-004C-0, 2026-09-17. DESIGN_ONLY: selected architecture, not an
implemented adapter, accepted engine, runtime deployment, or accuracy claim.
The Human requested continued development with review in the designated ChatGPT
conversation. Review informs this design; it does not authorize physical outputs,
environment changes, deployment, or publication.

## Exact parent and promotion boundary

The sole implementation parent is [P004B candidate](../../runs/jetson_p0_004b/candidate_runtime/),
33 files at HEAD `25b47124cb779553de2b7d67f9bc5f0d4a127447`.
Canonical sorted compact JSON inventory SHA256:
`1946d3b95f9c3e8608e210005c04d4489146265e726b6f95d82e4b2e91a91db1`.
Its [inventory](../../runs/jetson_p0_004b/candidate_changed_files.json) file SHA256 is
`39642bb6e1e978a876b602874e43ae1cd4825c5b312d62f2e268456320b59bbe`.

This design lives in `D:/OneDevice_Worktrees/jetson-p0-004c0`, branch
`jetson-p0-004c0-contract`, at the same HEAD. Future P004C changes descend from
that candidate at the same relative path in this isolated worktree. Its working
copy becomes the identified P004C descendant; the original workspace's P004B
snapshot and inventory remain frozen. Record a new descendant inventory and diff
against these 33 hashes; do not silently reuse the old inventory as its identity.
Do not start an unrelated fifth runtime fork or use root src/app_v007 as parent.

Promotion is: exact P004B -> P004C candidate implementation and CPU contract tests
-> P004D isolated artifacts -> P004E numeric/decision parity -> P004F explicitly
authorized Jetson candidate validation -> separately reviewed deployment.
No step selects a current symlink, active package, production DB, or device output.
P003 runtime/raw/timing numbers stay frozen. C-0 creates only three documents.

## Actual installed, deployed, and running state

These are 2026-09-17 read-only observations, not new execution acceptance.
Jetson facts reuse the immediately preceding audit; C-0 SSH calls are zero.

| Boundary | Windows laptop | Actual Jetson |
|---|---|---|
| OS/device | Windows 11 Home build 26200, Ryzen 7 260, RTX 5070 Laptop | Orin Nano Engineering Reference Developer Kit Super, L4T 36.4.7, aarch64 |
| Python | Repository .venv, 3.13.5; system/user sites excluded | envs/app_v1, 3.10.12; system and user sites visible |
| Torch / Ultralytics | 2.11.0+cu128 / 8.4.146, distribution metadata | 2.8.0 / 8.4.118, mostly ~/.local/lib/python3.10/site-packages |
| NumPy / OpenCV | 2.5.2 / opencv-python 5.0.0.93 | Default 2.2.6 / 5.0.0.93; separate process-local NumPy 1.26.4 overlay |
| TensorRT | No distribution in inspected .venv; not a system-wide absence claim | 10.3.0 system distribution; dpkg 10.3.0.30-1+cuda12.5 |
| CUDA | Torch distribution label cu128, no GPU execution | version.json SDK 12.6.11 / cudart 12.6.68; historical torch CUDA 12.6 |
| Runtime code | Root concrete PyTorch; P003 latency and P004B factory snapshots separate | releases/app_v007; P002, P002R2, P003 candidates; no P004B deployment |
| App/connection state | Edge/collector/tunnel listeners absent at observed ports | Inspection app stopped; health connection refused; current symlinks absent |
| Camera | No new capture | HCAM0 device nodes present; historical MJPG 1280x720@30, not re-tested |
| Persisted package | Earbud proxy package and disabled ENGINE_Z3005_5/unprepared | DB selection points to app_v007 earbud/app_v001; not currently loaded |
| Stored evidence | PC mirror 72 asset files; DB 4 KiB plus ~2 MB WAL and SHM | data/app_v1 DB 561152 bytes and 72 asset files |

The Windows Dataset Wizard EXE under dist is a separate capture application, not
the Edge inspection HMI or deployed TRT adapter. Its bundled dependencies were
not inferred from .venv. A 4 KiB PC DB with a nonempty WAL is not evidence of an
empty history; C-0 does not open/checkpoint it. The previous audit used an
immutable read-only SELECT for persisted package selection; DB writes were zero.

Both devices have source PT SHA
`49f533e4e4e5846d1582564d8efbb38a647ad10348a976db9085d94df16250c1`.
The existing Windows ONNX SHA
`ef8b5918b69c7ca4d073e0564f696688e2292b957d3fab852dd680cbe928e209`
is HISTORICAL_CANDIDATE_ARTIFACT, not ACCEPTED_BUILD_INPUT. Shape/hash existence
does not establish PT/ONNX parity, parser compatibility, or TRT readiness.

The NumPy/Torch bridge history, NumPy1 overlay/OpenCV metadata conflict, and
intermittent NvMap ROOT_CAUSE_UNCONFIRMED remain KNOWN_RUNTIME_RISK. They do not
justify changing dependencies in this design task or declaring TRT validated.

## Selected architecture

```text
Windows: Dataset / training -> source.pt
                              |
                     isolated ONNX export
                              |
                  source.onnx + SHA + provenance
                              |
                     validated transfer/staging
                              v
Jetson:            target TensorRT build
                              |
                     model.plan + SHA
                              |
                        Product Package
                              |
                        Detector Factory
                         /            \
                  pytorch            tensorrt
                     |                  |
              PyTorchDetector    TensorRTDetector (future)
                                        |
                               long-lived runtime
CameraFrame ----------------------------+
                                        |
                           preprocess -> TRT plan
                                        |
                          raw outputs -> decode/filter
                                        |
                             NMS -> restore coordinates
                                        |
                                 DetectionResult
                                        |
                     Existing Worker -> Existing Service
                                        |
                              Journal / PC Sync / HMI
```

| Concern | Selected V1 contract |
|---|---|
| Input | Batch 1, static [1,3,640,640], NCHW; uint8 HWC BGR CameraFrame source |
| Preprocess | BGR->RGB, linear aspect-preserving letterbox, pad 114, divide 255, contiguous NCHW; rect/crop/augmentation false |
| Precision | FP16 engine candidate target; FP32 reference allowed; not production accepted |
| Binding dtype | Declared and inspected float32 or float16; never inferred from FP16 build option |
| Container | Explicit trt_plan, raw serialized plan; no extension/header autodetection |
| Build lifecycle | Windows controlled PT->ONNX export; Jetson target build in isolated staging |
| Artifact portability | TARGET-BOUND; no assumption that a Windows-built plan runs on Jetson |
| Decode/NMS owner | Project TensorRT adapter; engine-embedded NMS excluded from V1 |
| Runtime owner | Existing Vision Worker process, single active inspection |
| Framework dependency | TRT path does not require torch, ultralytics, onnx, or onnxruntime |
| Fallback / hidden retry | None, including PyTorch fallback, CPU fallback, reduced input size, or empty detections on error |

BUILD_DEPENDENCIES != PRODUCTION_RUNTIME_DEPENDENCIES. Export and parser/builder
tools belong to staging, not the inference dependency graph. Host preprocessing
may still use NumPy/OpenCV. TRT must not call torch.from_numpy. Factory imports
an adapter only after explicit backend selection. Unselected backends do not
initialize their frameworks. Low-level CUDA binding choice is DEFERRED_TO_P004C
read-only availability/API inventory; missing bindings block native activation,
not pure contract tests. No automatic installation is permitted.

Exact exporter/builder commands, workspace limits, compatibility options and
observed IO dtype belong to P004D evidence. Disable tool auto-install behavior;
never export next to protected PT/ONNX/package artifacts. Validate a historical
ONNX before reuse, or export a separately identified replacement in staging.
No build or export occurs in C-0.

## Additive package lifecycle

Source: [package.py](../../runs/jetson_p0_004b/candidate_runtime/src/recipe/package.py),
validate_backend/load_package/ProductPackage.snapshot.

| Existing or future declaration | Meaning |
|---|---|
| Valid schema1 legacy detector without backend | PYTORCH_LEGACY_DEFAULT, unchanged |
| Explicit schema1 backend=pytorch | Existing PyTorch behavior unchanged |
| Schema2 output=null and preprocessing.nms_location=null | CONTRACT_VALID_NON_EXECUTABLE; existing fixtures stay valid |
| Future schema2 explicit output object and nms_location=adapter | EXECUTABLE_CANDIDATE only; requires explicit provenance and activation gates |
| Unknown backend/format or mixed/null-incomplete executable fields | Explicit rejection, never a legacy default |

Schema2 alone never implies runtime-ready. C-0 does not alter today's validator,
which permits only the null output branch and rejects executable objects.
Future additive validation preserves that branch without relaxing executable
requirements. A contract-valid fake engine remains a fake, non-executable fixture.
Even after TensorRTDetector exists, Factory rejects the null branch with
TENSORRT_CONTRACT_NON_EXECUTABLE before adapter import/activation. Tests must prove
zero native loader/model/GPU calls for this branch; removal of today's generic
NOT_IMPLEMENTED error must not accidentally activate old fixtures.

For the future executable branch, detector.output must explicitly declare:
`layout`, `box_format`, `coordinate_space`, `class_score_semantics`,
`objectness_semantics`, and `tensor_shape_contract`. The shape contract includes
exact tensor name(s), dtype(s), batch/channel/candidate axes and relationship to
the ordered package class count. No dimension or suffix alone identifies a head.
Supported enum values must follow captured model/export evidence before C
implements a decoder; unknown semantics prevent activation. Segmentation,
rotated boxes, end-to-end/NMS outputs and alternative heads are not silently
treated as ordinary detection outputs. Historical [1,7,8400] is shape evidence,
not proof of xywh, score activation, objectness, or anchors.

Require `detector.provenance.source_onnx` in the executable branch with explicit
`sha256`, `export` and `export_environment`. `export` contains tool/version/options;
export_environment records Python/framework/exporter/ONNX versions and host
architecture. This follows existing source_model_sha256/build naming and separates
intermediate identity from build options. Retain build and build_environment for
the target TRT tool/options/TRT/CUDA/L4T/GPU capability/plugins. Exact values must
be observed; unknown fields cannot masquerade as accepted compatibility.

```text
detector.source_model_sha256 (PT)
       -> detector.provenance.source_onnx.sha256
       -> files.model.sha256 (raw plan)
       -> ProductPackage.manifest_hash / snapshot.manifest_sha256
       -> durable Journal package snapshot
```

load_package computes manifest_hash from the raw manifest.json bytes; snapshot()
carries that existing value as manifest_sha256 and does not calculate a new hash.
The manifest does not store its own hash. Source ONNX can remain a build archive rather than an extra runtime file;
its content-addressed archive/evidence must be retrievable for promotion. A
trusted build report binds every hop. Hash declarations alone prove integrity,
not semantic parity or trust. Runtime metadata reports declared build provenance
separately from observed runtime versions. No DB schema migration is required:
the detached JSON package snapshot already carries the complete manifest.

Both P004B format literals remain recognized as declarations: trt_plan and
ultralytics_metadata_prefixed_engine. Only trt_plan is the selected V1 execution
format. The second is explicitly unsupported for V1 execution. Any future
wrapped reader requires header-length presence/bounds, JSON decode/shape checks
and nonempty remaining plan bytes (FUTURE_READER_VALIDATION_REQUIRED); no
UnicodeDecodeError fallback or four-byte heuristic selects a format.

## Decode, NMS, and coordinates: evidence versus proposed policy

Preserved Jetson cfg/default.yaml has agnostic_nms=False, max_det=300 and
classes=null. Its SHA is
`9ad9a3150cedb839f7c1a352d37b578aaccd2db107ad63cea2e0bafce2966b71`,
matching P004A remote source inventory. Cached P003 DetectionPredictor.postprocess
passes args.conf/iou/classes/agnostic_nms/max_det to non_max_suppression;
construct_result calls scale_boxes after NMS. P003 scale_boxes subtracts padding,
divides by gain, then clips. P004B PyTorchDetector.predict explicitly supplies
package confidence/iou but not agnostic_nms or max_det.

Thus class-aware NMS with maximum 300 is the **source-backed default candidate**.
It is not a newly observed resolved predictor setting. The captured files do not
include nms.py contents or resolved predictor overrides. NMS_MODE_ACTIVATION_BLOCKER
remains until C reads the matching config-resolution/NMS source or existing
resolved-argument evidence. No SSH/framework execution is added merely to clear
it in C-0. Exact comparison operator, multi-label handling and score tie behavior
also require that source check before claiming PyTorch equivalence.

The following is an explicit candidate policy for tests, not measured parity:

1. Validate output names/shapes/dtypes, finite values and declared raw semantics.
   Decode only a supported, evidenced contract. Do not guess sigmoid/objectness.
2. Use the package confidence threshold. Proposed single-label policy chooses
   the highest class score, lowest class ID on ties, and retains score strictly
   greater than threshold. Validate this against the source before activation.
3. Proposed class-aware greedy NMS operates in letterboxed coordinates; suppress
   only same-class overlap with IoU strictly greater than package nms_iou.
   Sort by descending score, then class ID, then original raw candidate index.
   Keep at most 300 overall. Never introduce a hidden class filter or input cap.
4. Restore kept xyxy using recorded resize gain/padding, then clip to original
   [0,width] and [0,height]. Do not clip before NMS. Degenerate or nonfinite
   final boxes are OUTPUT_CONTRACT_MISMATCH, not a successful empty response.
5. Retain stable sorting for output. Identical-score tie resolution is an explicit
   deterministic candidate rule, not a claim about GPU NMS ordering. Parity must
   compare matchable detections and investigate decision-changing ties.

Letterbox integer rounding, max-NMS candidate handling and reference operator
details are DEFERRED_SOURCE_EVIDENCE, blocking semantic acceptance before native
activation. C may write failing/synthetic tests and pure helpers but may not
declare parity based on those tests. Evidence conflicting with the proposed
policy must update this design explicitly before implementation acceptance.

## Stable results, metadata, and latency

Source: [models.py](../../runs/jetson_p0_004b/candidate_runtime/src/contracts/models.py),
[PyTorchDetector](../../runs/jetson_p0_004b/candidate_runtime/src/vision/pytorch_detector.py),
[factory](../../runs/jetson_p0_004b/candidate_runtime/src/vision/detector_factory.py).

Keep detect(CameraFrame)->DetectionResult, frame_id propagation, ordered class
IDs/names, finite score [0,1], original-image nonnegative valid xyxy and existing
serialization fields. An empty result means zero objects after valid inference,
never failed inference. Keep source frame/evidence associations and Recipe inputs.

| Identity | Meaning |
|---|---|
| manifest.model_version | Human logical model/release label |
| DetectionResult.model_version | Legacy source detector PT SHA; PyTorch self.model_hash unchanged, TRT source_model_sha256 |
| files.model.sha256 | Executed artifact SHA: PT or TRT plan |
| runtime_metadata.artifact_sha256 | Executed artifact SHA, separate from source_model_sha256 |

No field rename, migration, or reinterpretation of historical PyTorch results.
RuntimeDetector.runtime_metadata returns detached finite JSON: backend, artifact
and source identity, device, input contract, observed runtime and optional timing.
No native handles or framework objects cross the Worker boundary.

latency_enabled defaults OFF. PyTorch synchronize calls and inference_ms timer
stay unchanged: its timer surrounds synchronized predict, not pure kernels,
and precedes final boxes-to-CPU/list conversion. TRT legacy inference_ms, if
populated, is explicitly adapter host-observed inference-path elapsed time with
completion synchronization, not a cross-backend identical-segment GPU metric.
Its exact segment label is recorded in runtime timing metadata; optional
detector_host_total_ms is the full host detect call. Unobserved h2d_ms remains
null. Do not invent Ultralytics timing for TRT or sum component percentiles.

## Ownership, cleanup, errors, and readiness

Worker constructs one detector per worker lifetime. TRT adapter owns runtime,
engine, execution context, CUDA stream and reusable IO buffers in that process.
Allocate after shape/dtype validation; reject unbounded/dynamic shapes and unsafe
sizes before allocation. Requests reuse resources serially. Service, Journal,
Camera and HMI own none of those GPU objects. Do not deserialize per inspection.

Future C minimally extends RuntimeDetector with idempotent close(), implements
PyTorch close as an idempotent no-op, and calls detector.close exactly once in
the normal Worker finally lifecycle if constructed, after in-flight native work
completes. Repeated close is safe; cleanup errors never mask the primary failure.
The current RuntimeDetector has no close method and current Worker finally closes
only the camera. Release stream/buffers/
context/engine/runtime in dependency-safe order, including partial-init failure.
No forced GC, empty_cache, hidden retry, reconnect, environment mutation or
destruction while a call is in flight. Exact low-level release APIs are binding
evidence, not guessed in this design. No Detector implementation in C-0.

| Error | Boundary | Required lifecycle outcome |
|---|---|---|
| ENGINE_MISSING / ARTIFACT_HASH_MISMATCH | Init/package | No READY; report fault; no new inspection |
| ARTIFACT_FORMAT_UNSUPPORTED | Init | Reject declared unsupported format before deserialization |
| ENGINE_DESERIALIZE_FAILED | Init | Cleanup partial resources; Worker fault, Service recovery |
| BINDING_CONTRACT_MISMATCH | Init | Reject names/count/modes/shapes/dtypes/unsafe allocation sizes |
| SELF_TEST_FAILED | Init | No READY, preserve diagnostic cause |
| INPUT_CONTRACT_MISMATCH | Request | Existing terminal ERROR path, durable result before publication |
| INFERENCE_FAILED | Request/native | Terminal ERROR if admission exists; mark detector unusable, Worker fault/recovery; no next job |
| OUTPUT_CONTRACT_MISMATCH | Request | Terminal ERROR, invalidate suspect execution contract; no empty-result fallback |

Package errors remain PackageError; detector errors use DetectorError with stable
codes and chained diagnostic cause. Future adapter/Worker lifecycle must preserve
at most one durable terminal result per inspection and reject late/canceled/
old-session results.
An initialization failure has no admitted inspection to fabricate. The current
Worker catches job errors and can continue; C must explicitly test fatal TRT
error propagation so a poisoned context never continues through that path.
Service RECOVERY/health behavior must reflect the actual Worker state, not a
nominal successful constructor. Existing PyTorch request semantics stay intact.

For a fatal request-time detector failure, enqueue the ERROR result followed by
fault in the same FIFO result channel, then stop accepting jobs. For a still
context-valid active request, Service handles durable finish and clears active
before handling fault and entering RECOVERY. If deadline/cancel/context rejection
already applies, existing cancel/quarantine semantics prevail: do not fabricate
a duplicate terminal ERROR. CPU synthetic tests must prove ordering, at-most-once
durability, no subsequent execution, and cleanup preserving the original cause.
A recoverable input error can finish ERROR while the detector remains usable.

Future activation gate (all required, no schema-only READY): safe path -> hash ->
declared format -> deserialize -> exact binding contract -> bounded buffers ->
approved hashed self-test image -> preprocess -> inference/completion -> finite
output -> evidenced decode/NMS -> valid DetectionResult -> correct metadata.
The old optional PyTorch self-test remains backward compatible; executable TRT
activation requires it. Self-test is not model accuracy or physical acceptance.

Publication remains after Journal.finish commit. Filesystem asset persistence
and SQLite are not one atomic transaction. Local diagnostic handoff is not a
network/PLC ACK. Native failure must not publish a PASS or bypass durable ERROR.

## Product swap and final-system backlog

PRODUCT_SWAP_INFRASTRUCTURE=PARTIAL. ENGINE_MODEL_ACCEPTANCE=BLOCKED.
Generic runtime must preserve Camera ownership, FreshFrameSelector, Worker,
Service/lifecycle/IDs/deadlines, result contract, Journal/assets/SHA, PC sync,
HMI shell, backend factory, health and future PLC/tracking architecture.
Replace only artifact, classes, preprocessing/output contract, Recipe/counts/
slots/thresholds, calibration/capture profile and package metadata. A new model
head outside the supported output contract needs an explicit adapter contract
extension; product swap does not promise support for every arbitrary network.

| Follow-up backlog, not implemented here | Required acceptance |
|---|---|
| Same-class manual slot assignment | Calibration UI/API can assign LEFT/RIGHT instances without class-name hacks |
| Moving conveyor geometry | Capture-zone normalization or localization/tracking; fixed-reference IoU is not assumed valid |
| PLC disposition | Human policy for PASS/FAIL/REVIEW/ERROR, safe timeout/unknown handling |
| Multi-product tracking/reject timing | Sensor cycle/inspection/physical position/reject correlation with physical evidence |
| Evidence crash recovery | Power-loss/restart reconciliation of filesystem assets and SQLite; PARTIAL_FINAL_SYSTEM |

ENGINE training blocks its own accuracy/parity/final physical acceptance, not
earbud-backed common infrastructure and synthetic PLC/HMI development. Preserve
existing P005 Mock PLC, P006 heartbeat and P007 Omron numbering. No motor, pusher,
PLC output, MQTT, new inspection, or package activation follows from this document.

## Deferred evidence and verification

DEFERRED_TO_P004C: installed CUDA binding API selection, output family/source
semantics, resolved NMS behavior, implementation and CPU contract/regression tests.
DEFERRED_TO_P004D: exporter/builder commands, actual graph/bindings/precision,
target resource options and observed provenance. PARSER_COMPATIBILITY=UNKNOWN;
REQUIRED_PLUGINS=UNKNOWN. DEFERRED_TO_P004E: numeric parity tolerance and accuracy
comparison (PARITY_NUMERIC_TOLERANCE=TBD_FROM_EMPIRICAL_PARITY_EVIDENCE).
DEFERRED_TO_P004F: actual integrated candidate execution. FINAL_ENGINE_PRODUCT_MODEL
=NOT_EVALUATED; production thresholds and physical conveyor acceptance absent.

Current source-backed design selects build lifecycle, FP16 target and adapter
decode ownership; historical P004A pending decisions remain unchanged in frozen
P004A evidence. This document supersedes those design choices prospectively,
without turning compatibility UNKNOWNs into PASS.

See [task](../../tasks/JETSON-P0-004C-0.md) and
[verification](../verification/JETSON-P0-004C-0.json). Verification checks three
new documents, JSON/links, exact parent inventory, unchanged worktree tracked
files, unchanged original workspace protected hashes/status and diff whitespace.
No runtime tests are re-executed for a document-only task. Prior 114+28 tests are
historical evidence, not C-0 execution. Jetson preservation here means zero
remote operations, not a fresh remote after-hash measurement.
