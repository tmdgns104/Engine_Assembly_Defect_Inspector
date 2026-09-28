"""Serial cycle ownership; delegate observation, identity and tracking semantics."""
from src.integration.bound_clearance_gateway import BoundClearanceGateway
from src.integration.cycle_track_binding import BoundClearanceEvidence
from src.observation.contracts import ProviderResult, ProviderStatus
from src.tracking.contracts import SingleActiveTrackerConfig, TrackState, require_integer, require_text
from src.tracking.single_active import SingleActiveTracker
from .contracts import CoordinatorResult, CoordinatorState, CycleStart


class VisionRuntimeCoordinator:
    """Own one G and one H5 for one explicit session; do not reuse after restart.

    All methods are serial. No external direct access to owned components is
    supported. Frozen G has no public state/identity getter: narrow private reads
    project current state without duplicating its state machine. Never write G
    internals, call its step directly, bypass H5 or reset a LOST tracker.
    """

    def __init__(self, runtime_session_id: str, tracker_config: SingleActiveTrackerConfig):
        require_text(runtime_session_id, 'runtime_session_id')
        self._session_id = runtime_session_id
        self._tracker = SingleActiveTracker(tracker_config)
        self._gateway = BoundClearanceGateway(self._tracker, runtime_session_id)
        self._active_cycle: CycleStart | None = None
        self._retired_cycles: set[str] = set()

    @property
    def runtime_session_id(self) -> str:
        return self._session_id

    @property
    def active_cycle(self) -> CycleStart | None:
        return self._active_cycle

    def _projection(self) -> CoordinatorState:
        state = self._tracker._state
        if state == TrackState.LOST:
            return CoordinatorState.FAULTED
        if self._active_cycle is None:
            return CoordinatorState.NO_ACTIVE_CYCLE
        return {
            TrackState.IDLE: CoordinatorState.WAITING_FOR_PRODUCT,
            TrackState.TRACKING: CoordinatorState.TRACK_ACTIVE,
            TrackState.INSPECTION_READY: CoordinatorState.INSPECTION_READY,
            TrackState.INSPECTED: CoordinatorState.INSPECTED,
            TrackState.CLEARING: CoordinatorState.CLEARING,
            TrackState.WAIT_AREA_CLEAR: CoordinatorState.WAIT_AREA_CLEAR,
        }[state]

    def _result(self, before, provider_status=None, gateway_result=None,
                inspection_event=None, completed_cycle=None, completed_track=None,
                completed_inspection=None, reason=None) -> CoordinatorResult:
        completed = completed_cycle is not None
        binding_status = 'BOUND' if self._gateway.active_binding else 'UNBOUND'
        if self._tracker._state == TrackState.LOST:
            binding_status = 'RETIRED_NON_CLEARABLE'
        elif completed:
            binding_status = 'RETIRED'
        cycle = completed_cycle if completed else self._active_cycle
        return CoordinatorResult(
            self._session_id, cycle.cycle_id if cycle else None,
            completed_track if completed else self._tracker._track_id,
            CoordinatorState.CYCLE_COMPLETE if completed else self._projection(),
            provider_status, before, self._tracker._state, inspection_event,
            completed_inspection if completed else self._tracker._inspection_id,
            binding_status, gateway_result.gateway_disposition if gateway_result else None,
            gateway_result, completed, reason,
        )

    def start_cycle(self, cycle: CycleStart) -> CoordinatorResult:
        if type(cycle) is not CycleStart:
            raise TypeError('CycleStart required')
        if cycle.runtime_session_id != self._session_id:
            raise ValueError('SESSION_MISMATCH')
        if self._tracker._state == TrackState.LOST:
            raise ValueError('RECOVERY_REQUIRED')
        if cycle.cycle_id in self._retired_cycles:
            raise ValueError('CYCLE_ALREADY_RETIRED')
        if self._active_cycle is not None and self._active_cycle != cycle:
            raise ValueError('ACTIVE_CYCLE_EXISTS')
        self._active_cycle = cycle
        return self._result(self._tracker._state)

    def route(self, frame_id: str, sequence: int, monotonic_s: float,
              provider_result: ProviderResult,
              evidence: BoundClearanceEvidence | None = None) -> CoordinatorResult:
        """Bootstrap only after cycle start; all evidence delegates through H5.

        H5 consumes identity-valid events before downstream validation/delegation.
        Preserve its exceptions and consumed-event state; do not retry or relabel
        evidence. This is serial in-process ordering, not a durable transaction.
        """
        before = self._tracker._state
        # Type/input errors otherwise belong to H5/H4 so their consumption rule
        # is preserved. Only inspect status when this is an actual provider value.
        status = provider_result.status if type(provider_result) is ProviderResult else None
        if self._active_cycle is None and status == ProviderStatus.PRODUCT_OBSERVED:
            return self._result(before, status, reason='CYCLE_REQUIRED_FOR_PRODUCT')
        if before == TrackState.LOST and evidence is None:
            return self._result(before, status, reason='RECOVERY_REQUIRED')
        cycle = self._active_cycle
        track = self._tracker._track_id
        inspection = self._tracker._inspection_id
        result = self._gateway.route(frame_id, sequence, monotonic_s, provider_result, evidence)
        update = result.h4_result.tracker_update if result.h4_result else None

        # Ordered bootstrap: the real tracker chooses identity, then H5 validates
        # and binds it before the caller can receive an inspection-window event.
        if (cycle is not None and before == TrackState.IDLE and update is not None
                and update.active_track_id is not None):
            self._gateway.bind(cycle.cycle_id, update.active_track_id)

        completed = (cycle is not None and result.binding_retired
                     and before == TrackState.CLEARING
                     and result.tracker_state_after == TrackState.IDLE)
        if completed:
            self._retired_cycles.add(cycle.cycle_id)
            self._active_cycle = None
        # LOST leaves the cycle present and projected FAULTED. H5 has retired its
        # binding. There is intentionally no recovery or replacement operation.
        reason = update.reason_code.value if update and update.reason_code else result.reason
        return self._result(before, status, result,
            inspection_event=update.inspection_event if update else None,
            completed_cycle=cycle if completed else None,
            completed_track=track, completed_inspection=inspection, reason=reason)

    def mark_inspected(self, cycle_id: str, track_id: int, inspection_id: str) -> CoordinatorResult:
        """Attach an external inspection ID once, never compute inspection truth."""
        require_text(cycle_id, 'cycle_id')
        require_integer(track_id, 'track_id', 1)
        require_text(inspection_id, 'inspection_id')
        if self._active_cycle is None or self._active_cycle.cycle_id != cycle_id:
            raise ValueError('CYCLE_MISMATCH')
        binding = self._gateway.active_binding
        if binding is None or binding.track_id != track_id or self._tracker._track_id != track_id:
            raise ValueError('TRACK_MISMATCH')
        before = self._tracker._state
        self._tracker.mark_inspected(track_id, inspection_id)
        return self._result(before)
