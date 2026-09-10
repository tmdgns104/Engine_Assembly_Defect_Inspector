"""Structural adapter contracts; this module opens no device or model."""

from typing import Protocol, runtime_checkable

from .models import CameraFrame, DetectionResult


class CameraError(RuntimeError):
    """Backend-neutral capture/lifecycle failure, including exhausted input."""


class DetectorError(RuntimeError):
    """Backend-neutral inference failure; never substitute empty detections."""


@runtime_checkable
class Camera(Protocol):
    """Synchronous capture; no inherited implementation is required."""

    def capture(self) -> CameraFrame:
        """Return a frame with stable payload for its consumer, or raise CameraError."""
        ...

    def status(self) -> bool:
        """True means ready; False means closed/unavailable (not an inspection verdict)."""
        ...

    def close(self) -> None:
        """Release resources; repeated close is safe. Failures raise CameraError."""
        ...


@runtime_checkable
class Detector(Protocol):
    def detect(self, frame: CameraFrame) -> DetectionResult:
        """Keep input frame_id, return original-image pixel boxes, or raise DetectorError."""
        ...
