"""Validated in-memory contracts and explicit JSON-safe projections.

Invalid field types raise TypeError; invalid values raise ValueError.
No serializer walks arbitrary objects or touches the image payload.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from .enums import ReasonCode, ResultStatus, RunMode


def _text(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


def _number(value: float, name: str, minimum: float = 0) -> None:
    # bool and framework scalar objects are not contract numbers.
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a built-in int or float")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")


def _integer(value: int, name: str, minimum: int) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be a built-in int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _tuple_of(value: tuple, item_type: type, name: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be a tuple")
    if not all(isinstance(item, item_type) for item in value):
        raise TypeError(f"{name} items must be {item_type.__name__}")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Nonnegative xyxy pixel edges in the original image, top-left origin."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ("x1", "y1", "x2", "y2"):
            _number(getattr(self, name), name)
        if self.x1 > self.x2 or self.y1 > self.y2:
            raise ValueError("bounding box requires x1 <= x2 and y1 <= y2")

    def to_dict(self) -> dict:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}


@dataclass(frozen=True, slots=True)
class Detection:
    """One observation, not a physical-defect decision."""

    class_id: int
    class_name: str
    confidence: float
    bounding_box: BoundingBox

    def __post_init__(self) -> None:
        _integer(self.class_id, "class_id", 0)
        _text(self.class_name, "class_name")
        _number(self.confidence, "confidence")
        if self.confidence > 1:
            raise ValueError("confidence must be <= 1")
        if not isinstance(self.bounding_box, BoundingBox):
            raise TypeError("bounding_box must be BoundingBox")

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """A completed detector call; empty detections are a valid observation."""

    frame_id: str
    detections: tuple[Detection, ...] = ()
    model_version: str | None = None
    inference_ms: float | None = None

    def __post_init__(self) -> None:
        _text(self.frame_id, "frame_id")
        _tuple_of(self.detections, Detection, "detections")
        if self.model_version is not None:
            _text(self.model_version, "model_version")
        if self.inference_ms is not None:
            _number(self.inference_ms, "inference_ms")

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "detections": [item.to_dict() for item in self.detections],
            "model_version": self.model_version,
            "inference_ms": self.inference_ms,
        }


@dataclass(frozen=True, slots=True)
class FrameMetadata:
    """Serializable identity, capture time and original image dimensions."""

    frame_id: str
    captured_at: datetime
    width: int
    height: int
    source: str | None = None

    def __post_init__(self) -> None:
        _text(self.frame_id, "frame_id")
        _integer(self.width, "width", 1)
        _integer(self.height, "height", 1)
        object.__setattr__(self, "captured_at", _utc(self.captured_at, "captured_at"))
        if self.source is not None:
            _text(self.source, "source")

    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "captured_at": self.captured_at.isoformat(),
            "width": self.width,
            "height": self.height,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class CameraFrame:
    """Image payload stays in memory; use to_metadata() for external results.

    The adapter owns pixel layout and buffer lifetime. Freezing this wrapper
    does not freeze or copy a mutable image buffer.
    """

    image: object
    frame_id: str
    captured_at: datetime
    width: int
    height: int
    source: str | None = None

    def __post_init__(self) -> None:
        if self.image is None:
            raise ValueError("image must not be None")
        metadata = self.to_metadata()
        object.__setattr__(self, "captured_at", metadata.captured_at)

    def to_metadata(self) -> FrameMetadata:
        return FrameMetadata(
            frame_id=self.frame_id,
            captured_at=self.captured_at,
            width=self.width,
            height=self.height,
            source=self.source,
        )


@dataclass(frozen=True, slots=True)
class InspectionRequest:
    """Shared manual/PLC request; no equipment addresses or commands."""

    request_id: str
    run_mode: RunMode
    requested_at: datetime

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        if not isinstance(self.run_mode, RunMode):
            raise TypeError("run_mode must be RunMode")
        object.__setattr__(self, "requested_at", _utc(self.requested_at, "requested_at"))

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "run_mode": self.run_mode.value,
            "requested_at": self.requested_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Reason:
    """Stable code plus human-readable explanation.

    A nonblank string permits later domain codes without adding result states.
    """

    code: ReasonCode | str
    message: str

    def __post_init__(self) -> None:
        _text(self.code, "code")
        _text(self.message, "message")

    def to_dict(self) -> dict:
        return {"code": str(self.code), "message": self.message}


@dataclass(frozen=True, slots=True)
class InspectionResult:
    """Final result envelope, without images or backend model objects.

    A PASS needs at least frame metadata and an evidence reference structurally.
    T12/T13 must verify sufficiency, uncertainty and successful persistence.
    """

    request_id: str
    status: ResultStatus
    reasons: tuple[Reason, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    frame_meta: FrameMetadata | None = None

    def __post_init__(self) -> None:
        _text(self.request_id, "request_id")
        if not isinstance(self.status, ResultStatus):
            raise TypeError("status must be ResultStatus")
        _tuple_of(self.reasons, Reason, "reasons")
        _tuple_of(self.evidence_refs, str, "evidence_refs")
        for reference in self.evidence_refs:
            _text(reference, "evidence reference")
        if self.frame_meta is not None and not isinstance(self.frame_meta, FrameMetadata):
            raise TypeError("frame_meta must be FrameMetadata or None")
        if self.status == ResultStatus.PASS and (self.frame_meta is None or not self.evidence_refs):
            raise ValueError("PASS requires frame_meta and at least one evidence reference")
        if self.status != ResultStatus.PASS and not self.reasons:
            raise ValueError("FAIL, REVIEW and ERROR require an explanatory reason")

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "reasons": [reason.to_dict() for reason in self.reasons],
            "evidence_refs": list(self.evidence_refs),
            "frame_meta": self.frame_meta.to_dict() if self.frame_meta is not None else None,
        }
