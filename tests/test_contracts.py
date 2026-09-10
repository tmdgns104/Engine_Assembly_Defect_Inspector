"""Contract behavior only: no training, real adapters, or device access."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
import subprocess
import sys
import unittest

from src.contracts import (
    BoundingBox, Camera, CameraError, CameraFrame, Detection, DetectionResult,
    Detector, DetectorError, FrameMetadata, InspectionRequest, InspectionResult,
    Reason, ReasonCode, ResultStatus, RunMode,
)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.time = datetime(2026, 9, 10, 12, 30, tzinfo=timezone(timedelta(hours=9)))
        self.box = BoundingBox(1.5, 2, 20, 30)
        self.detection = Detection(0, "object_a", 0.75, self.box)
        self.meta = FrameMetadata("frame-1", self.time, 640, 480, "test")

    def json_dict(self, value):
        return json.loads(json.dumps(value.to_dict(), allow_nan=False))

    def test_result_status_has_exactly_four_string_values(self):
        self.assertEqual([status.value for status in ResultStatus], ["PASS", "FAIL", "REVIEW", "ERROR"])
        self.assertEqual(json.loads(json.dumps(ResultStatus.PASS)), "PASS")
        with self.assertRaises(ValueError):
            ResultStatus("EMERGENCY STOP")

    def test_bounding_box_uses_original_image_xyxy_pixel_edges(self):
        self.assertEqual(self.json_dict(self.box), {"x1": 1.5, "y1": 2, "x2": 20, "y2": 30})
        self.assertEqual(BoundingBox(0, 0, 640, 480).x2, 640)
        self.assertEqual(BoundingBox(2, 3, 2, 3).x1, 2)  # Equality is explicitly allowed.

    def test_bounding_box_rejects_invalid_coordinates(self):
        invalid = [(-1, 0, 2, 2), (3, 0, 2, 2), (0, 3, 2, 2),
                   (0, 0, float("nan"), 2), (0, 0, 2, float("inf")),
                   (True, 0, 2, 2), ("0", 0, 2, 2), (0, 0, 10**400, 2)]
        for coordinates in invalid:
            with self.subTest(coordinates=coordinates), self.assertRaises((TypeError, ValueError)):
                BoundingBox(*coordinates)

    def test_detection_confidence_range_and_identity(self):
        for confidence in (0.0, 1.0):
            self.assertEqual(Detection(0, "object_a", confidence, self.box).confidence, confidence)
        for confidence in (-0.1, 1.1, float("nan"), float("inf"), True, "0.5"):
            with self.subTest(confidence=confidence), self.assertRaises((TypeError, ValueError)):
                Detection(0, "object_a", confidence, self.box)
        for class_id, name in [(-1, "a"), (True, "a"), (0, " ")]:
            with self.subTest(class_id=class_id, name=name), self.assertRaises((TypeError, ValueError)):
                Detection(class_id, name, 0.5, self.box)

    def test_detection_result_serializes_nested_contracts(self):
        result = DetectionResult("frame-1", (self.detection,), "test-model", 2.5)
        data = self.json_dict(result)
        self.assertEqual(data, {
            "frame_id": "frame-1", "detections": [{"class_id": 0, "class_name": "object_a",
                "confidence": 0.75, "bounding_box": {"x1": 1.5, "y1": 2, "x2": 20, "y2": 30}}],
            "model_version": "test-model", "inference_ms": 2.5,
        })

    def test_empty_detection_is_valid_observation_without_inspection_status(self):
        data = self.json_dict(DetectionResult("frame-1"))
        self.assertEqual(data["detections"], [])
        self.assertIsNone(data["inference_ms"])
        self.assertNotIn("status", data)

    def test_detection_result_rejects_invalid_optional_metadata(self):
        for duration in (-1, float("nan"), float("inf"), True, object()):
            with self.subTest(duration=duration), self.assertRaises((TypeError, ValueError)):
                DetectionResult("frame-1", inference_ms=duration)
        with self.assertRaises(ValueError):
            DetectionResult("frame-1", model_version=" ")
        with self.assertRaises(ValueError):
            DetectionResult("")

    def test_timestamps_are_normalized_to_utc_and_iso8601(self):
        request = InspectionRequest("req-1", RunMode.MANUAL, self.time)
        frame = CameraFrame(object(), "frame-1", self.time, 640, 480)
        expected = "2026-09-10T03:30:00+00:00"
        self.assertEqual(self.json_dict(self.meta)["captured_at"], expected)
        self.assertEqual(self.json_dict(request)["requested_at"], expected)
        self.assertEqual(frame.captured_at.tzinfo, timezone.utc)
        self.assertEqual(frame.captured_at, self.time)

    def test_naive_timestamps_are_rejected_at_each_entry_point(self):
        naive = datetime(2026, 9, 10)
        factories = [lambda: FrameMetadata("f", naive, 1, 1),
                     lambda: CameraFrame(object(), "f", naive, 1, 1),
                     lambda: InspectionRequest("r", RunMode.PLC, naive)]
        for factory in factories:
            with self.subTest(factory=factory), self.assertRaises(ValueError):
                factory()
        with self.assertRaises(TypeError):
            FrameMetadata("f", "2026-09-10", 1, 1)

    def test_frame_metadata_does_not_touch_or_serialize_image(self):
        class OpaqueImage:
            def __deepcopy__(self, memo):
                raise AssertionError("Image payload must not be copied by serialization")

        image = OpaqueImage()
        frame = CameraFrame(image, "frame-1", self.time, 640, 480, "test")
        self.assertIs(frame.image, image)
        self.assertEqual(frame.to_metadata(), self.meta)
        self.assertNotIn("image", self.json_dict(frame.to_metadata()))
        with self.assertRaises(TypeError):
            json.dumps(frame)

    def test_frame_rejects_missing_payload_and_invalid_metadata(self):
        with self.assertRaises(ValueError):
            CameraFrame(None, "frame-1", self.time, 640, 480)
        for width, height in [(0, 1), (1, -1), (True, 1), (1.5, 2)]:
            with self.subTest(width=width, height=height), self.assertRaises((TypeError, ValueError)):
                FrameMetadata("f", self.time, width, height)
        with self.assertRaises(ValueError):
            FrameMetadata("f", self.time, 1, 1, " ")

    def test_manual_and_plc_requests_share_one_serialization_contract(self):
        for mode in RunMode:
            request = InspectionRequest("req-1", mode, self.time)
            data = self.json_dict(request)
            self.assertEqual(set(data), {"request_id", "run_mode", "requested_at"})
            self.assertEqual(data["run_mode"], mode.value)
            self.assertEqual(data["request_id"], "req-1")
        with self.assertRaises(TypeError):
            InspectionRequest("req-1", "manual", self.time)
        with self.assertRaises(ValueError):
            InspectionRequest(" ", RunMode.MANUAL, self.time)

    def test_inspection_result_json_and_request_correlation(self):
        request = InspectionRequest("req-1", RunMode.MANUAL, self.time)
        result = InspectionResult(request.request_id, ResultStatus.PASS,
                                  evidence_refs=("evidence/frame-1.png",), frame_meta=self.meta)
        data = self.json_dict(result)
        self.assertEqual(data["request_id"], request.request_id)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["evidence_refs"], ["evidence/frame-1.png"])
        self.assertEqual(data["frame_meta"], self.meta.to_dict())
        self.assertEqual(data["reasons"], [])
        # Capture failure can report a useful error even before any frame exists.
        error = InspectionResult("req-1", ResultStatus.ERROR,
                                 (Reason(ReasonCode.CAMERA_ERROR, "Camera input unavailable"),))
        self.assertIsNone(self.json_dict(error)["frame_meta"])

    def test_result_structural_guards_do_not_implement_decision_engine(self):
        for fields in ({}, {"frame_meta": self.meta}, {"evidence_refs": ("image.png",)}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                InspectionResult("r", ResultStatus.PASS, **fields)
        for status, code in [(ResultStatus.FAIL, ReasonCode.MISSING_REQUIRED_OBJECT),
                             (ResultStatus.REVIEW, ReasonCode.LOW_IMAGE_QUALITY),
                             (ResultStatus.ERROR, ReasonCode.PERSISTENCE_ERROR)]:
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    InspectionResult("r", status)
                result = InspectionResult("r", status, (Reason(code, "Explanation for the operator"),))
                self.assertEqual(self.json_dict(result)["reasons"][0]["code"], code.value)

    def test_reasons_support_common_codes_and_future_domain_strings(self):
        self.assertEqual(self.json_dict(Reason(ReasonCode.DETECTOR_ERROR, "Inference failed")),
                         {"code": "DETECTOR_ERROR", "message": "Inference failed"})
        self.assertEqual(self.json_dict(Reason("CUSTOM_RULE", "Rule explanation"))["code"], "CUSTOM_RULE")
        for code, message in [("", "message"), ("CUSTOM", " "), (object(), "message")]:
            with self.subTest(code=code), self.assertRaises((TypeError, ValueError)):
                Reason(code, message)

    def test_backend_objects_are_rejected_in_serializable_fields(self):
        backend_object = object()
        factories = [lambda: Detection(0, "a", 0.5, backend_object),
                     lambda: DetectionResult("f", (backend_object,)),
                     lambda: DetectionResult("f", [self.detection]),
                     lambda: InspectionResult("r", "PASS"),
                     lambda: InspectionResult("r", ResultStatus.PASS, evidence_refs=(backend_object,), frame_meta=self.meta),
                     lambda: InspectionResult("r", ResultStatus.PASS, evidence_refs=("file",), frame_meta=backend_object),
                     lambda: InspectionResult("r", ResultStatus.REVIEW, (backend_object,))]
        for factory in factories:
            with self.subTest(factory=factory), self.assertRaises(TypeError):
                factory()

    def test_frozen_contracts_and_detached_json_collections(self):
        with self.assertRaises(FrozenInstanceError):
            self.detection.confidence = 2
        result = DetectionResult("f", (self.detection,))
        data = result.to_dict()
        data["detections"][0]["bounding_box"]["x1"] = -100
        data["detections"].clear()
        self.assertEqual(result.detections[0].bounding_box.x1, 1.5)
        with self.assertRaises(TypeError):
            InspectionResult("r", ResultStatus.ERROR, [Reason("X", "message")])

    def test_dummy_camera_detector_pipeline_satisfies_interfaces(self):
        capture_time = self.time

        class DummyCamera:
            def __init__(self):
                self.closed = False

            def capture(self) -> CameraFrame:
                if self.closed:
                    raise CameraError("Camera is closed")
                return CameraFrame(b"dummy pixels", "frame-1", capture_time, 1, 1)

            def status(self) -> bool:
                return not self.closed

            def close(self) -> None:
                self.closed = True

        class DummyDetector:
            def detect(self, frame: CameraFrame) -> DetectionResult:
                return DetectionResult(frame.frame_id)

        camera = DummyCamera()
        detector = DummyDetector()
        self.assertIsInstance(camera, Camera)
        self.assertIsInstance(detector, Detector)
        self.assertNotIsInstance(object(), Camera)
        self.assertNotIsInstance(object(), Detector)
        self.assertTrue(camera.status())
        frame = camera.capture()
        result = detector.detect(frame)
        self.assertIsInstance(result, DetectionResult)
        self.assertEqual(result.frame_id, frame.frame_id)
        camera.close()
        camera.close()
        self.assertFalse(camera.status())
        with self.assertRaises(CameraError):
            camera.capture()
        self.assertTrue(issubclass(DetectorError, RuntimeError))

    def test_contract_import_and_json_work_without_site_packages(self):
        # -S excludes installed ML/camera packages, independently of this test process.
        code = (
            "import json,sys; from src.contracts import DetectionResult; "
            "assert json.loads(json.dumps(DetectionResult('f').to_dict()))['detections']==[]; "
            "assert not any(n.split('.')[0] in {'torch','ultralytics','cv2','onnxruntime','tensorrt','numpy'} for n in sys.modules)"
        )
        completed = subprocess.run([sys.executable, "-S", "-c", code], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
