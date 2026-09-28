"""Opaque process-session identities around the unchanged clearance contract."""
from dataclasses import asdict, dataclass

from .clearance import ClearanceEvidence, VisionExitEvidence, VisionAbsenceEvidence, AreaClearEvidence


def _nonblank(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonblank opaque string')


@dataclass(frozen=True, slots=True)
class CycleTrackBinding:
    runtime_session_id: str
    cycle_id: str
    track_id: int

    def __post_init__(self):
        _nonblank(self.runtime_session_id, 'runtime_session_id')
        _nonblank(self.cycle_id, 'cycle_id')
        if type(self.track_id) is not int or self.track_id <= 0:
            raise ValueError('track_id must be a positive integer')

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BoundClearanceEvidence:
    runtime_session_id: str
    cycle_id: str
    track_id: int
    evidence_id: str
    source_epoch: str
    source_sequence: int
    clearance_evidence: ClearanceEvidence

    def __post_init__(self):
        CycleTrackBinding(self.runtime_session_id, self.cycle_id, self.track_id)
        _nonblank(self.evidence_id, 'evidence_id')
        _nonblank(self.source_epoch, 'source_epoch')
        if type(self.source_sequence) is not int or self.source_sequence < 0:
            raise ValueError('source_sequence must be a nonnegative integer')
        if type(self.clearance_evidence) not in (ClearanceEvidence, VisionExitEvidence, VisionAbsenceEvidence, AreaClearEvidence):
            raise TypeError('unchanged ClearanceEvidence required')
        if type(self.clearance_evidence) in (VisionExitEvidence,VisionAbsenceEvidence,AreaClearEvidence) and self.source_sequence != self.clearance_evidence.empty_sequences[-1]:
            raise ValueError('VISION_EXIT_SEQUENCE_MISMATCH')

    def to_dict(self) -> dict:
        return asdict(self)
