"""Explicit adapter selection in the Worker; never infer a backend or silently fall back."""
from typing import Protocol

from src.contracts import Detector, DetectorError
from src.recipe.package import PackageError, ProductPackage, validate_backend, validate_output_contract


class RuntimeDetector(Detector, Protocol):
    """Worker readiness metadata is separate from each DetectionResult's stable semantics."""

    def runtime_metadata(self) -> dict:
        """Return a detached JSON-compatible snapshot, without native runtime objects."""
        ...

    def close(self) -> None:
        """Release detector resources; repeated close is safe."""
        ...


def create_detector(package: ProductPackage, *, latency_enabled=False, executor_factory=None) -> RuntimeDetector:
    """Accept a validated package; backend rejection precedes any adapter import or file read."""
    try:
        backend = validate_backend(package.manifest)
    except PackageError as error:
        raise DetectorError(str(error)) from error
    if backend == "tensorrt":
        if package.manifest["detector"]["output"] is None:
            raise DetectorError("TENSORRT_CONTRACT_NON_EXECUTABLE")
        try:
            validate_output_contract(package.manifest["detector"]["output"], len(package.names))
        except PackageError as error:
            raise DetectorError(str(error)) from error
        if package.preprocessing["nms_location"] != "adapter":
            raise DetectorError("TENSORRT_CONTRACT_NON_EXECUTABLE")
        if package.manifest["files"]["model"]["artifact_format"] != "trt_plan":
            raise DetectorError("ARTIFACT_FORMAT_UNSUPPORTED")
        if executor_factory is None:
            raise DetectorError("TENSORRT_NATIVE_RUNTIME_NOT_IMPLEMENTED")
        # Explicit injection is the CPU test boundary, never a production fallback.
        from src.vision.tensorrt_detector import TensorRTDetector
        return TensorRTDetector(package, executor_factory(package), latency_enabled=latency_enabled)
    # This import is intentionally after selection. Importing the module itself loads no framework.
    from src.vision.pytorch_detector import PyTorchDetector
    return PyTorchDetector(package.model_path, package.manifest["files"]["model"]["sha256"],
                           package.names, package.preprocessing["confidence"],
                           package.preprocessing["nms_iou"], package.preprocessing,
                           latency_enabled=latency_enabled)
