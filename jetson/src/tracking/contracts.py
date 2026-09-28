"""Immutable normalized tracking values, independent of models and inspection truth.

Type mismatches raise TypeError; invalid values raise ValueError. State-machine
operation rejection uses TrackingError and a stable reason_code.
"""

from dataclasses import dataclass
from enum import Enum
import math


def require_text(value: str, name: str) -> None:
    if type(value) is not str:
        raise TypeError(f'{name} must be a built-in str')
    if not value.strip():
        raise ValueError(f'{name} must not be blank')


def require_number(value: float, name: str) -> None:
    if type(value) not in (int, float):
        raise TypeError(f'{name} must be a built-in number')
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < 0:
        raise ValueError(f'{name} must be finite and nonnegative')


def require_integer(value: int, name: str, minimum: int) -> None:
    if type(value) is not int:
        raise TypeError(f'{name} must be a built-in int')
    if value < minimum:
        raise ValueError(f'{name} must be >= {minimum}')


class TrackState(str, Enum):
    IDLE = 'IDLE'
    TRACKING = 'TRACKING'
    INSPECTION_READY = 'INSPECTION_READY'
    INSPECTED = 'INSPECTED'
    CLEARING = 'CLEARING'
    WAIT_AREA_CLEAR = 'WAIT_AREA_CLEAR'
    LOST = 'LOST'


class WindowRelation(str, Enum):
    UPSTREAM = 'UPSTREAM'
    INSIDE = 'INSIDE'
    DOWNSTREAM = 'DOWNSTREAM'


class TrackingReason(str, Enum):
    AMBIGUOUS_TRACK_START = 'AMBIGUOUS_TRACK_START'
    DOWNSTREAM_WITHOUT_ACTIVE_TRACK = 'DOWNSTREAM_WITHOUT_ACTIVE_TRACK'
    AMBIGUOUS_ACTIVE_OBSERVATIONS = 'AMBIGUOUS_ACTIVE_OBSERVATIONS'
    TRACK_ASSOCIATION_INVALID = 'TRACK_ASSOCIATION_INVALID'
    FRAME_SEQUENCE_REGRESSION = 'FRAME_SEQUENCE_REGRESSION'
    FRAME_TIME_REGRESSION = 'FRAME_TIME_REGRESSION'
    MISSED_OBSERVATION_LIMIT = 'MISSED_OBSERVATION_LIMIT'
    MISSED_INSPECTION_COMPLETION = 'MISSED_INSPECTION_COMPLETION'
    TRACK_ID_MISMATCH = 'TRACK_ID_MISMATCH'
    INSPECTION_ALREADY_ATTACHED = 'INSPECTION_ALREADY_ATTACHED'
    INVALID_STATE_TRANSITION = 'INVALID_STATE_TRANSITION'
    WINDOW_CROSS_AXIS_OUTSIDE = 'WINDOW_CROSS_AXIS_OUTSIDE'
    MISSED_INSPECTION_WINDOW = 'MISSED_INSPECTION_WINDOW'


class TrackingError(ValueError):
    def __init__(self, reason_code: TrackingReason):
        self.reason_code = reason_code
        super().__init__(reason_code.value)


@dataclass(frozen=True, slots=True)
class NormalizedBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ('x1', 'y1', 'x2', 'y2'):
            value = getattr(self, name)
            require_number(value, name)
            if value > 1:
                raise ValueError(f'{name} must be <= 1')
        if self.x1 > self.x2 or self.y1 > self.y2:
            raise ValueError('box edges must be ordered')

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass(frozen=True, slots=True)
class InspectionWindow(NormalizedBox):
    """Inclusive center-membership rectangle in station/camera coordinates."""

    def __post_init__(self) -> None:
        NormalizedBox.__post_init__(self)
        if self.width == 0 or self.height == 0:
            raise ValueError('inspection window must have positive area')


@dataclass(frozen=True, slots=True)
class ProductObservation:
    bbox: NormalizedBox
    source: str

    def __post_init__(self) -> None:
        if type(self.bbox) is not NormalizedBox:
            raise TypeError('bbox must be NormalizedBox')
        require_text(self.source, 'source')


@dataclass(frozen=True, slots=True)
class TrackingFrame:
    frame_id: str
    sequence: int
    monotonic_s: float
    observations: tuple[ProductObservation, ...]

    def __post_init__(self) -> None:
        require_text(self.frame_id, 'frame_id')
        require_integer(self.sequence, 'sequence', 0)
        require_number(self.monotonic_s, 'monotonic_s')
        if type(self.observations) is not tuple or any(type(o) is not ProductObservation for o in self.observations):
            raise TypeError('observations must be a tuple of ProductObservation')


