"""Metadata/storage tests and sample CLI integration; never opens real hardware."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from training.scripts import capture_proxy as capture
from training.scripts.verify_proxy_captures import verify_session


class ProxyCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # A real 1x1 PNG fixture. Core storage tests do not need OpenCV.
        self.png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQIHWOoqKgAAALUAWlMblpQAAAAAElFTkSuQmCC")
        self.time = datetime(2026, 9, 11, 9, tzinfo=timezone(timedelta(hours=9)))

    def record(self, **overrides):
        args = dict(session_id="S001", episode_id="S001_NORMAL_01", scenario="NORMAL",
                    captured_at=self.time, width=1, height=1, device="test-host",
                    camera_source="test-source", source_kind="sample", image_png=self.png)
        args.update(overrides)
        return capture.make_record(**args)

    def test_portable_session_and_episode_ids(self):
        capture.validate_ids("S001", "S001_NORMAL_01")
        for session, episode in [("../S1", "S1_NORMAL_01"), ("CON", "CON_NORMAL_01"),
                                 ("s1", "s1_E1"), ("S001", "S002_NORMAL_01"),
                                 ("S001", "S001_../bad"), ("", "_E1")]:
            with self.subTest(session=session, episode=episode), self.assertRaises(ValueError):
                capture.validate_ids(session, episode)

    def test_capture_ids_unique_even_for_same_timestamp(self):
        first, second = self.record(), self.record()
        self.assertNotEqual(first["capture_id"], second["capture_id"])
        self.assertTrue(first["capture_id"].startswith("S001_NORMAL_01_20260911T000000000000Z_"))
        self.assertTrue(first["image_path"].endswith(first["capture_id"] + ".png"))

    def test_utc_timestamp_and_naive_rejection(self):
        self.assertEqual(self.record()["captured_at"], "2026-09-11T00:00:00+00:00")
        with self.assertRaises(ValueError):
            self.record(captured_at=datetime(2026, 9, 11))
        record = self.record()
        record["captured_at"] = "2026-09-11T09:00:00+09:00"
        with self.assertRaises(ValueError):
            capture.validate_record(record)

    def test_scenario_configuration_and_smoke_separation(self):
        for scenario in capture.SCENARIOS:
            record = self.record(scenario=scenario)
            capture.validate_record(record)
            config = record["object_configuration"]
            self.assertEqual(config["objects_expected"], [] if scenario == "CAMERA_SMOKE" else capture.OBJECTS)
            self.assertEqual(config["objects_removed"], ["OBJ_" + scenario[-1]] if scenario.startswith("MISSING_") else [])
            self.assertEqual(config["unexpected_object"], scenario == "EXTRA_OBJECT")
        with self.assertRaises(ValueError):
            self.record(scenario="ENGINE_PART")

    def test_metadata_json_roundtrip_and_no_labels(self):
        record = self.record(notes="separate physical placement")
        self.assertEqual(json.loads(json.dumps(record, allow_nan=False)), record)
        record["bounding_boxes"] = []
        with self.assertRaises(ValueError):
            capture.validate_record(record)

    def test_invalid_metadata_is_rejected(self):
        invalid_fields = {"width": [0, True, 1.2], "height": [-1], "device": [" "],
                          "camera_source": [None], "notes": [{}], "source_kind": ["unknown"],
                          "image_sha256": ["bad"], "image_bytes": [0], "schema_version": [True, 2],
                          "image_path": ["../../outside.png"], "capture_id": ["../bad"]}
        for key, values in invalid_fields.items():
            for value in values:
                record = self.record()
                record[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    capture.validate_record(record)
        record = self.record(scenario="MISSING_A")
        record["object_configuration"]["objects_removed"] = []
        with self.assertRaises(ValueError):
            capture.validate_record(record)

    def test_output_created_and_two_manifest_records_appended(self):
        records = [self.record(), self.record()]
        for record in records:
            image_path = capture.save_capture(self.root, record, self.png)
            self.assertEqual(image_path.read_bytes(), self.png)
        loaded = capture.read_manifest(self.root / "S001/manifest.jsonl")
        self.assertEqual(loaded, records)
        self.assertFalse((self.root / "S001/.capture.lock").exists())

    def test_duplicate_preserves_image_and_manifest(self):
        record = self.record()
        image = capture.save_capture(self.root, record, self.png)
        manifest = self.root / "S001/manifest.jsonl"
        before = manifest.read_bytes()
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(self.root, record, self.png)
        self.assertEqual(image.read_bytes(), self.png)
        self.assertEqual(manifest.read_bytes(), before)

    def test_episode_cannot_silently_change_scenario_or_source(self):
        capture.save_capture(self.root, self.record(), self.png)
        for changes in ({"scenario": "MISSING_A"}, {"source_kind": "camera"},
                        {"camera_source": "another-camera"}, {"width": 2}):
            with self.subTest(changes=changes), self.assertRaises(capture.CaptureError):
                capture.save_capture(self.root, self.record(**changes), self.png)
        new_episode = self.record(episode_id="S001_MISSING_A_01", scenario="MISSING_A")
        capture.save_capture(self.root, new_episode, self.png)

    def test_manifest_reader_rejects_preexisting_episode_inconsistency(self):
        first = self.record()
        second = self.record(scenario="MISSING_A")
        manifest = self.root / "manifest.jsonl"
        manifest.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(capture.CaptureError, "Inconsistent"):
            capture.read_manifest(manifest)

    def test_lock_contention_does_not_remove_existing_lock(self):
        session = self.root / "S001"
        session.mkdir()
        lock = session / ".capture.lock"
        lock.write_text("other owner", encoding="utf-8")
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(self.root, self.record(), self.png)
        self.assertEqual(lock.read_text(), "other owner")

    def test_orphan_or_truncated_manifest_stops_next_writer(self):
        orphan = self.root / "S001/S001_NORMAL_01/images/orphan.png"
        orphan.parent.mkdir(parents=True)
        orphan.write_bytes(self.png)
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(self.root, self.record(), self.png)
        self.assertEqual(orphan.read_bytes(), self.png)
        other_root = self.root / "truncated"
        (other_root / "S001").mkdir(parents=True)
        manifest = other_root / "S001/manifest.jsonl"
        manifest.write_text('{"partial":', encoding="utf-8")
        with self.assertRaises(capture.CaptureError):
            capture.save_capture(other_root, self.record(), self.png)
        self.assertEqual(manifest.read_text(), '{"partial":')

    def test_manifest_failure_is_not_reported_as_success_and_preserves_recovery(self):
        record = self.record()
        with patch.object(capture, "append_manifest", side_effect=OSError("simulated disk full")):
            with self.assertRaisesRegex(capture.CaptureError, "Storage failed"):
                capture.save_capture(self.root, record, self.png)
        self.assertEqual((self.root / record["image_path"]).read_bytes(), self.png)
        self.assertFalse((self.root / "S001/.capture.lock").exists())
        with self.assertRaisesRegex(capture.CaptureError, "Orphan"):
            capture.save_capture(self.root, self.record(), self.png)

    def test_missing_recorded_image_blocks_append(self):
        record = self.record()
        path = capture.save_capture(self.root, record, self.png)
        path.unlink()  # Only this test's disposable fixture.
        with self.assertRaisesRegex(capture.CaptureError, "mismatch"):
            capture.save_capture(self.root, self.record(), self.png)

    def test_payload_hash_mismatch_rejected_before_writes(self):
        record = self.record()
        with self.assertRaises(ValueError):
            capture.save_capture(self.root, record, self.png + b"changed")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_sample_cli_writes_decodable_png_without_camera(self):
        import cv2
        import numpy as np

        sample = self.root / "sample.png"
        self.assertTrue(cv2.imwrite(str(sample), np.full((12, 16, 3), 120, dtype=np.uint8)))
        output = self.root / "out"
        command = [sys.executable, "training/scripts/capture_proxy.py", "--sample", str(sample),
                   "--output-root", str(output), "--session-id", "SAMPLE01",
                   "--episode-id", "SAMPLE01_NORMAL_01", "--scenario", "NORMAL"]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        record = json.loads(completed.stdout)["metadata"]
        image_path = output / record["image_path"]
        self.assertEqual(cv2.imread(str(image_path)).shape[:2], (12, 16))
        self.assertEqual(record["source_kind"], "sample")
        self.assertEqual(record["image_sha256"], hashlib.sha256(image_path.read_bytes()).hexdigest())
        self.assertEqual(len(capture.read_manifest(output / "SAMPLE01/manifest.jsonl")), 1)

    def test_bad_sample_returns_clear_nonzero_error(self):
        completed = subprocess.run([sys.executable, "training/scripts/capture_proxy.py",
                                   "--sample", str(self.root / "missing.png"),
                                   "--output-root", str(self.root / "out"), "--session-id", "S1",
                                   "--episode-id", "S1_E1", "--scenario", "NORMAL"],
                                  capture_output=True, text=True, timeout=15)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("CAPTURE_ERROR", completed.stderr)
        self.assertFalse((self.root / "out").exists())

    def test_verifier_reloads_all_images_and_detects_corruption(self):
        record = self.record()
        path = capture.save_capture(self.root, record, self.png)
        verified = verify_session(self.root, "S001")
        self.assertEqual(verified["captures"], 1)
        self.assertEqual(verified["images"][0]["width"], 1)
        path.write_bytes(path.read_bytes()[:-1] + b"X")
        with self.assertRaisesRegex(capture.CaptureError, "hash mismatch"):
            verify_session(self.root, "S001")

    def test_verifier_rejects_undecodable_bytes_even_with_matching_hash(self):
        bad_png = b"\x89PNG\r\n\x1a\nnot a valid PNG"
        record = self.record(image_png=bad_png)
        capture.save_capture(self.root, record, bad_png)
        with self.assertRaisesRegex(capture.CaptureError, "reload"):
            verify_session(self.root, "S001")

    def test_camera_branch_negotiates_format_reads_one_saved_frame_and_releases(self):
        import cv2
        import numpy as np

        camera = MagicMock()
        camera.isOpened.return_value = True
        camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        camera.get.side_effect = lambda key: cv2.VideoWriter_fourcc(*"YUYV") if key == cv2.CAP_PROP_FOURCC else 30
        camera.getBackendName.return_value = "V4L2"
        args = SimpleNamespace(sample=None, camera="/dev/video-test", fourcc="YUYV", width=640, height=480, fps=30)
        with patch.object(cv2, "VideoCapture", return_value=camera) as factory:
            frame, timestamp, kind, source = capture.read_source(args)
        factory.assert_called_once_with("/dev/video-test", cv2.CAP_V4L2)
        self.assertEqual(camera.read.call_count, 5)
        self.assertEqual(frame.shape[:2], (480, 640))
        self.assertEqual(timestamp.utcoffset(), timedelta(0))
        self.assertEqual((kind, source), ("camera", "/dev/video-test"))
        camera.release.assert_called_once()

    def test_camera_open_or_read_failure_releases_without_output(self):
        import cv2

        args = SimpleNamespace(sample=None, camera="/dev/video-test", fourcc="YUYV", width=640, height=480, fps=30)
        for opened in (False, True):
            camera = MagicMock()
            camera.isOpened.return_value = opened
            camera.read.return_value = (False, None)
            with self.subTest(opened=opened), patch.object(cv2, "VideoCapture", return_value=camera):
                with self.assertRaises(capture.CaptureError):
                    capture.read_source(args)
            camera.release.assert_called_once()


if __name__ == "__main__":
    unittest.main()
