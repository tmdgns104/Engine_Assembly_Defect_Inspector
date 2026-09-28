"""Process-local identity/replay gate. Physical semantics belong to H4 alone."""
from dataclasses import dataclass

from src.observation.contracts import ProviderResult
from src.tracking.contracts import TrackState
from src.tracking.single_active import SingleActiveTracker
from .cycle_track_binding import BoundClearanceEvidence, CycleTrackBinding, _nonblank
from .provider_tracker_bridge import BridgeResult, ProviderTrackerBridge


@dataclass(frozen=True, slots=True)
class BoundGatewayResult:
    binding: CycleTrackBinding | None
    evidence: BoundClearanceEvidence | None
    identity_validation: str
    gateway_disposition: str
    h4_called: bool
    h4_result: BridgeResult | None
    tracker_state_before: TrackState
    tracker_state_after: TrackState
    binding_retired: bool
    reason: str | None

    def to_dict(self) -> dict:
        return {
            'binding': self.binding.to_dict() if self.binding else None,
            'evidence': self.evidence.to_dict() if self.evidence else None,
            'identity_validation': self.identity_validation,
            'gateway_disposition': self.gateway_disposition,
            'h4_called': self.h4_called,
            'h4_result': self.h4_result.to_dict() if self.h4_result else None,
            'tracker_state_before': self.tracker_state_before.value,
            'tracker_state_after': self.tracker_state_after.value,
            'binding_retired': self.binding_retired,
            'reason': self.reason,
        }


class BoundClearanceGateway:
    """One registry for one caller-owned tracker and runtime session, serial use only.

    Retain this instance for the entire session; reconstructing it loses ledgers.
    All provider routing must use this gateway. The caller may mark_inspected or
    explicitly reset LOST, but must not bypass it with raw clearance calls.
    Frozen G exposes no public identity getter: read `_state`/`_track_id`, never
    write them. There is no durable, distributed or authenticated authority here.
    """

    def __init__(self, tracker: SingleActiveTracker, runtime_session_id: str):
        _nonblank(runtime_session_id, 'runtime_session_id')
        self._bridge = ProviderTrackerBridge(tracker)
        self._tracker = tracker
        self._session_id = runtime_session_id
        self._active: CycleTrackBinding | None = None
        self._retired_cycles: set[str] = set()
        self._evidence_ids: set[str] = set()
        self._source_epochs: dict[str, str] = {}
        self._source_sequences: dict[tuple[str, str, str], int] = {}

    @property
    def runtime_session_id(self) -> str:
        return self._session_id

    @property
    def active_binding(self) -> CycleTrackBinding | None:
        return self._active

    def _current(self, binding: CycleTrackBinding) -> bool:
        return (self._tracker._track_id == binding.track_id
                and self._tracker._state not in {TrackState.IDLE, TrackState.LOST})

    def bind(self, cycle_id: str, track_id: int) -> CycleTrackBinding:
        """Explicit registration, never infer a cycle or allocate a vision track."""
        proposed = CycleTrackBinding(self._session_id, cycle_id, track_id)
        if cycle_id in self._retired_cycles:
            raise ValueError('CYCLE_ALREADY_RETIRED')
        if self._active is not None:
            if self._active.cycle_id == cycle_id and self._active.track_id != track_id:
                raise ValueError('CYCLE_ALREADY_BOUND')
            if self._active.track_id == track_id and self._active.cycle_id != cycle_id:
                raise ValueError('TRACK_ALREADY_BOUND')
            if self._active != proposed:
                raise ValueError('ACTIVE_BINDING_EXISTS')
        if not self._current(proposed):
            raise ValueError('TRACK_NOT_CURRENT')
        self._active = proposed
        return proposed

    def _identity_error(self, evidence: BoundClearanceEvidence) -> str | None:
        # Stable precedence: old sessions first, retired cycles before active match.
        if evidence.runtime_session_id != self._session_id:
            return 'SESSION_MISMATCH'
        if evidence.cycle_id in self._retired_cycles:
            return 'CYCLE_ALREADY_RETIRED'
        if self._active is None:
            return 'NO_ACTIVE_BINDING'
        if evidence.cycle_id != self._active.cycle_id:
            return 'CYCLE_MISMATCH'
        if evidence.track_id != self._active.track_id or not self._current(self._active):
            return 'TRACK_MISMATCH'
        if evidence.evidence_id in self._evidence_ids:
            return 'EVIDENCE_ID_REPLAY'
        authority = evidence.clearance_evidence
        epoch = self._source_epochs.get(authority.source)
        if epoch is not None and epoch != evidence.source_epoch:
            return 'SOURCE_EPOCH_MISMATCH'
        key = (authority.source, authority.authority_id, evidence.source_epoch)
        previous = self._source_sequences.get(key)
        if previous is not None:
            if evidence.source_sequence == previous:
                return 'SOURCE_SEQUENCE_REPLAY'
            if evidence.source_sequence < previous:
                return 'SOURCE_SEQUENCE_REGRESSION'
        return None

    def _consume(self, evidence: BoundClearanceEvidence) -> None:
        # Consume at delegation attempt, even if H4 holds/rejects or raises.
        # Never retry the same event later under more favorable physical semantics.
        authority = evidence.clearance_evidence
        self._evidence_ids.add(evidence.evidence_id)
        self._source_epochs[authority.source] = evidence.source_epoch
        key = (authority.source, authority.authority_id, evidence.source_epoch)
        self._source_sequences[key] = evidence.source_sequence

    def _retire(self) -> None:
        self._retired_cycles.add(self._active.cycle_id)
        self._active = None
        # Epoch/sequence are bound-source state; IDs and retired cycles last session.
        self._source_epochs.clear()
        self._source_sequences.clear()

    def route(self, frame_id: str, sequence: int, monotonic_s: float,
              provider_result: ProviderResult,
              evidence: BoundClearanceEvidence | None = None) -> BoundGatewayResult:
        """Validate identity, consume once, delegate H4 and observe retirement.

        Without evidence, delegate unchanged H4 (including unbound bootstrap).
        Structural/provider/order exceptions propagate, never become success.
        Identity rejection changes neither registry nor H4/G state.
        """
        if evidence is not None and type(evidence) is not BoundClearanceEvidence:
            raise TypeError('BoundClearanceEvidence or None required')
        binding = self._active
        before = self._tracker._state
        error = self._identity_error(evidence) if evidence is not None else None
        if error is None and binding is not None and not self._current(binding):
            error = 'TRACK_MISMATCH'
        if error is not None:
            return BoundGatewayResult(binding, evidence, error, 'REJECTED_IDENTITY',
                                      False, None, before, before, False, error)
        if evidence is not None:
            self._consume(evidence)
        result = self._bridge.route(frame_id, sequence, monotonic_s, provider_result,
                                    evidence.clearance_evidence if evidence else None)
        retired = binding is not None and (
            result.tracker_state_after == TrackState.LOST
            or (before == TrackState.CLEARING and result.tracker_state_after == TrackState.IDLE))
        if retired:
            self._retire()
        return BoundGatewayResult(binding, evidence,
            'VALID' if evidence is not None else 'NOT_PROVIDED',
            result.bridge_disposition.value, True, result, before,
            result.tracker_state_after, retired, result.reason)
