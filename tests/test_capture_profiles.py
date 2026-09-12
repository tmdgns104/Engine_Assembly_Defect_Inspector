"""Product-independent collection regression tests; fixtures are never real captures."""

import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from training.scripts import capture_proxy as capture
from training.scripts.verify_proxy_captures import verify_session


PROFILE_PATH = Path("training/datasets/proxy/earbud_case_v0/profile.json")


class CaptureProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = capture.load_profile(PROFILE_PATH)
        self.png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQIHWOoqKgAAALUAWlMblpQAAAAAElFTkSuQmCC")

    def record(self, scenario="NORMAL", **overrides):
        args = dict(session_id="P001", episode_id=f"P001_{scenario}_01", scenario=scenario,
                    captured_at=datetime(2026, 9, 12, tzinfo=timezone.utc), width=1, height=1,
                    device="synthetic-host", camera_source="synthetic.png", source_kind="sample",
                    image_png=self.png, profile=self.profile)
        args.update(overrides)
        return capture.make_record(**args)

    def test_load_profile_without_optional_packages(self):
        result = subprocess.run([sys.executable, "-S", "-c",
                                 "from pathlib import Path; from training.scripts.capture_proxy import load_profile; "
                                 f"print(load_profile(Path({str(PROFILE_PATH)!r}))['product_id'])"],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "earbud_case_v0")

    def test_four_scenarios_preserve_case_and_actual_lr(self):
        expected = {"NORMAL": [], "MISSING_LEFT": ["earbud_left"],
                    "MISSING_RIGHT": ["earbud_right"], "MISSING_BOTH": ["earbud_left", "earbud_right"]}
        self.assertEqual(set(self.profile["scenarios"]), set(expected))
        for name, removed in expected.items():
            with self.subTest(scenario=name):
                record = self.record(name)
                self.assertEqual(record["schema_version"], 2)
                self.assertEqual(record["object_configuration"], {
                    "objects_expected": ["earbud_left", "earbud_right", "case"],
                    "objects_removed": removed, "unexpected_object": False})
                capture.save_capture(self.root, record, self.png)
        result = verify_session(self.root, "P001")
        self.assertEqual(result["captures"], 4)
        self.assertEqual(result["scenario_counts"], dict.fromkeys(expected, 1))
        self.assertEqual(result["source_counts"], {"sample": 4})
        self.assertEqual(result["product_id"], "earbud_case_v0")
        self.assertEqual(result["record_semantics"], "capture_intent_not_inspection_result")

    def test_invalid_profiles_rejected(self):
        mutations = [
            ("profile_schema_version", True), ("profile_schema_version", 2),
            ("profile_version", 0), ("profile_version", True),
            ("product_id", "../engine"), ("product_id", None),
            ("objects", []), ("objects", ["case", "case"]), ("objects", ["case", {}]),
            ("objects", ["part/name"]), ("scenarios", []), ("scenarios", {}),
        ]
        invalid = [None, [], {}]
        for key, value in mutations:
            profile = copy.deepcopy(self.profile)
            profile[key] = value
            invalid.append(profile)
        for removed, unexpected in [(["undefined_part"], False), (["case", "case"], False),
                                     ([{}], False), ("case", False), ([], 1)]:
            profile = copy.deepcopy(self.profile)
            profile["scenarios"]["MISSING_LEFT"] = {"objects_removed": removed, "unexpected_object": unexpected}
            invalid.append(profile)
        for key in ("CAMERA_SMOKE", "../BAD", "lowercase"):
            profile = copy.deepcopy(self.profile)
            profile["scenarios"][key] = {"objects_removed": [], "unexpected_object": False}
            invalid.append(profile)
        for settings in ({"objects_removed": ["case"], "unexpected_object": False},
                         {"objects_removed": [], "unexpected_object": True}, {}, None):
            profile = copy.deepcopy(self.profile)
            profile["scenarios"]["NORMAL"] = settings
            invalid.append(profile)
        profile = copy.deepcopy(self.profile)
        profile["bounding_boxes"] = []
        invalid.append(profile)
        for profile in invalid:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                capture.validate_profile(profile)

    def test_loader_rejects_malformed_and_duplicate_json(self):
        path = self.root / "invalid.json"
        for raw in ('{"broken":', '{"objects":[],"objects":["case"]}', 'null'):
            path.write_text(raw, encoding="utf-8")
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                capture.load_profile(path)

    def test_undefined_scenario_and_object_claims_rejected(self):
        for scenario in ("MISSING_A", "NOT_DEFINED", None, []):
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                self.record(scenario)
        for removed in (["case"], ["unknown"], []):
            record = self.record("MISSING_BOTH")
            record["object_configuration"]["objects_removed"] = removed
            with self.assertRaises(ValueError):
                capture.validate_record(record)

    def test_invalid_cli_intent_does_not_open_camera_or_save(self):
        for profile_path, scenario in ((PROFILE_PATH, "MISSING_A"), (self.root / "missing.json", "NORMAL")):
            with self.subTest(scenario=scenario), patch.object(capture, "read_source") as source:
                code = capture.main(["--profile", str(profile_path), "--camera", "/dev/video-test",
                                     "--output-root", str(self.root / "out"), "--session-id", "P001",
                                     "--episode-id", "P001_E1", "--scenario", scenario])
                self.assertEqual(code, 1)
                source.assert_not_called()
                self.assertFalse((self.root / "out").exists())

    def test_smoke_and_legacy_records_remain_distinct(self):
        for profile, version in ((None, 1), (self.profile, 2)):
            root = self.root / str(version)
            record = self.record("CAMERA_SMOKE", profile=profile)
            self.assertEqual(record["schema_version"], version)
            self.assertEqual(record["object_configuration"], {
                "objects_expected": [], "objects_removed": [], "unexpected_object": False})
            capture.save_capture(root, record, self.png)
            self.assertEqual(verify_session(root, "P001")["scenario_counts"], {"CAMERA_SMOKE": 1})
        legacy = self.record("MISSING_A", profile=None)
        self.assertEqual(legacy["object_configuration"]["objects_removed"], ["OBJ_A"])
        self.assertNotIn("profile_snapshot", legacy)

    def test_past_record_survives_profile_mutation_and_file_removal(self):
        path = self.root / "profile.json"
        path.write_text(json.dumps(self.profile), encoding="utf-8")
        loaded = capture.load_profile(path)
        record = self.record("MISSING_LEFT", profile=loaded)
        digest = record["profile_sha256"]
        capture.save_capture(self.root, record, self.png)
        loaded["scenarios"]["MISSING_LEFT"]["objects_removed"] = ["earbud_right"]
        loaded["profile_version"] = 2
        path.write_text(json.dumps(loaded), encoding="utf-8")
        self.assertNotEqual(capture.profile_digest(capture.load_profile(path)), digest)
        path.unlink()  # Disposable test profile, never the repository profile.
        with patch.object(capture, "load_profile", side_effect=AssertionError("must use snapshot")):
            result = verify_session(self.root, "P001")
        self.assertEqual(result["profile_sha256"], digest)
        old = capture.read_manifest(self.root / "P001/manifest.jsonl")[0]
        self.assertEqual(old["profile_snapshot"]["scenarios"]["MISSING_LEFT"]["objects_removed"], ["earbud_left"])
        self.assertEqual(record, old)

    def test_profile_hash_is_canonical_and_tampering_rejected(self):
        reversed_keys = dict(reversed(list(self.profile.items())))
        self.assertEqual(capture.profile_digest(reversed_keys), capture.profile_digest(self.profile))
        record = self.record()
        snapshot = record["profile_snapshot"]
        raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(record["profile_sha256"], hashlib.sha256(raw).hexdigest())
        for key, value in (("profile_sha256", "0" * 64), ("profile_snapshot", {}), ("decision", "PASS")):
            changed = copy.deepcopy(record)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                capture.validate_record(changed)
        snapshot["product_id"] = "changed_product"
        with self.assertRaisesRegex(ValueError, "profile_sha256"):
            capture.validate_record(record)

    def test_manifest_verifier_rejects_changed_profile_snapshot(self):
        record = self.record("MISSING_LEFT")
        capture.save_capture(self.root, record, self.png)
        record["profile_snapshot"]["scenarios"]["MISSING_LEFT"]["objects_removed"] = ["earbud_right"]
        manifest = self.root / "P001/manifest.jsonl"
        manifest.write_text(json.dumps(record) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(capture.CaptureError, "profile_sha256"):
            verify_session(self.root, "P001")

    def test_published_schema_inventory_covers_both_record_formats(self):
        # Contract drift check; cross-field/hash rules are tested through the executable validator.
        folder = PROFILE_PATH.parent.parent
        schema = json.loads((folder / "capture-schema.json").read_text(encoding="utf-8"))
        profile_schema = json.loads((folder / "profile-schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(profile_schema["required"]), set(self.profile))
        for profile, version in ((None, 1), (self.profile, 2)):
            record = self.record(profile=profile)
            definition = schema["$defs"][f"v{version}"]
            self.assertEqual(set(definition["required"]), set(record))
            self.assertEqual(set(definition["properties"]), set(record))
            self.assertFalse(definition["additionalProperties"])
            self.assertEqual(definition["properties"]["schema_version"]["const"], version)
        reference = schema["$defs"]["v2"]["properties"]["profile_snapshot"]["$ref"]
        self.assertEqual(json.loads((folder / reference).read_text(encoding="utf-8")), profile_schema)

    def test_profile_change_requires_new_session_and_preserves_old_files(self):
        first = self.record()
        capture.save_capture(self.root, first, self.png)
        manifest = self.root / "P001/manifest.jsonl"
        before = manifest.read_bytes()
        modified = copy.deepcopy(self.profile)
        modified["profile_version"] = 2
        for profile in (modified, None):
            second = self.record(episode_id="P001_E2", profile=profile)
            with self.assertRaisesRegex(capture.CaptureError, "Session profile"):
                capture.save_capture(self.root, second, self.png)
            self.assertEqual(manifest.read_bytes(), before)
        second = self.record(session_id="P002", episode_id="P002_E1", profile=modified)
        capture.save_capture(self.root, second, self.png)
        self.assertEqual(verify_session(self.root, "P002")["profile_version"], 2)
        manifest.write_text(before.decode("utf-8") + json.dumps(self.record(profile=modified)) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(capture.CaptureError, "Session profile"):
            capture.read_manifest(manifest)

    def test_virtual_four_part_product_uses_same_collection_path(self):
        # Test-only fictional product. No engine parts or real geometry/thresholds.
        profile = {"profile_schema_version": 1, "profile_version": 3, "product_id": "fixture_test_only",
                   "objects": ["plate", "pin", "ring", "cover"], "scenarios": {
                       "NORMAL": {"objects_removed": [], "unexpected_object": False},
                       "REMOVE_PAIR": {"objects_removed": ["pin", "ring"], "unexpected_object": False},
                       "ADD_SPARE": {"objects_removed": [], "unexpected_object": True}}}
        path = self.root / "fictional.json"
        path.write_text(json.dumps(profile), encoding="utf-8")
        loaded = capture.load_profile(path)
        for scenario in profile["scenarios"]:
            record = self.record(scenario, profile=loaded)
            self.assertEqual(record["object_configuration"]["objects_expected"], profile["objects"])
            self.assertEqual(record["object_configuration"]["objects_removed"], profile["scenarios"][scenario]["objects_removed"])
            capture.save_capture(self.root, record, self.png)
        self.assertEqual(verify_session(self.root, "P001")["product_id"], "fixture_test_only")

    def test_profile_sample_cli_and_verifier_work_without_original_profile(self):
        source = self.root / "sample.png"
        source.write_bytes(self.png)
        profile_path = self.root / "selected.json"
        profile_path.write_text(json.dumps(self.profile), encoding="utf-8")
        command = [sys.executable, "training/scripts/capture_proxy.py", "--profile", str(profile_path),
                   "--sample", str(source), "--output-root", str(self.root / "out"),
                   "--session-id", "P001", "--episode-id", "P001_MISSING_BOTH_01", "--scenario", "MISSING_BOTH"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["metadata"]["source_kind"], "sample")
        profile_path.unlink()
        verified = subprocess.run([sys.executable, "training/scripts/verify_proxy_captures.py",
                                   "--output-root", str(self.root / "out"), "--session-id", "P001"],
                                  capture_output=True, text=True, timeout=15)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["scenario_counts"], {"MISSING_BOTH": 1})

    def test_v2_duplicate_lock_and_episode_guards_preserve_files(self):
        record = self.record()
        image = capture.save_capture(self.root, record, self.png)
        manifest = self.root / "P001/manifest.jsonl"
        before = manifest.read_bytes()
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(self.root, record, self.png)
        with self.assertRaisesRegex(capture.CaptureError, "Episode"):
            capture.save_capture(self.root, self.record("MISSING_LEFT", episode_id=record["episode_id"]), self.png)
        lock = self.root / "P001/.capture.lock"
        lock.write_text("another owner", encoding="utf-8")
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(self.root, self.record(), self.png)
        self.assertEqual(lock.read_text(), "another owner")
        self.assertEqual(image.read_bytes(), self.png)
        self.assertEqual(manifest.read_bytes(), before)

    def test_v2_verification_rejects_hash_size_and_dimension_errors(self):
        for problem in ("hash", "size", "dimensions"):
            with self.subTest(problem=problem):
                root = self.root / problem
                record = self.record(width=2 if problem == "dimensions" else 1)
                image = capture.save_capture(root, record, self.png)
                if problem == "hash":
                    image.write_bytes(self.png[:-1] + b"X")
                elif problem == "size":
                    image.write_bytes(self.png + b"X")
                with self.assertRaises(capture.CaptureError):
                    verify_session(root, "P001")


if __name__ == "__main__":
    unittest.main()