@dataclass(frozen=True, slots=True)
class SingleActiveTrackerConfig:
    inspection_window: InspectionWindow
    axis: str
    direction: int
    max_center_step_norm: float
    max_reverse_step_norm: float
    max_missed_frames: int
    clear_frames: int
    # AUTO 후보 확장. None/False는 승인된 기존 frame-count 동작을 보존한다.
    max_center_speed_norm_s: float | None = None
    max_unobserved_seconds: float | None = None
    allow_pending_downstream: bool = False
    free_motion: bool = False
    zone_hysteresis: float = 0.0
    zone_entry_frames: int = 1
    wait_area_clear: bool = False

    def __post_init__(self) -> None:
        if type(self.inspection_window) is not InspectionWindow:
            raise TypeError('inspection_window must be InspectionWindow')
        if type(self.axis) is not str or self.axis not in ('x', 'y'):
            raise ValueError('axis must be x or y')
        if type(self.direction) is not int or self.direction not in (-1, 1):
            raise ValueError('direction must be integer -1 or +1')
        require_number(self.max_center_step_norm, 'max_center_step_norm')
        require_number(self.max_reverse_step_norm, 'max_reverse_step_norm')
        if not 0 < self.max_center_step_norm <= 1:
            raise ValueError('max_center_step_norm must be in (0, 1]')
        if self.max_reverse_step_norm > self.max_center_step_norm:
            raise ValueError('reverse limit cannot exceed total step limit')
        require_integer(self.max_missed_frames, 'max_missed_frames', 0)
        require_integer(self.clear_frames, 'clear_frames', 1)
        for name in ('max_center_speed_norm_s', 'max_unobserved_seconds'):
            value = getattr(self, name)
            if value is not None:
                require_number(value, name)
                if value <= 0:
                    raise ValueError(name + ' must be positive')
        if type(self.free_motion) is not bool: raise TypeError('free_motion must be bool')
        if type(self.wait_area_clear) is not bool: raise TypeError('wait_area_clear must be bool')
        if self.wait_area_clear and not self.free_motion:
            raise ValueError('AREA_CLEARANCE_REQUIRES_FREE_MOTION_BENCH')
        require_number(self.zone_hysteresis, 'zone_hysteresis')
        if not 0 <= self.zone_hysteresis <= .2: raise ValueError('invalid zone hysteresis')
        require_integer(self.zone_entry_frames, 'zone_entry_frames', 1)
        if type(self.allow_pending_downstream) is not bool:
            raise TypeError('allow_pending_downstream must be bool')


@dataclass(frozen=True, slots=True)
class InspectionWindowEvent:
    track_id: int
    frame_id: str
    sequence: int
    monotonic_s: float

    def __post_init__(self) -> None:
        require_integer(self.track_id, 'track_id', 1)
        require_text(self.frame_id, 'frame_id')
        require_integer(self.sequence, 'sequence', 0)
        require_number(self.monotonic_s, 'monotonic_s')

    def to_dict(self) -> dict:
        return {'track_id': self.track_id, 'frame_id': self.frame_id,
                'sequence': self.sequence, 'monotonic_s': self.monotonic_s}


@dataclass(frozen=True, slots=True)
class TrackingUpdate:
    frame_id: str
    sequence: int
    state: TrackState
    active_track_id: int | None
    inspection_event: InspectionWindowEvent | None
    reason_code: TrackingReason | None
    missed_frames: int
    window_relation: WindowRelation | None
    inspection_id: str | None
    clear_count: int

    def __post_init__(self) -> None:
        require_text(self.frame_id, 'frame_id')
        require_integer(self.sequence, 'sequence', 0)
        require_integer(self.missed_frames, 'missed_frames', 0)
        require_integer(self.clear_count, 'clear_count', 0)
        if type(self.state) is not TrackState:
            raise TypeError('state must be TrackState')
        if self.active_track_id is not None:
            require_integer(self.active_track_id, 'active_track_id', 1)
        if self.inspection_id is not None:
            require_text(self.inspection_id, 'inspection_id')
        for name, expected in [('reason_code', TrackingReason), ('window_relation', WindowRelation),
                               ('inspection_event', InspectionWindowEvent)]:
            value = getattr(self, name)
            if value is not None and type(value) is not expected:
                raise TypeError(f'{name} must be {expected.__name__} or None')

    def to_dict(self) -> dict:
        return {'frame_id': self.frame_id, 'sequence': self.sequence, 'state': self.state.value,
                'active_track_id': self.active_track_id,
                'inspection_event': self.inspection_event.to_dict() if self.inspection_event else None,
                'reason_code': self.reason_code.value if self.reason_code else None,
                'missed_frames': self.missed_frames,
                'window_relation': self.window_relation.value if self.window_relation else None,
                'inspection_id': self.inspection_id, 'clear_count': self.clear_count}
