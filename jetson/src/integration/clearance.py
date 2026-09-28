"""Explicit external clearance assertion, independent of visual absence."""
from dataclasses import dataclass, field
import math


@dataclass(frozen=True, slots=True)
class ClearanceEvidence:
    """Caller attests that the current active physical product cleared the region.

    Validates declaration shape only, not physical truth, authenticity, freshness
    or association to a physical cycle. The final authority source is not chosen
    here. No value is inferred from provider output or tracking state.
    """
    confirmed_clear: bool
    authority_id: str
    source: str

    def __post_init__(self):
        if type(self.confirmed_clear) is not bool:
            raise TypeError('confirmed_clear must be an explicit bool')
        for name in ('authority_id', 'source'):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise ValueError(f'{name} must be explicit nonblank text')


@dataclass(frozen=True, slots=True)
class VisionExitEvidence:
    """영상 정책의 추정 이탈. 물리 PLC 확인/confirmed_clear와 다른 계약이다."""
    authority_id: str
    exit_sequence: int
    empty_sequences: tuple[int, ...]
    exit_monotonic: float
    confirmed_monotonic: float
    source: str = field(default='VISION_INFERRED_EXIT', init=False)
    physical_clearance_verified: bool = field(default=False, init=False)

    def __post_init__(self):
        if not isinstance(self.authority_id, str) or not self.authority_id.strip():
            raise ValueError('영상 authority_id가 필요합니다')
        values = (self.exit_sequence,) + self.empty_sequences
        if type(self.empty_sequences) is not tuple or len(values) < 3:
            raise ValueError('출구 관측과 복수의 정상 빈 프레임이 필요합니다')
        if any(type(v) is not int or v < 0 for v in values) or any(b <= a for a,b in zip(values,values[1:])):
            raise ValueError('영상 이탈 frame sequence가 유효하지 않습니다')
        if not all(math.isfinite(t) for t in (self.exit_monotonic,self.confirmed_monotonic)) or self.confirmed_monotonic <= self.exit_monotonic:
            raise ValueError('영상 이탈 시간이 유효하지 않습니다')


@dataclass(frozen=True, slots=True)
class VisionAbsenceEvidence:
    """Bounded healthy envelope absence; does not assert a physically verified exit."""
    authority_id: str
    empty_sequences: tuple[int, ...]
    first_monotonic: float
    confirmed_monotonic: float
    source: str = field(default='VISION_BOUNDED_ABSENCE', init=False)
    physical_clearance_verified: bool = field(default=False, init=False)
    def __post_init__(self):
        if not isinstance(self.authority_id,str) or not self.authority_id: raise ValueError('AUTHORITY_REQUIRED')
        if (type(self.empty_sequences) is not tuple or len(self.empty_sequences)<6 or
            any(type(v) is not int or v<0 for v in self.empty_sequences) or
            any(b<=a for a,b in zip(self.empty_sequences,self.empty_sequences[1:]))):
            raise ValueError('ORDERED_HEALTHY_ABSENCE_REQUIRED')
        if (not all(math.isfinite(t) for t in (self.first_monotonic,self.confirmed_monotonic)) or
                self.confirmed_monotonic-self.first_monotonic<1.2):
            raise ValueError('BOUNDED_ABSENCE_DURATION_REQUIRED')


@dataclass(frozen=True, slots=True)
class AreaClearEvidence:
    """Independent reviewed-background authority, never detector absence or PLC IO."""
    authority_id: str
    empty_sequences: tuple[int, ...]
    first_monotonic: float
    confirmed_monotonic: float
    reference_version: str
    config_version: str
    termination_reason: str
    source: str = field(default='VISION_BACKGROUND_AREA_CLEAR', init=False)
    physical_clearance_verified: bool = field(default=False, init=False)

    def __post_init__(self):
        for value in (self.authority_id,self.reference_version,self.config_version):
            if not isinstance(value,str) or not value.strip(): raise ValueError('AREA_AUTHORITY_REQUIRED')
        if (type(self.empty_sequences) is not tuple or len(self.empty_sequences)<6 or
            any(type(s) is not int or s<0 for s in self.empty_sequences) or
            any(b<=a for a,b in zip(self.empty_sequences,self.empty_sequences[1:]))):
            raise ValueError('ORDERED_AREA_CLEAR_FRAMES_REQUIRED')
        if (not all(math.isfinite(t) for t in (self.first_monotonic,self.confirmed_monotonic)) or
                self.confirmed_monotonic-self.first_monotonic<1.2-1e-9):
            raise ValueError('AREA_CLEAR_DURATION_REQUIRED')
        if self.termination_reason not in ('EXIT_CONFIRMED','AREA_CLEAR_CONFIRMED'):
            raise ValueError('AREA_TERMINATION_REASON_REQUIRED')
