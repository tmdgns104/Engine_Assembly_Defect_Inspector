"""Read-only product package verification. Activation and GPU loading belong to Service/Worker."""

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


class PackageError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise PackageError(message)


def backend_resolution(manifest):
    """Only schema1's original detector shape can omit the backend declaration."""
    detector = manifest.get("detector")
    require(isinstance(detector, dict), "BACKEND_CONTRACT_INVALID: detector must be an object")
    declared = detector.get("backend")
    if "backend" not in detector:
        require(manifest.get("schema_version") == 1 and
                detector == {"task": "detect", "output": "ultralytics_xyxy"},
                "BACKEND_CONTRACT_INVALID: no valid legacy default")
        return {"declared_backend": None, "resolved_backend": "pytorch",
                "resolution_basis": "PYTORCH_LEGACY_DEFAULT"}
    require(isinstance(declared, str) and declared in ("pytorch", "tensorrt"), "UNSUPPORTED_BACKEND")
    return {"declared_backend": declared, "resolved_backend": declared, "resolution_basis": "EXPLICIT"}


def valid_sha256(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_output_contract(output, class_count=None):
    """One evidenced raw Detect head family, never inferred from suffix or dimensions."""
    error = "TENSORRT_CONTRACT_NON_EXECUTABLE"
    expected = {"layout":"BCN", "box_format":"xywh", "coordinate_space":"letterbox_pixels",
                "class_score_semantics":"sigmoid_probabilities", "objectness_semantics":"absent"}
    require(isinstance(output, dict) and set(output) == set(expected) | {
        "number_of_classes", "tensor_shape_contract"}, error)
    require(all(output[key] == value for key, value in expected.items()), error)
    count = output["number_of_classes"]
    require(type(count) is int and count > 0 and (class_count is None or count == class_count), error)
    tensor = output["tensor_shape_contract"]
    require(isinstance(tensor, dict) and set(tensor) == {
        "name", "dtype", "shape", "batch_axis", "feature_axis", "candidate_axis"}, error)
    require(isinstance(tensor["name"], str) and bool(tensor["name"].strip()), error)
    require(tensor["dtype"] in ("float32", "float16"), error)
    require(isinstance(tensor["shape"], list) and all(type(v) is int for v in tensor["shape"])
            and tensor["shape"] == [1, 4 + count, 8400], error)
    require(all(type(tensor[key]) is int and tensor[key] == value for key, value in
                (("batch_axis",0), ("feature_axis",1), ("candidate_axis",2))), error)


def validate_source_onnx(source):
    error = "TENSORRT_CONTRACT_NON_EXECUTABLE: source_onnx provenance"
    require(isinstance(source, dict) and set(source) == {"sha256", "export", "export_environment"}, error)
    require(valid_sha256(source["sha256"]), error)
    export = source["export"]
    require(isinstance(export, dict) and set(export) == {"tool", "version", "options"}, error)
    require(all(isinstance(export[key], str) and export[key].strip() for key in ("tool", "version"))
            and isinstance(export["options"], dict), error)
    environment = source["export_environment"]
    require(isinstance(environment, dict) and set(environment) == {
        "python", "torch", "ultralytics", "onnx", "host_architecture"}, error)
    require(all(isinstance(value, str) and value.strip() for value in environment.values()), error)


def validate_backend(manifest):
    backend = backend_resolution(manifest)["resolved_backend"]
    detector = manifest["detector"]
    if backend == "pytorch":
        expected = {"task": "detect", "output": "ultralytics_xyxy"}
        if "backend" in detector:
            expected["backend"] = "pytorch"
        require(manifest["schema_version"] == 1 and detector == expected,
                "BACKEND_CONTRACT_INVALID: unsupported PyTorch contract")
        return backend
    require(manifest["schema_version"] == 2, "BACKEND_CONTRACT_INVALID: TensorRT requires schema2")
    require(set(detector) == {"backend", "task", "output", "input", "precision",
                              "source_model_sha256", "provenance"}, "BACKEND_CONTRACT_INVALID: TensorRT fields")
    require(detector["task"] == "detect", "BACKEND_CONTRACT_INVALID: task")
    executable = detector["output"] is not None
    if executable:
        validate_output_contract(detector["output"])
    require(detector["precision"] is None or detector["precision"] in ("fp32", "fp16"),
            "BACKEND_CONTRACT_INVALID: precision declaration; INT8 out of scope")
    require(valid_sha256(detector["source_model_sha256"]), "BACKEND_CONTRACT_INVALID: source_model_sha256")
    inputs = detector["input"]
    require(isinstance(inputs, dict) and set(inputs) in (
                {"shape", "dtype", "layout"}, {"name", "shape", "dtype", "layout"}),
            "BACKEND_CONTRACT_INVALID: input fields")
    if "name" in inputs:
        require(isinstance(inputs["name"], str) and bool(inputs["name"].strip())
                and "\0" not in inputs["name"] and len(inputs["name"].encode("utf-8")) < 4096,
                "BACKEND_CONTRACT_INVALID: input name")
    shape = inputs["shape"]
    require(isinstance(shape, list) and len(shape) == 4 and all(type(x) is int and x > 0 for x in shape)
            and shape[:2] == [1, 3] and inputs["layout"] == "NCHW"
            and inputs["dtype"] in ("float32", "float16"), "BACKEND_CONTRACT_INVALID: input declaration")
    provenance = detector["provenance"]
    fields = {"build", "build_environment"} | ({"source_onnx"} if executable else set())
    require(isinstance(provenance, dict) and set(provenance) == fields,
            "BACKEND_CONTRACT_INVALID: provenance fields")
    try:
        canonical(provenance)
    except (ValueError, TypeError) as error:
        raise PackageError("BACKEND_CONTRACT_INVALID: provenance must be finite JSON") from error
    if executable:
        validate_source_onnx(provenance["source_onnx"])
        require(inputs["shape"] == [1, 3, 640, 640] and detector["precision"] in ("fp32", "fp16"),
                "TENSORRT_CONTRACT_NON_EXECUTABLE: static input/precision required")
    build, environment = provenance["build"], provenance["build_environment"]
    require(isinstance(build, dict) and set(build) == {"tool", "version", "options"}
            and isinstance(build["options"], dict), "BACKEND_CONTRACT_INVALID: build provenance")
    require(isinstance(environment, dict) and set(environment) == {"tensorrt", "cuda", "l4t", "gpu_compute_capability", "plugins"},
            "BACKEND_CONTRACT_INVALID: build environment")
    # Null means unobserved, never compatibility PASS. These are declarations, not runtime checks.
    for value in (build["tool"], build["version"], *(environment[k] for k in ("tensorrt", "cuda", "l4t", "gpu_compute_capability"))):
        require(value is None or isinstance(value, str) and bool(value.strip()), "BACKEND_CONTRACT_INVALID: provenance value")
    plugins = environment["plugins"]
    require(plugins is None or isinstance(plugins, list) and all(isinstance(x, str) and x.strip() for x in plugins),
            "BACKEND_CONTRACT_INVALID: plugins declaration")
    return backend


def integer(value, minimum, maximum, name):
    require(type(value) is int and minimum <= value <= maximum, f"Invalid {name}")


def box(value, normalized=False):
    require(isinstance(value, list) and len(value) == 4, "Box must be xyxy")
    require(all(type(x) in (int, float) and math.isfinite(x) for x in value), "Box must be finite")
    require(0 <= value[0] < value[2] and 0 <= value[1] < value[3], "Invalid box extent")
    if normalized:
        require(max(value) <= 1, "Normalized box outside image")


def validate_recipe(recipe, names):
    require(recipe.get("schema_version") == 1, "Unsupported recipe schema")
    require(bool(recipe.get("recipe_id")) and bool(recipe.get("version")), "Missing recipe identity")
    require(recipe.get("coordinate_space") == "normalized_image", "Unsupported slot coordinate system")
    require(recipe.get("alignment_mode") in ("human_fixed_reference", "fixed_profile", "engine_affine"), "Unsupported alignment mode")
    if recipe.get('alignment_mode') == 'engine_affine':
        settings=recipe.get('engine_pose',{})
        require(isinstance(settings,dict) and set(settings)=={'path','sha256','envelope_package','envelope_manifest_sha256'}, 'Invalid engine pose reference')
        require(valid_sha256(settings['sha256']) and valid_sha256(settings['envelope_manifest_sha256']) and all(isinstance(settings[k],str) and settings[k] for k in ('path','envelope_package')), 'Invalid engine pose provenance')
    require(recipe.get("visibility_mode") == "human_per_request", "Automatic visibility is not verified")
    require(recipe.get("rule") == "presence_count", "Unsupported rule")
    slots = recipe.get("slots")
    require(isinstance(slots, list) and 0 < len(slots) <= 64, "Empty or excessive required slots")
    identifiers = set()
    # 선택적 제품 사유 코드는 레시피 소유다. 기존 레시피는 변경 없이 유효하다.
    def reason_code(document, key):
        if key in document:
            value = document[key]
            require(isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", value) is not None,
                    f"Invalid recipe reason code: {key}")
    reason_code(recipe, "all_targets_missing_reason_code")
    for slot in slots:
        reason_code(slot, "missing_reason_code")
        require(isinstance(slot.get("id"), str) and bool(slot["id"].strip()), "Invalid slot ID")
        require(slot["id"] not in identifiers, "Duplicate slot")
        identifiers.add(slot["id"])
        allowed = slot.get("allowed_classes")
        require(isinstance(allowed, list) and allowed and len(set(allowed)) == len(allowed)
                and set(allowed) <= set(names), "Invalid slot classes")
        integer(slot.get("expected_count"), 1, 64, "expected count")
        box(slot.get("region"), normalized=True)
        require(isinstance(slot.get("display"), str) and bool(slot["display"].strip()), "Missing slot display")
    reference = recipe.get("reference_class")
    require(reference is None or reference in names, "Unknown reference class")
    for key in ("presence_confidence", "reference_confidence", "slot_overlap", "reference_iou"):
        value = recipe.get(key)
        require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 1, f"Invalid {key}")
    integer(recipe.get("observation_count"), 1, 16, "observation count")
    require(isinstance(recipe.get("required_views"), list) and recipe["required_views"] == ["top"], "Only top view is supported")
    require(recipe.get("orientation_verified") is False, "Automatic orientation verification is unsupported")


