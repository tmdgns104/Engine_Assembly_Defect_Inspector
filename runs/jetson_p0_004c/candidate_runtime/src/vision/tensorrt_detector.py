"""High-level CPU candidate. Native TensorRT/CUDA provider is not implemented."""
import copy
import json
import time
from typing import Protocol

from src.contracts import CameraFrame, DetectionResult, DetectorError
from src.contracts.interfaces import FatalDetectorError
from src.vision.tensorrt_preprocess import preprocess
from src.vision.tensorrt_postprocess import postprocess


class TensorRTExecutor(Protocol):
    """Native boundary owns completion and resources; no handles cross to Service.

    execute must finish/synchronize before returning named host arrays. The CPU
    candidate injects test executors; there is no default native implementation.
    """
    def execute(self, input_array) -> dict: ...
    def runtime_metadata(self) -> dict: ...
    def close(self) -> None: ...


class TensorRTDetector:
    def __init__(self, package, executor: TensorRTExecutor, *, latency_enabled=False):
        self.snapshot = package.snapshot()
        self.names = list(package.names)
        self.executor = executor
        self.latency_enabled = latency_enabled
        self.detector_host_total_ms = None
        self.runtime_state = "EXECUTOR_INJECTED_NATIVE_UNVERIFIED"
        self.closed = False
        self.usable = True

    def detect(self, frame):
        if self.closed or not self.usable:
            raise FatalDetectorError("INFERENCE_FAILED: detector closed or invalidated")
        start = time.perf_counter()
        self.detector_host_total_ms = None
        if (not isinstance(frame, CameraFrame) or getattr(frame.image, "shape", None)
                != (frame.height, frame.width, 3)):
            raise DetectorError("INPUT_CONTRACT_MISMATCH: frame dimensions")
        contract = self.snapshot["manifest"]["detector"]
        # Rejected inputs never touch the executor, so they are recoverable.
        tensor, transform = preprocess(frame.image, contract["input"]["dtype"])
        try:
            outputs = self.executor.execute(tensor)
        except Exception as error:
            self.usable = False
            self.runtime_state = "INVALIDATED"
            if isinstance(error, FatalDetectorError):
                raise
            # Usability is unproven after an unknown execution error. Stop without
            # guessing a driver/root cause or attempting another request.
            raise FatalDetectorError("INFERENCE_FAILED: " + str(error)) from error
        try:
            config = self.snapshot["preprocessing"]
            detections = postprocess(outputs, contract["output"], self.names,
                                     config["confidence"], config["nms_iou"], transform)
        except DetectorError as error:
            self.usable = False
            self.runtime_state = "INVALIDATED"
            raise FatalDetectorError(str(error)) from error
        elapsed = (time.perf_counter() - start) * 1000
        if self.latency_enabled:
            self.detector_host_total_ms = elapsed
        return DetectionResult(frame.frame_id, detections, contract["source_model_sha256"], elapsed)

    def runtime_metadata(self):
        manifest = self.snapshot["manifest"]
        contract = manifest["detector"]
        metadata = {
            "backend":"tensorrt", "artifact_sha256":manifest["files"]["model"]["sha256"],
            "source_model_sha256":contract["source_model_sha256"],
            "source_onnx_sha256":contract["provenance"]["source_onnx"]["sha256"],
            "input_contract":contract["input"], "output_contract":contract["output"],
            "precision":contract["precision"], "declared_provenance":contract["provenance"],
            "runtime_state":self.runtime_state, "observed_runtime":self.executor.runtime_metadata(),
            "timing":{"latency_enabled":self.latency_enabled,
                      "inference_ms_scope":"host preprocess + executor completion + postprocess",
                      "detector_host_total_ms":self.detector_host_total_ms, "h2d_ms":None}}
        try:
            return json.loads(json.dumps(metadata, allow_nan=False))
        except (ValueError, TypeError) as error:
            raise DetectorError("RUNTIME_METADATA_INVALID") from error

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.usable = False
        self.runtime_state = "CLOSED"
        try:
            self.executor.close()
        except Exception as error:
            self.runtime_state = "CLOSE_FAILED"
            raise FatalDetectorError("DETECTOR_CLOSE_FAILED: " + str(error)) from error
