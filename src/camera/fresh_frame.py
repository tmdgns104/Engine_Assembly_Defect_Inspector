"""Local monotonic trigger/frame contract. No camera, model, or I/O ownership."""

from collections import Counter
from dataclasses import asdict, dataclass
import math


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


@dataclass(frozen=True)
class TriggerContext:
    trigger_id: str
    cell_id: str
    plc_session_id: int
    cycle_id: int
    request_id: int
    trigger_received_monotonic: float
    trigger_source: str
    capture_epoch: str
    deadline_monotonic: float

    def __post_init__(self):
        for value in (self.trigger_id, self.cell_id, self.capture_epoch):
            if not isinstance(value, str) or not value.strip():
                raise ValueError('TRIGGER_METADATA_INVALID')
        for value in (self.plc_session_id, self.cycle_id, self.request_id):
            if type(value) is not int or not 1 <= value <= 4294967295:
                raise ValueError('TRIGGER_METADATA_INVALID')
        start, end = self.trigger_received_monotonic, self.deadline_monotonic
        if not finite_number(start) or not finite_number(end) or not 0 <= start < end:
            raise ValueError('TRIGGER_METADATA_INVALID')
        if self.trigger_source not in ('MOCK', 'LOCAL_TEST'):
            raise ValueError('TRIGGER_SOURCE_UNSUPPORTED')

    def to_dict(self):
        return asdict(self)


class FreshFrameError(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class FreshFrameSelector:
    """Fail closed within one trigger; retain bounded rejection metadata only.

    Accepted source time is strictly after t0 + epsilon. The two lab windows
    cap both selection time and source time, so inference delays cannot cause
    an unbounded wait for a later product. They do not prove product identity.
    """

    def __init__(self, trigger, config, max_age_seconds, spacing_seconds=0):
        self.trigger = trigger
        self.max_age_seconds = max_age_seconds
        self.spacing_seconds = spacing_seconds
        epsilon_ms = config['boundary_epsilon_ms']
        windows = [config['max_trigger_to_frame_ms'], config['inspection_window_ms']]
        if (any(not finite_number(v) or v <= 0 for v in windows)
                or not finite_number(max_age_seconds) or max_age_seconds <= 0
                or not finite_number(spacing_seconds) or spacing_seconds < 0
                or not finite_number(epsilon_ms) or epsilon_ms < 0):
            raise ValueError('FRESH_FRAME_CONFIG_INVALID')
        self.epsilon_seconds = epsilon_ms / 1000
        self.deadline = min(trigger.deadline_monotonic,
                            trigger.trigger_received_monotonic + min(windows) / 1000)
        self.last_sequence = -1
        self.last_pts = -1
        self.last_frame_id = None
        self.last_selected_source = None
        self.selected = []
        self.rejected = []
        self.rejection_counts = Counter()
        self.terminal_reason = None

    def check_active(self, now, cancelled=False):
        if self.terminal_reason:
            raise FreshFrameError(self.terminal_reason)
        if cancelled:
            self.terminal_reason = 'CANCELLED'
        elif not finite_number(now) or now < self.trigger.trigger_received_monotonic:
            self.terminal_reason = 'FRAME_METADATA_INVALID'
        elif now >= self.deadline:
            self.terminal_reason = 'DEADLINE_EXCEEDED'
        if self.terminal_reason:
            raise FreshFrameError(self.terminal_reason)

    def reject(self, reason, metadata, now, fatal=False):
        self.rejection_counts[reason] += 1
        # Malformed metadata must still produce strict JSON evidence (no NaN/Infinity).
        safe = {key: value if isinstance(value, (str, bool)) or value is None or finite_number(value)
                else repr(value) for key, value in metadata.items()}
        self.rejected.append({'reason': reason, 'selected_at_monotonic': now if finite_number(now) else None,
                              'frame': safe, 'trigger_id': self.trigger.trigger_id})
        self.rejected = self.rejected[-32:]
        if fatal:
            self.terminal_reason = reason
            raise FreshFrameError(reason)
        return None

    def consider(self, metadata, now, cancelled=False):
        try:
            self.check_active(now, cancelled)
        except FreshFrameError as error:
            return self.reject(error.reason, metadata, now, fatal=True)
        required = ('frame_id', 'camera_epoch', 'received_at')
        valid = all(isinstance(metadata.get(key), str) and metadata[key] for key in required)
        valid = valid and all(type(metadata.get(key)) is int and metadata[key] >= 0
                              for key in ('sequence', 'source_pts_ns'))
        valid = valid and all(finite_number(metadata.get(key)) for key in
                              ('received_monotonic', 'estimated_source_monotonic'))
        if not valid:
            return self.reject('FRAME_METADATA_INVALID', metadata, now, fatal=True)
        source = metadata['estimated_source_monotonic']
        received = metadata['received_monotonic']
        if not 0 <= source <= received <= now:
            return self.reject('FRAME_METADATA_INVALID', metadata, now, fatal=True)
        if metadata['camera_epoch'] != self.trigger.capture_epoch:
            return self.reject('CAMERA_EPOCH_CHANGED', metadata, now, fatal=True)
        if metadata['sequence'] <= self.last_sequence or metadata['frame_id'] == self.last_frame_id:
            return self.reject('DUPLICATE_FRAME', metadata, now)
        if metadata['source_pts_ns'] < self.last_pts:
            return self.reject('PTS_REGRESSION', metadata, now, fatal=True)
        if metadata['source_pts_ns'] == self.last_pts:
            return self.reject('DUPLICATE_FRAME', metadata, now)
        self.last_sequence = metadata['sequence']
        self.last_pts = metadata['source_pts_ns']
        self.last_frame_id = metadata['frame_id']
        if source <= self.trigger.trigger_received_monotonic + self.epsilon_seconds:
            return self.reject('PRE_TRIGGER', metadata, now)
        if now - source > self.max_age_seconds:
            return self.reject('STALE', metadata, now)
        if self.last_selected_source is not None and source - self.last_selected_source < self.spacing_seconds:
            return self.reject('OBSERVATION_SPACING', metadata, now)
        decision = dict(metadata, trigger_id=self.trigger.trigger_id,
                        trigger_to_frame_ms=(source - self.trigger.trigger_received_monotonic) * 1000,
                        frame_age_at_select_ms=(now - source) * 1000,
                        selection_wait_ms=(now - self.trigger.trigger_received_monotonic) * 1000,
                        selected_at_monotonic=now, freshness_basis='GSTREAMER_PTS_MONOTONIC_ESTIMATE',
                        exposure_time_verified=False)
        self.last_selected_source = source
        self.selected.append(decision)
        return decision

    def evidence(self):
        return {'trigger': self.trigger.to_dict(), 'selected_frames': list(self.selected),
                'rejected_frames': list(self.rejected), 'rejection_counts': dict(self.rejection_counts),
                'rejection_metadata_truncated': max(0, sum(self.rejection_counts.values()) - len(self.rejected)),
                'selection_deadline_monotonic': self.deadline, 'terminal_reason': self.terminal_reason,
                'exposure_time_verified': False}
