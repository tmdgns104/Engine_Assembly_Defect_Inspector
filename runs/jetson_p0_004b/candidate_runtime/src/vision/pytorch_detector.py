"""GPU-only BENCH adapter; deployment must pass the original model hash."""

import hashlib
import copy
import time
from pathlib import Path

from src.contracts import BoundingBox, Detection, DetectionResult, DetectorError


class PyTorchDetector:
    def __init__(self, model_path, expected_sha256, class_names, confidence=0.25, nms_iou=0.7, preprocessing=None, *, latency_enabled=False):
        import torch
        from ultralytics import YOLO

        self.torch = torch
        self.latency_enabled = latency_enabled
        self.last_reported_speed = None
        self.startup_timestamps_ns = {}
        self.model_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
        if self.model_hash != expected_sha256:
            raise DetectorError("MODEL_HASH_MISMATCH")
        if not torch.cuda.is_available():
            raise DetectorError("CUDA_REQUIRED; CPU fallback is disabled")
        if latency_enabled:
            self.startup_timestamps_ns['model_cpu_load_start'] = time.monotonic_ns()
        self.model = YOLO(str(model_path))
        if latency_enabled:
            self.startup_timestamps_ns['model_cpu_load_end'] = time.monotonic_ns()
            self.startup_timestamps_ns['model_to_cuda_start'] = time.monotonic_ns()
        self.model = self.model.to("cuda:0")
        if latency_enabled:
            self.startup_timestamps_ns['model_to_cuda_ready'] = time.monotonic_ns()
        if self.model.task != "detect":
            raise DetectorError("MODEL_TASK_MISMATCH")
        if self.model.names != dict(enumerate(class_names)):
            raise DetectorError("MODEL_CLASSES_MISMATCH")
        self.confidence = confidence
        self.nms_iou = nms_iou
        if preprocessing is None:
            raise DetectorError("Explicit preprocessing configuration is required")
        self.preprocessing = preprocessing
        self.input_shape = None
        self.model.model.register_forward_pre_hook(self._observe_input)
        self.device = str(next(self.model.model.parameters()).device)
        if self.device != "cuda:0":
            raise DetectorError("MODEL_NOT_ON_CUDA")

    def _observe_input(self, module, inputs):
        self.input_shape = list(inputs[0].shape)

    def runtime_metadata(self):
        """Readiness/provenance snapshot; no synchronize, model call or detection-schema change."""
        return copy.deepcopy({
            "backend": "pytorch", "device": self.device,
            "gpu": self.torch.cuda.get_device_name(0), "input_shape": self.input_shape,
            "artifact_sha256": self.model_hash, "source_model_sha256": self.model_hash,
            "observed_runtime": {"torch": self.torch.__version__, "cuda": self.torch.version.cuda},
            "timing": {"latency_enabled": self.latency_enabled,
                       "last_reported_speed": self.last_reported_speed,
                       "startup_timestamps_ns": self.startup_timestamps_ns}})

    def detect(self, frame):
        try:
            self.torch.cuda.synchronize()
            start = time.perf_counter()
            result = self.model.predict(frame.image, imgsz=self.preprocessing["size"], rect=False, device=0,
                                        half=False, conf=self.confidence, iou=self.nms_iou,
                                        augment=False, verbose=False)[0]
            self.torch.cuda.synchronize()
            elapsed = (time.perf_counter() - start) * 1000
            detections = []
            for row in result.boxes.data.detach().cpu().tolist():
                x1, y1, x2, y2, score, class_id = row
                index = int(class_id)
                detections.append(Detection(index, self.model.names[index], float(score),
                                             BoundingBox(float(x1), float(y1), float(x2), float(y2))))
            if self.latency_enabled:
                # Preserve upstream timings separately; never rename the legacy predict timer.
                self.last_reported_speed = dict(result.speed)
            return DetectionResult(frame.frame_id, tuple(detections), self.model_hash, elapsed)
        except Exception as error:
            raise DetectorError(f"{type(error).__name__}: {error}") from error
