"""Explicit adapter selection in the Worker; never infer a backend or silently fall back."""
from typing import Protocol

from src.contracts import Detector, DetectorError
from src.recipe.package import PackageError, ProductPackage, validate_backend


class RuntimeDetector(Detector, Protocol):
    """Worker readiness metadata is separate from each DetectionResult's stable semantics."""

    def runtime_metadata(self) -> dict:
        """Return a detached JSON-compatible snapshot, without native runtime objects."""
        ...


def create_detector(package: ProductPackage, *, latency_enabled=False) -> RuntimeDetector:
    """Accept a validated package; backend rejection precedes any adapter import or file read."""
    try:
        backend = validate_backend(package.manifest)
    except PackageError as error:
        raise DetectorError(str(error)) from error
    if backend == "tensorrt":
        raise DetectorError("TENSORRT_BACKEND_NOT_IMPLEMENTED")
    # This import is intentionally after selection. Importing the module itself loads no framework.
    from src.vision.pytorch_detector import PyTorchDetector
    return PyTorchDetector(package.model_path, package.manifest["files"]["model"]["sha256"],
                           package.names, package.preprocessing["confidence"],
                           package.preprocessing["nms_iou"], package.preprocessing,
                           latency_enabled=latency_enabled)
