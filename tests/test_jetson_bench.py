"""BENCH decision, request admission and persistence checks; no hardware substitute."""

import copy
import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from apps.edge_service.bench import BenchWorker, BusyError, atomic_write
from src.decision.bench import calibrate, decide
from src.contracts import BoundingBox, CameraFrame, Detection, DetectionResult


ROOT = Path(__file__).resolve().parents[1]


def detection(name, box, score=.95):
    return {"class_name": name, "confidence": score,
            "bounding_box": dict(zip(("x1", "y1", "x2", "y2"), box))}


class BenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".cache").mkdir(exist_ok=True)

    def setUp(self):
        self.config = json.loads((ROOT / "config/earbud_bench.json").read_text(encoding="utf-8"))
        self.objects = [detection("case", [100, 100, 400, 400]),
                        detection("earbud_left", [140, 220, 200, 310]),
                        detection("earbud_right", [280, 220, 340, 310])]
        self.calibration = dict(calibrate(self.objects, self.config), confirmed=True)

    def observations(self, objects=None):
        return [{"frame_id": f"frame-{i}", "freshness": {"source_pts_ns": 100 + i},
                 "quality": {"valid": True}, "detections": copy.deepcopy(objects if objects is not None else self.objects)}
                for i in range(3)]

    def test_four_states(self):
        for removed, status, missing in [(set(), "PASS", 0), ({"earbud_left"}, "FAIL", 1),
                                         ({"earbud_right"}, "FAIL", 1), ({"earbud_left", "earbud_right"}, "FAIL", 2)]:
            obs = self.observations([x for x in self.objects if x["class_name"] not in removed])
            result = decide(obs, self.calibration, self.config, True)
            self.assertEqual(result["status"], status)
            self.assertEqual(list(result["slot_states"].values()).count("ABSENT_CONFIRMED"), missing)

    def test_visibility_and_calibration_are_required(self):
        self.assertEqual(decide(self.observations(), self.calibration, self.config, False)["status"], "REVIEW")
        self.assertEqual(decide(self.observations(), None, self.config, True)["status"], "REVIEW")

    def test_missing_reference_or_shifted_reference_never_passes(self):
        for objects in [self.objects[1:], [detection("case", [500, 100, 800, 400])] + self.objects[1:]]:
            self.assertEqual(decide(self.observations(objects), self.calibration, self.config, True)["status"], "REVIEW")

    def test_outside_slot_or_low_confidence_is_review(self):
        for bad in [detection("earbud_left", [420, 220, 480, 310]), detection("earbud_left", [140, 220, 200, 310], .5)]:
            objects = [self.objects[0], bad, self.objects[2]]
            self.assertEqual(decide(self.observations(objects), self.calibration, self.config, True)["status"], "REVIEW")

    def test_transient_miss_is_not_confirmed_absence(self):
        obs = self.observations()
        obs[1]["detections"] = [self.objects[0], self.objects[2]]
        self.assertEqual(decide(obs, self.calibration, self.config, True)["status"], "REVIEW")

    def test_duplicate_id_or_timestamp_is_error(self):
        for key in ("id", "pts"):
            obs = self.observations()
            if key == "id":
                obs[1]["frame_id"] = obs[0]["frame_id"]
            else:
                obs[1]["freshness"] = obs[0]["freshness"]
            self.assertEqual(decide(obs, self.calibration, self.config, True)["status"], "ERROR")

    def test_quality_failure_is_review(self):
        obs = self.observations()
        obs[0]["quality"]["valid"] = False
        self.assertEqual(decide(obs, self.calibration, self.config, True)["status"], "REVIEW")

    def test_other_product_names_and_three_slots(self):
        config = copy.deepcopy(self.config)
        config["reference_class"] = "fixture"
        config["slots"] = [{"id": str(i), "class_name": f"part{i}", "display": f"part{i}", "expected_count": 1} for i in range(3)]
        objects = [detection("fixture", [0, 0, 500, 500])] + [detection(f"part{i}", [20+i*100, 40, 70+i*100, 100]) for i in range(3)]
        calibration = dict(calibrate(objects, config), confirmed=True)
        self.assertEqual(decide(self.observations(objects), calibration, config, True)["status"], "PASS")

    def test_write_never_overwrites_and_failure_does_not_publish(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            path = Path(directory) / "result.json"
            atomic_write(path, b"original")
            with self.assertRaises(FileExistsError):
                atomic_write(path, b"changed")
            self.assertEqual(path.read_bytes(), b"original")
            worker = BenchWorker(self.config, b"config", "unused", Path(directory))
            worker.state, worker.last_frame_time = "READY", time.monotonic()
            with patch("apps.edge_service.bench.atomic_write", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    worker.submit("calibrate", True)
            self.assertEqual(worker.state, "ERROR")
            self.assertIsNone(worker.job)
            self.assertIsNone(worker.last_result)

    def test_busy_rejects_duplicate_and_status_remains_responsive(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            worker = BenchWorker(self.config, b"config", "unused", Path(directory))
            worker.state, worker.last_frame_time = "READY", time.monotonic()
            worker.submit("calibrate", True)
            with self.assertRaises(BusyError):
                worker.submit("calibrate", True)
            self.assertEqual(worker.snapshot()["state"], "BUSY")
            worker.job["deadline"] = time.monotonic() - 1
            self.assertEqual(worker.snapshot()["state"], "ERROR")
            with self.assertRaises(BusyError):
                worker.submit("calibrate", True)

    def test_request_discards_buffered_frame_and_saves_only_new_observations(self):
        import numpy as np
        config = dict(self.config, frame_spacing_seconds=0, min_blur_variance=0)
        image = np.full((500, 500, 3), 120, dtype=np.uint8)
        detector_objects = tuple(Detection(i, obj["class_name"], obj["confidence"],
                                          BoundingBox(**obj["bounding_box"])) for i, obj in enumerate(self.objects))
        class Camera:
            sequence = 0
            def capture(camera):
                camera.sequence += 1
                now = time.monotonic()
                source = now - 10 if camera.sequence == 1 else now
                camera.frame_info = {"source_pts_ns": camera.sequence, "age_seconds": 0,
                                     "estimated_source_monotonic": source}
                return CameraFrame(image, str(camera.sequence), datetime.now(timezone.utc), 500, 500, "live")
        class Detector:
            model_hash, input_shape = "test", [1, 3, 640, 640]
            def detect(detector, frame):
                return DetectionResult(frame.frame_id, detector_objects, "test", 1.0)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            worker = BenchWorker(config, b"config", "unused", Path(directory))
            worker.state, worker.last_frame_time = "READY", time.monotonic()
            request_id = worker.submit("calibrate", True)
            worker._execute(worker.job, Camera(), Detector())
            result = worker.last_result
            self.assertEqual([x["frame_id"] for x in result["observations"]], ["2", "3", "4"])
            self.assertEqual(len(result["assets"]), 3)
            self.assertTrue(result["storage_success"])
            self.assertIsNone(worker.calibration)
            self.assertEqual(worker.candidate["request_id"], request_id)
            worker.job = None
            worker.state = "READY"
            worker.confirm_calibration(request_id)
            self.assertTrue(worker.calibration["confirmed"])


if __name__ == "__main__":
    unittest.main()
