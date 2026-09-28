"""Immutable provider inputs and sidecar evidence, separate from clearance truth."""
from dataclasses import asdict, dataclass, field
from enum import Enum
import math

import numpy as np

from src.tracking.contracts import NormalizedBox, ProductObservation


def validate_bgr(image: np.ndarray) -> None:
    """Require nonempty uint8 HWC BGR; never cast, reshape or resize."""
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise TypeError('image must be a uint8 BGR ndarray')
    if image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1:
        raise ValueError('image must have nonempty shape (height, width, 3)')


def _integer(value: int, name: str, minimum: int) -> None:
    if type(value) is not int:
        raise TypeError(f'{name} must be an integer')
    if value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')


@dataclass(frozen=True, slots=True, init=False)
class AuthorizedEmptyReference:
    """Caller attests empty-state authority; immutable bytes prevent alias mutation.

    This validates the declaration, not physical truth. No refresh/adaptation API.
    """
    authority_id: str
    source_frame_count: int
    shape: tuple[int, int, int]
    _pixels: bytes = field(repr=False)

    def __init__(self, image: np.ndarray, authority_id: str, source_frame_count: int):
        validate_bgr(image)
        if type(authority_id) is not str or not authority_id.strip():
            raise ValueError('explicit nonblank empty-reference authority_id required')
        _integer(source_frame_count, 'source_frame_count', 1)
        object.__setattr__(self, 'authority_id', authority_id)
        object.__setattr__(self, 'source_frame_count', source_frame_count)
        object.__setattr__(self, 'shape', image.shape)
        object.__setattr__(self, '_pixels', image.tobytes(order='C'))

    @property
    def image(self) -> np.ndarray:
        """Read-only view backed by immutable bytes, not a writable owner array."""
        return np.frombuffer(self._pixels, dtype=np.uint8).reshape(self.shape)


@dataclass(frozen=True, slots=True)
class StaticReferenceConfig:
    """All thresholds/geometry are caller supplied; there are no production defaults."""
    absdiff_threshold: int
    open_kernel: int
    close_kernel: int
    min_component_area_px: int
    corridor: NormalizedBox
    max_normalized_bbox_area: float

    def __post_init__(self):
        _integer(self.absdiff_threshold, 'absdiff_threshold', 0)
        if self.absdiff_threshold > 255:
            raise ValueError('absdiff_threshold must be <= 255')
        for name in ('open_kernel', 'close_kernel'):
            value = getattr(self, name)
            _integer(value, name, 1)
            if value % 2 != 1:
                raise ValueError(f'{name} must be odd')
        _integer(self.min_component_area_px, 'min_component_area_px', 1)
        if type(self.corridor) is not NormalizedBox:
            raise TypeError('corridor must use the existing NormalizedBox contract')
        if self.corridor.width <= 0 or self.corridor.height <= 0:
            raise ValueError('corridor must have positive area')
        area = self.max_normalized_bbox_area
        if type(area) not in (int, float) or not 0 < area <= 1 or not math.isfinite(area):
            raise ValueError('max_normalized_bbox_area must be finite in (0, 1]')


class ProviderStatus(str, Enum):
    PRODUCT_OBSERVED = 'PRODUCT_OBSERVED'
    NO_FOREGROUND = 'NO_FOREGROUND'
    AMBIGUOUS_FOREGROUND = 'AMBIGUOUS_FOREGROUND'


class AmbiguityReason(str, Enum):
    MULTIPLE_FOREGROUND_COMPONENTS = 'MULTIPLE_FOREGROUND_COMPONENTS'
    MERGED_FOREGROUND_ENVELOPE = 'MERGED_FOREGROUND_ENVELOPE'
    FOREGROUND_OUTSIDE_PRODUCT_CORRIDOR = 'FOREGROUND_OUTSIDE_PRODUCT_CORRIDOR'
    NO_USABLE_PRODUCT_ENVELOPE = 'NO_USABLE_PRODUCT_ENVELOPE'


@dataclass(frozen=True, slots=True)
class ComponentEvidence:
    """Measured component bounds are diagnostics, not accepted product observations."""
    bbox: NormalizedBox
    area_pixels: int
    corridor_relation: str

    def __post_init__(self):
        if type(self.bbox) is not NormalizedBox:
            raise TypeError('component bbox must be NormalizedBox')
        _integer(self.area_pixels, 'area_pixels', 1)
        if self.corridor_relation not in ('INSIDE', 'OUTSIDE', 'OVERLAP'):
            raise ValueError('invalid corridor relation')


@dataclass(frozen=True, slots=True)
class ProviderResult:
    observations: tuple[ProductObservation, ...]
    status: ProviderStatus
    reason: AmbiguityReason | None
    threshold_pixels: int
    foreground_pixels: int
    total_components: int
    components: tuple[ComponentEvidence, ...]
    clear_authority: bool = field(default=False, init=False)

    def __post_init__(self):
        if type(self.observations) is not tuple or any(type(o) is not ProductObservation for o in self.observations):
            raise TypeError('observations must be a tuple of existing ProductObservation')
        if type(self.status) is not ProviderStatus or len(self.observations) > 1:
            raise ValueError('invalid provider status or observation count')
        if (self.status == ProviderStatus.PRODUCT_OBSERVED) != (len(self.observations) == 1):
            raise ValueError('only PRODUCT_OBSERVED may contain exactly one observation')
        if self.status == ProviderStatus.AMBIGUOUS_FOREGROUND:
            if type(self.reason) is not AmbiguityReason:
                raise ValueError('ambiguity requires an explicit reason')
        elif self.reason is not None:
            raise ValueError('reason belongs only to AMBIGUOUS_FOREGROUND')
        for name in ('threshold_pixels', 'foreground_pixels', 'total_components'):
            _integer(getattr(self, name), name, 0)
        if type(self.components) is not tuple or any(type(c) is not ComponentEvidence for c in self.components):
            raise TypeError('components must be an immutable evidence tuple')
        if len(self.components) > self.total_components:
            raise ValueError('eligible component count exceeds total count')

    def to_dict(self) -> dict:
        return {
            'observations': [asdict(observation) for observation in self.observations],
            'status': self.status.value,
            'reason': self.reason.value if self.reason else None,
            'threshold_pixels': self.threshold_pixels,
            'foreground_pixels': self.foreground_pixels,
            'total_components': self.total_components,
            'components': [asdict(component) for component in self.components],
            'clear_authority': False,
        }
