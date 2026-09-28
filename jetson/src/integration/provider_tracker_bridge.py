"""Route provider evidence without conflating ambiguity with physical clearance."""
from dataclasses import asdict, dataclass
from enum import Enum

from src.observation.contracts import ProviderResult, ProviderStatus
from src.tracking.contracts import TrackingFrame, TrackingUpdate, TrackState
from src.tracking.single_active import SingleActiveTracker
from .clearance import ClearanceEvidence, VisionExitEvidence, VisionAbsenceEvidence, AreaClearEvidence


class BridgeDisposition(str, Enum):
    FORWARDED_PRODUCT = 'FORWARDED_PRODUCT'
    FORWARDED_MISS = 'FORWARDED_MISS'
    FORWARDED_CONFIRMED_CLEAR = 'FORWARDED_CONFIRMED_CLEAR'
    FORWARDED_VISION_INFERRED_EXIT = 'FORWARDED_VISION_INFERRED_EXIT'
    CLEARANCE_HELD_NO_AUTHORITY = 'CLEARANCE_HELD_NO_AUTHORITY'
    CLEARANCE_HELD_AMBIGUOUS = 'CLEARANCE_HELD_AMBIGUOUS'
    CLEARANCE_EVIDENCE_CONFLICT = 'CLEARANCE_EVIDENCE_CONFLICT'
    CLEARANCE_EVIDENCE_NOT_APPLICABLE = 'CLEARANCE_EVIDENCE_NOT_APPLICABLE'


@dataclass(frozen=True, slots=True)
class BridgeResult:
    frame_id: str
    sequence: int
    monotonic_s: float
    provider_status: ProviderStatus
    bridge_disposition: BridgeDisposition
    tracker_called: bool
    tracker_state_before: TrackState
    tracker_state_after: TrackState
    tracker_update: TrackingUpdate | None
    clearance_authority_used: ClearanceEvidence | None
    reason: str | None

    def to_dict(self) -> dict:
        return {
            'frame_id': self.frame_id, 'sequence': self.sequence, 'monotonic_s': self.monotonic_s,
            'provider_status': self.provider_status.value,
            'bridge_disposition': self.bridge_disposition.value,
            'tracker_called': self.tracker_called,
            'tracker_state_before': self.tracker_state_before.value,
            'tracker_state_after': self.tracker_state_after.value,
            'tracker_update': self.tracker_update.to_dict() if self.tracker_update else None,
            'clearance_authority_used': asdict(self.clearance_authority_used) if self.clearance_authority_used else None,
            'reason': self.reason,
        }


@dataclass(frozen=True, slots=True)
class ProviderTrackerBridge:
    """Use one caller-owned tracker. All access must be serial, including caller operations.

    Frozen G has no public state accessor: read `_state` only, never mutate it.
    This narrow version-coupling is covered by the parent SHA and impacted tests.
    No mirrored lifecycle is cached; caller mark_inspected/reset is immediately
    visible. HOLD leaves G's order and counters completely untouched.
    """
    tracker: SingleActiveTracker

    def __post_init__(self):
        if type(self.tracker) is not SingleActiveTracker:
            raise TypeError('caller-owned accepted SingleActiveTracker required')

    def route(self, frame_id: str, sequence: int, monotonic_s: float,
              provider_result: ProviderResult,
              clearance: ClearanceEvidence | None = None) -> BridgeResult:
        """Validate metadata, route once or hold; propagate existing G ordering errors.

        Metadata is caller supplied: no clock, fabricated observation or frame.
        Held frames are not G observations and do not advance its ordering history.
        """
        if type(provider_result) is not ProviderResult:
            raise TypeError('existing H3 ProviderResult required')
        if clearance is not None and type(clearance) not in (ClearanceEvidence, VisionExitEvidence, VisionAbsenceEvidence, AreaClearEvidence):
            raise TypeError('clearance must be explicit ClearanceEvidence or None')
        if provider_result.clear_authority is not False:
            raise ValueError('H3 provider cannot carry clearance authority')
        frame = TrackingFrame(frame_id, sequence, monotonic_s, provider_result.observations)
        status = provider_result.status
        before = self.tracker._state
        vision_exit = type(clearance) in (VisionExitEvidence,VisionAbsenceEvidence,AreaClearEvidence)
        if vision_exit and (clearance.empty_sequences[-1] != sequence or clearance.confirmed_monotonic != monotonic_s):
            raise ValueError('VISION_EXIT_FRAME_MISMATCH')
        confirmed = vision_exit or (clearance is not None and clearance.confirmed_clear)
        reason = provider_result.reason.value if provider_result.reason else None

        def held(disposition, explanation):
            return BridgeResult(frame_id, sequence, monotonic_s, status, disposition,
                                False, before, before, None, None, explanation)

        # Contradictory product/clear evidence takes precedence in every state.
        if status == ProviderStatus.PRODUCT_OBSERVED and confirmed:
            return held(BridgeDisposition.CLEARANCE_EVIDENCE_CONFLICT,
                        'PRODUCT_OBSERVATION_CONTRADICTS_CLEARANCE')
        # Strict V1 rejects inapplicable authority without any lifecycle mutation.
        if confirmed and before != TrackState.CLEARING:
            return held(BridgeDisposition.CLEARANCE_EVIDENCE_NOT_APPLICABLE,
                        'CONFIRMED_CLEAR_ONLY_APPLIES_IN_CLEARING')
        used_authority = None
        if status == ProviderStatus.PRODUCT_OBSERVED:
            if len(frame.observations) != 1:
                raise ValueError('PRODUCT_OBSERVED requires exactly one observation')
            disposition = BridgeDisposition.FORWARDED_PRODUCT
        elif before == TrackState.CLEARING:
            if status == ProviderStatus.AMBIGUOUS_FOREGROUND:
                return held(BridgeDisposition.CLEARANCE_HELD_AMBIGUOUS, reason)
            if not confirmed:
                return held(BridgeDisposition.CLEARANCE_HELD_NO_AUTHORITY,
                            'NO_CONFIRMED_CLEARANCE')
            disposition = (BridgeDisposition.FORWARDED_VISION_INFERRED_EXIT if vision_exit
                           else BridgeDisposition.FORWARDED_CONFIRMED_CLEAR)
            used_authority = clearance
        else:
            disposition = BridgeDisposition.FORWARDED_MISS
        update = self.tracker.step(frame)
        return BridgeResult(frame_id, sequence, monotonic_s, status, disposition,
                            True, before, update.state, update, used_authority, reason)
