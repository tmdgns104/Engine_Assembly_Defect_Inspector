import copy
import json
import tempfile
import unittest
from pathlib import Path

from src.recipe.package import PackageError, canonical, load_package, sha256
from src.decision.slots import assess, assign_slots, normalized_box, pixel_box


def fixture_documents():
    recipe = {"schema_version": 1, "recipe_id": "assembly", "version": "1", "coordinate_space": "normalized_image",
              "alignment_mode": "fixed_profile", "visibility_mode": "human_per_request", "rule": "presence_count",
              "reference_class": None, "presence_confidence": .8, "reference_confidence": .8,
              "slot_overlap": .65, "reference_iou": .65, "observation_count": 3,
              "required_views": ["top"], "orientation_verified": False,
              "slots": [{"id": "first", "allowed_classes": ["bolt"], "display": "첫 자리", "expected_count": 2, "region": [0, 0, .45, 1]},
                        {"id": "second", "allowed_classes": ["bolt"], "display": "다음 자리", "expected_count": 1, "region": [.55, 0, 1, 1]}]}
    pre = {"input_layout": "NCHW", "source_color": "BGR", "model_color": "RGB", "normalization": "divide_255",
           "dtype": "float32", "resize": "letterbox", "interpolation": "linear", "padding": 114,
           "rect": False, "crop": False, "nms_location": "ultralytics", "augmentation": False,
           "size": [768, 960], "confidence": .25, "nms_iou": .7}
    return {"classes": {"classes": [{"id": i, "name": name} for i, name in enumerate(["base", "bolt", "cover", "washer"])]},
            "preprocessing": pre, "recipe": recipe, "capture": {"width": 1280, "height": 720, "fps": 30, "format": "MJPG", "view": "top"}}


def write_package(root, documents=None):
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "enabled": True, "release_id": "fixture-v1", "product_id": "fixture", "model_version": "mock",
                "detector": {"backend": "pytorch", "task": "detect", "output": "ultralytics_xyxy"}, "files": {}}
    for key, value in {"model": b"fixture-not-a-real-model", **(documents or fixture_documents())}.items():
        data = value if isinstance(value, bytes) else canonical(value).encode()
        filename = "best.pt" if key == "model" else key + ".json"
        (root / filename).write_bytes(data)
        manifest["files"][key] = {"path": filename, "sha256": sha256(data)}
    (root / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return manifest


def detection(box, name="bolt", confidence=.95):
    return {"class_name": name, "confidence": confidence, "bounding_box": dict(zip(("x1", "y1", "x2", "y2"), box))}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "product"

    def test_valid_non_earbud_package_and_snapshot_is_detached(self):
        write_package(self.root)
        package = load_package(self.root)
        self.assertEqual(package.preprocessing["size"], [768, 960])
        self.assertEqual(len(package.names), 4)
        snapshot = package.snapshot()
        snapshot["recipe"]["slots"].clear()
        self.assertEqual(len(package.recipe["slots"]), 2)

    def test_tampered_hash_and_path_escape_rejected(self):
        manifest = write_package(self.root)
        (self.root / "best.pt").write_bytes(b"tampered")
        with self.assertRaises(PackageError): load_package(self.root)
        manifest["files"]["model"]["path"] = "../best.pt"
        (self.root / "manifest.json").write_text(canonical(manifest))
        with self.assertRaises(PackageError): load_package(self.root)

    def test_invalid_recipes_and_inputs_rejected(self):
        for case in ("empty", "duplicate", "unknown", "bad_box", "zero_count", "unsupported", "dtype", "size", "device"):
            with self.subTest(case=case):
                docs = fixture_documents()
                if case == "empty": docs["recipe"]["slots"] = []
                if case == "duplicate": docs["recipe"]["slots"][1]["id"] = "first"
                if case == "unknown": docs["recipe"]["slots"][0]["allowed_classes"] = ["unknown"]
                if case == "bad_box": docs["recipe"]["slots"][0]["region"] = [0, 0, 2, 1]
                if case == "zero_count": docs["recipe"]["slots"][0]["expected_count"] = 0
                if case == "unsupported": docs["recipe"]["rule"] = "color"
                if case == "dtype": docs["preprocessing"]["dtype"] = "float16"
                if case == "size": docs["preprocessing"]["size"] = [641, 640]
                if case == "device": docs["capture"]["device"] = "/dev/video0"
                write_package(self.root, docs)
                with self.assertRaises(PackageError): load_package(self.root)


class SlotTests(unittest.TestCase):
    def setUp(self):
        self.recipe = fixture_documents()["recipe"]
        self.detections = [detection([5, 10, 15, 20]), detection([25, 10, 35, 20]), detection([65, 10, 75, 20])]
        self.view = {"alignment_confirmed": True, "product_identity": "human_confirmed", "visible_slots": {"first": True, "second": True}, "basis": "fixture"}

    def observations(self, detections):
        return [{"frame_id": str(i), "width": 100, "height": 100, "quality": {"valid": True},
                 "freshness": {"source_pts_ns": i}, "detections": detections} for i in range(3)]

    def test_same_class_multiple_slots_and_expected_count_two(self):
        assignment, uncertain = assign_slots(self.detections, self.recipe, 100, 100)
        self.assertEqual(assignment, {"first": [0, 1], "second": [2]})
        self.assertFalse(uncertain)
        self.assertEqual(assess(self.observations(self.detections), self.recipe, self.view)["decision"], "PASS")

    def test_no_double_assignment_for_overlapping_slots(self):
        self.recipe["slots"][1]["region"] = [0, 0, .45, 1]
        assignment, uncertain = assign_slots(self.detections[:1], self.recipe, 100, 100)
        self.assertEqual(sum(map(len, assignment.values())), 0)
        self.assertEqual(uncertain, {"first", "second"})

    def test_fail_preserves_unobserved_slots(self):
        self.view["visible_slots"]["second"] = False
        result = assess(self.observations([]), self.recipe, self.view)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["unassessed"], ["second"])
        self.assertEqual(result["defects"][0]["slot"], "first")

    def test_no_automatic_visibility_or_identity(self):
        for key in ("alignment_confirmed", "product_identity", "visible_slots"):
            view = dict(self.view)
            view.pop(key)
            self.assertEqual(assess(self.observations(self.detections), self.recipe, view)["decision"], "REVIEW")

    def test_empty_recipe_never_passes(self):
        recipe = dict(self.recipe, slots=[])
        self.assertEqual(assess(self.observations([]), recipe, self.view)["decision"], "ERROR")

    def test_coordinate_roundtrip(self):
        source = [.1, .2, .7, .8]
        self.assertEqual(normalized_box(pixel_box(source, 1280, 720), 1280, 720), source)


if __name__ == "__main__": unittest.main()
