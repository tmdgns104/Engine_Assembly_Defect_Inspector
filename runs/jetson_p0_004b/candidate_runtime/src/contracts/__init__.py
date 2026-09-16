"""Public runtime contracts. Importable without any ML or camera package."""

from .enums import ReasonCode, ResultStatus, RunMode
from .interfaces import Camera, CameraError, Detector, DetectorError
from .models import (
    BoundingBox,
    CameraFrame,
    Detection,
    DetectionResult,
    FrameMetadata,
    InspectionRequest,
    InspectionResult,
    Reason,
)

__all__ = [
    "BoundingBox", "Camera", "CameraError", "CameraFrame", "Detection",
    "DetectionResult", "Detector", "DetectorError", "FrameMetadata",
    "InspectionRequest", "InspectionResult", "Reason", "ReasonCode",
    "ResultStatus", "RunMode",
]
