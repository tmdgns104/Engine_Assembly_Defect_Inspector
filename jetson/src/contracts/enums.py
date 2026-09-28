"""Backend-neutral names shared by inspection callers and results."""

try:
    from enum import StrEnum
except ImportError:  # JetPack's Python 3.10; keep identical string/JSON behavior.
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


class ResultStatus(StrEnum):
    """Inspection outcomes; equipment safety states belong elsewhere."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    ERROR = "ERROR"


class RunMode(StrEnum):
    MANUAL = "manual"
    PLC = "plc"


class ReasonCode(StrEnum):
    """Common reasons, without engine-specific classes or tolerances."""

    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MISSING_REQUIRED_OBJECT = "MISSING_REQUIRED_OBJECT"
    UNEXPECTED_OBJECT = "UNEXPECTED_OBJECT"
    CAMERA_ERROR = "CAMERA_ERROR"
    DETECTOR_ERROR = "DETECTOR_ERROR"
    PERSISTENCE_ERROR = "PERSISTENCE_ERROR"