@dataclass(frozen=True)
class ProductPackage:
    root: Path
    manifest: dict
    classes: dict
    preprocessing: dict
    recipe: dict
    capture: dict
    manifest_hash: str

    @property
    def backend_resolution(self):
        return backend_resolution(self.manifest)

    @property
    def backend(self):
        return self.backend_resolution["resolved_backend"]

    @property
    def model_path(self):
        return self.root / self.manifest["files"]["model"]["path"]

    @property
    def names(self):
        return [item["name"] for item in self.classes["classes"]]

    def snapshot(self):
        # Return a detached JSON value so no caller can mutate an in-flight package.
        value = {"manifest": self.manifest, "classes": self.classes,
                 "preprocessing": self.preprocessing, "recipe": self.recipe,
                 "capture": self.capture, "manifest_sha256": self.manifest_hash}
        # Exact old explicit-PyTorch snapshots stay identical. New/defaulted contracts record resolution.
        if self.backend != "pytorch" or self.backend_resolution["declared_backend"] is None:
            value["backend_resolution"] = self.backend_resolution
        return json.loads(canonical(value))


def load_package(directory):
    root = Path(directory).resolve()
    raw = (root / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] in (1, 2), "Unsupported package schema")
    require(manifest.get("enabled") is True, "Package is not enabled")
    for key in ("release_id", "product_id", "model_version"):
        require(isinstance(manifest.get(key), str) and bool(manifest[key].strip()), f"Missing {key}")
    backend = validate_backend(manifest)
    require(set(manifest.get("files", {})) in ({"model", "classes", "preprocessing", "recipe", "capture"},
                                               {"model", "classes", "preprocessing", "recipe", "capture", "self_test"}), "Incomplete package")
    documents, paths = {}, set()
    for kind, entry in manifest["files"].items():
        require(isinstance(entry, dict) and isinstance(entry.get("path"), str) and bool(entry["path"]), "Unsafe package path")
        if backend == "tensorrt" and kind == "model":
            require(entry.get("artifact_format") in ("trt_plan", "ultralytics_metadata_prefixed_engine"),
                    "ARTIFACT_FORMAT_UNSUPPORTED")
            require(set(entry) == {"path", "sha256", "artifact_format"}, "BACKEND_CONTRACT_INVALID: artifact fields")
            require(valid_sha256(entry.get("sha256")), "BACKEND_CONTRACT_INVALID: artifact SHA256")
        elif backend == "pytorch":
            require("artifact_format" not in entry, "BACKEND_CONTRACT_INVALID: schema1 artifact format is implicit PyTorch")
        relative = Path(entry["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and ":" not in entry["path"]
                and "\\" not in entry["path"], "Unsafe package path")
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and path not in paths, "Escaping or reused package path")
        paths.add(path)
        data = path.read_bytes()
        require(sha256(data) == entry["sha256"],
                "ARTIFACT_HASH_MISMATCH" if backend == "tensorrt" and kind == "model" else f"Hash mismatch: {kind}")
        if kind not in ("model", "self_test"):
            documents[kind] = json.loads(data)
    rows = documents["classes"].get("classes", [])
    require(rows and [row["id"] for row in rows] == list(range(len(rows))), "Classes must have contiguous ordered IDs")
    names = [row["name"] for row in rows]
    require(all(isinstance(name, str) and name.strip() for name in names) and len(set(names)) == len(names), "Invalid class names")
    preprocessing = documents["preprocessing"]
    require(preprocessing.get("input_layout") == "NCHW" and preprocessing.get("source_color") == "BGR"
            and preprocessing.get("model_color") == "RGB" and preprocessing.get("normalization") == "divide_255"
            and preprocessing.get("dtype") in (("float32",) if backend == "pytorch" else ("float32", "float16")) and preprocessing.get("resize") == "letterbox"
            and preprocessing.get("interpolation") == "linear" and preprocessing.get("padding") == 114
            and preprocessing.get("rect") is False and preprocessing.get("crop") is False
            and preprocessing.get("nms_location") == ("ultralytics" if backend == "pytorch" else
                "adapter" if manifest["detector"]["output"] is not None else None)
            and "nms_location" in preprocessing and preprocessing.get("augmentation") is False,
            "Unsupported preprocessing contract")
    size = preprocessing.get("size")
    require(isinstance(size, list) and len(size) == 2, "Input size must be height,width")
    for dimension in size:
        integer(dimension, 32, 2048, "input dimension")
        require(dimension % 32 == 0, "Input dimension must be stride aligned")
    if backend == "tensorrt":
        if manifest["detector"]["output"] is not None:
            validate_output_contract(manifest["detector"]["output"], len(names))
        inputs = manifest["detector"]["input"]
        require(inputs["shape"] == [1, 3, *size] and inputs["dtype"] == preprocessing["dtype"],
                "BACKEND_CONTRACT_INVALID: input/preprocessing mismatch")
    for key in ("confidence", "nms_iou"):
        value = preprocessing.get(key)
        require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 1, f"Invalid {key}")
    validate_recipe(documents["recipe"], names)
    capture = documents["capture"]
    require(capture.get("format") == "MJPG" and capture.get("view") == "top", "Unsupported capture profile")
    for key in ("width", "height", "fps"):
        integer(capture.get(key), 1, 8192 if key != "fps" else 120, key)
    require("device" not in capture, "Station device path must be separate from product package")
    return ProductPackage(root, manifest, documents["classes"], preprocessing, documents["recipe"], capture, sha256(raw))
