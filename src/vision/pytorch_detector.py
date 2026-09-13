"""GPU-only BENCH adapter; deployment must pass the original model hash."""

import hashlib
import time
from pathlib import Path

from src.contracts import BoundingBox, Detection, DetectionResult, DetectorError


class PyTorchDetector:
    def __init__(self, model_path, expected_sha256, class_names, confidence=0.25, nms_iou=0.7):
        import torch
        from ultralytics import YOLO

        self.torch = torch
        self.model_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
        if self.model_hash != expected_sha256:
            raise DetectorError("MODEL_HASH_MISMATCH")
        if not torch.cuda.is_available():
            raise DetectorError("CUDA_REQUIRED; CPU fallback is disabled")
        self.model = YOLO(str(model_path)).to("cuda:0")
        if self.model.names != dict(enumerate(class_names)):
            raise DetectorError("MODEL_CLASSES_MISMATCH")
        self.confidence = confidence
        self.nms_iou = nms_iou
        self.input_shape = None
        self.model.model.register_forward_pre_hook(self._observe_input)
        self.device = str(next(self.model.model.parameters()).device)
        if self.device != "cuda:0":
            raise DetectorError("MODEL_NOT_ON_CUDA")

    def _observe_input(self, module, inputs):
        self.input_shape = list(inputs[0].shape)

    def detect(self, frame):
        try:
            self.torch.cuda.synchronize()
            start = time.perf_counter()
            result = self.model.predict(frame.image, imgsz=640, rect=False, device=0,
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
            return DetectionResult(frame.frame_id, tuple(detections), self.model_hash, elapsed)
        except Exception as error:
            raise DetectorError(f"{type(error).__name__}: {error}") from error
