"""Immutable cycle input and coordinator snapshots; no inspection truth."""
from dataclasses import asdict, dataclass
from enum import Enum

from src.integration.bound_clearance_gateway import BoundGatewayResult
from src.observation.contracts import ProviderStatus
from src.tracking.contracts import InspectionWindowEvent, TrackState, require_text


@dataclass(frozen=True, slots=True)
class CycleStart:
    runtime_session_id: str
    cycle_id: str

    def __post_init__(self):
        require_text(self.runtime_session_id, 'runtime_session_id')
        require_text(self.cycle_id, 'cycle_id')

    def to_dict(self) -> dict:
        return asdict(self)


class CoordinatorState(str, Enum):
    NO_ACTIVE_CYCLE = 'NO_ACTIVE_CYCLE'
    WAITING_FOR_PRODUCT = 'WAITING_FOR_PRODUCT'
    TRACK_ACTIVE = 'TRACK_ACTIVE'
    INSPECTION_READY = 'INSPECTION_READY'
    INSPECTED = 'INSPECTED'
    CLEARING = 'CLEARING'
    WAIT_AREA_CLEAR = 'WAIT_AREA_CLEAR'
    CYCLE_COMPLETE = 'CYCLE_COMPLETE'
    FAULTED = 'FAULTED'


@dataclass(frozen=True, slots=True)
class CoordinatorResult:
    runtime_session_id: str
    cycle_id: str | None
    track_id: int | None
    coordinator_state: CoordinatorState
    provider_status: ProviderStatus | None
    tracker_state_before: TrackState
    tracker_state_after: TrackState
    inspection_event: InspectionWindowEvent | None
    inspection_id: str | None
    binding_status: str
    gateway_disposition: str | None
    gateway_result: BoundGatewayResult | None
    cycle_retired: bool
    reason: str | None

    def to_dict(self) -> dict:
        return {
            'runtime_session_id': self.runtime_session_id,
            'cycle_id': self.cycle_id, 'track_id': self.track_id,
            'coordinator_state': self.coordinator_state.value,
            'provider_status': self.provider_status.value if self.provider_status else None,
            'tracker_state_before': self.tracker_state_before.value,
            'tracker_state_after': self.tracker_state_after.value,
            'inspection_event': self.inspection_event.to_dict() if self.inspection_event else None,
            'inspection_id': self.inspection_id,
            'binding_status': self.binding_status,
            'gateway_disposition': self.gateway_disposition,
            'gateway_result': self.gateway_result.to_dict() if self.gateway_result else None,
            'cycle_retired': self.cycle_retired, 'reason': self.reason,
        }
