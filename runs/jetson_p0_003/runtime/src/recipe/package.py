"""Read-only product package verification. Activation and GPU loading belong to Service/Worker."""

import hashlib
import json
import math
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
    require(recipe.get("alignment_mode") in ("human_fixed_reference", "fixed_profile"), "Unsupported alignment mode")
    require(recipe.get("visibility_mode") == "human_per_request", "Automatic visibility is not verified")
    require(recipe.get("rule") == "presence_count", "Unsupported rule")
    slots = recipe.get("slots")
    require(isinstance(slots, list) and 0 < len(slots) <= 64, "Empty or excessive required slots")
    identifiers = set()
    for slot in slots:
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
    def model_path(self):
        return self.root / self.manifest["files"]["model"]["path"]

    @property
    def names(self):
        return [item["name"] for item in self.classes["classes"]]

    def snapshot(self):
        # Return a detached JSON value so no caller can mutate an in-flight package.
        return json.loads(canonical({"manifest": self.manifest, "classes": self.classes,
                                    "preprocessing": self.preprocessing, "recipe": self.recipe,
                                    "capture": self.capture, "manifest_sha256": self.manifest_hash}))


def load_package(directory):
    root = Path(directory).resolve()
    raw = (root / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    require(manifest.get("schema_version") == 1, "Unsupported package schema")
    require(manifest.get("enabled") is True, "Package is not enabled")
    for key in ("release_id", "product_id", "model_version"):
        require(isinstance(manifest.get(key), str) and bool(manifest[key].strip()), f"Missing {key}")
    require(manifest.get("detector") == {"backend": "pytorch", "task": "detect", "output": "ultralytics_xyxy"}, "Unsupported detector contract")
    require(set(manifest.get("files", {})) in ({"model", "classes", "preprocessing", "recipe", "capture"},
                                               {"model", "classes", "preprocessing", "recipe", "capture", "self_test"}), "Incomplete package")
    documents, paths = {}, set()
    for kind, entry in manifest["files"].items():
        relative = Path(entry["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and ":" not in entry["path"]
                and "\\" not in entry["path"], "Unsafe package path")
        path = (root / relative).resolve()
        require(path.is_relative_to(root) and path not in paths, "Escaping or reused package path")
        paths.add(path)
        data = path.read_bytes()
        require(sha256(data) == entry["sha256"], f"Hash mismatch: {kind}")
        if kind not in ("model", "self_test"):
            documents[kind] = json.loads(data)
    rows = documents["classes"].get("classes", [])
    require(rows and [row["id"] for row in rows] == list(range(len(rows))), "Classes must have contiguous ordered IDs")
    names = [row["name"] for row in rows]
    require(all(isinstance(name, str) and name.strip() for name in names) and len(set(names)) == len(names), "Invalid class names")
    preprocessing = documents["preprocessing"]
    require(preprocessing.get("input_layout") == "NCHW" and preprocessing.get("source_color") == "BGR"
            and preprocessing.get("model_color") == "RGB" and preprocessing.get("normalization") == "divide_255"
            and preprocessing.get("dtype") == "float32" and preprocessing.get("resize") == "letterbox"
            and preprocessing.get("interpolation") == "linear" and preprocessing.get("padding") == 114
            and preprocessing.get("rect") is False and preprocessing.get("crop") is False
            and preprocessing.get("nms_location") == "ultralytics" and preprocessing.get("augmentation") is False,
            "Unsupported preprocessing contract")
    size = preprocessing.get("size")
    require(isinstance(size, list) and len(size) == 2, "Input size must be height,width")
    for dimension in size:
        integer(dimension, 32, 2048, "input dimension")
        require(dimension % 32 == 0, "Input dimension must be stride aligned")
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
