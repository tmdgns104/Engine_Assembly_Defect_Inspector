"""Deterministic one-product lifecycle. Caller supplies ordered envelope observations.

This class owns no camera, inspection execution, clock, database or physical output.
It must be called serially. LOST reset policy belongs to a future integration layer.
"""

from .contracts import (
    InspectionWindowEvent, NormalizedBox, SingleActiveTrackerConfig,
    TrackingError, TrackingFrame, TrackingReason, TrackingUpdate,
    TrackState, WindowRelation, require_integer, require_text,
)
import math


class SingleActiveTracker:
    def __init__(self, config: SingleActiveTrackerConfig):
        if type(config) is not SingleActiveTrackerConfig:
            raise TypeError('config must be SingleActiveTrackerConfig')
        self.config = config
        self._generation = 0
        self._last_frame = None
        self._used_inspection_ids: set[str] = set()
        self._clear_active()

    def _clear_active(self) -> None:
        self._state = TrackState.IDLE
        self._track_id = None
        self._inspection_id = None
        self._last_center = None
        self._last_cross = None
        self._last_observed_s = None
        self._pending_downstream = False
        self._relation = None
        self._reason = None
        self._missed = 0
        self._clear_count = 0
        self._zone_count = 0
        self._zone_inside = False
        self._last_box = None
        self._pre_ambiguity_state = None

    def _update(self, event: InspectionWindowEvent | None = None) -> TrackingUpdate:
        frame = self._last_frame
        return TrackingUpdate(
            frame.frame_id, frame.sequence, self._state, self._track_id, event,
            self._reason, self._missed, self._relation, self._inspection_id,
            self._clear_count,
        )

    def _lose(self, reason: TrackingReason) -> TrackingUpdate:
        if (reason == TrackingReason.AMBIGUOUS_ACTIVE_OBSERVATIONS and
                self._inspection_id is None and
                self._state in (TrackState.TRACKING, TrackState.INSPECTION_READY)):
            self._pre_ambiguity_state = self._state
        self._state = TrackState.WAIT_AREA_CLEAR if self.config.wait_area_clear else TrackState.LOST
        self._reason = reason
        return self._update()

    def wait_for_area_clear(self, reason: TrackingReason) -> None:
        """Preserve a bound identity without accepting a reappearance as that product."""
        if not self.config.wait_area_clear or self._track_id is None or self._state == TrackState.LOST:
            raise TrackingError(TrackingReason.INVALID_STATE_TRANSITION)
        if (reason == TrackingReason.AMBIGUOUS_ACTIVE_OBSERVATIONS and
                self._inspection_id is None and
                self._state in (TrackState.TRACKING, TrackState.INSPECTION_READY)):
            self._pre_ambiguity_state = self._state
        self._state = TrackState.WAIT_AREA_CLEAR
        self._reason = reason

    def resume_short_ambiguity(self, box: NormalizedBox, observed_s: float) -> bool:
        """Resume an uninspected identity after a brief, spatially matched ambiguity."""
        if (self._state != TrackState.WAIT_AREA_CLEAR or
                self._reason != TrackingReason.AMBIGUOUS_ACTIVE_OBSERVATIONS or
                self._inspection_id is not None or self._last_box is None or
                self._pre_ambiguity_state not in (TrackState.TRACKING, TrackState.INSPECTION_READY)):
            return False
        elapsed = observed_s - self._last_observed_s
        if not 0 <= elapsed <= .5:
            return False
        previous = self._last_box
        distance = math.hypot(box.center_x-previous.center_x,
                              box.center_y-previous.center_y)
        limit = self.config.max_center_step_norm
        if self.config.max_center_speed_norm_s is not None:
            limit += self.config.max_center_speed_norm_s * elapsed
        if distance > limit:
            return False
        intersection = max(0,min(previous.x2,box.x2)-max(previous.x1,box.x1))*max(
            0,min(previous.y2,box.y2)-max(previous.y1,box.y1))
        union = previous.width*previous.height+box.width*box.height-intersection
        if self.config.free_motion and union and intersection/union < .02 and distance > .12:
            return False
        self._state = self._pre_ambiguity_state
        self._pre_ambiguity_state = None
        self._reason = None
        return True

    def _position(self, box: NormalizedBox) -> tuple[float, WindowRelation | None]:
        window = self.config.inspection_window
        if self.config.free_motion:
            margin = self.config.zone_hysteresis if self._zone_inside else 0
            inside = (window.x1-margin <= box.center_x <= window.x2+margin
                      and window.y1-margin <= box.center_y <= window.y2+margin)
            self._zone_count = self._zone_count+1 if inside else 0
            self._zone_inside = inside and (self._zone_inside or self._zone_count >= self.config.zone_entry_frames)
            relation = (WindowRelation.INSIDE if self._zone_inside else
                        WindowRelation.DOWNSTREAM if self._state in (TrackState.INSPECTED,TrackState.CLEARING) else WindowRelation.UPSTREAM)
            return (box.center_x if self.config.axis == 'x' else box.center_y), relation
        if self.config.axis == 'x':
            center, cross = box.center_x, box.center_y
            low, high, cross_low, cross_high = window.x1, window.x2, window.y1, window.y2
        else:
            center, cross = box.center_y, box.center_x
            low, high, cross_low, cross_high = window.y1, window.y2, window.x1, window.x2
        if low <= center <= high:
            relation = WindowRelation.INSIDE if cross_low <= cross <= cross_high else None
        else:
            upstream = center < low if self.config.direction == 1 else center > high
            relation = WindowRelation.UPSTREAM if upstream else WindowRelation.DOWNSTREAM
        return center, relation

    def step(self, frame: TrackingFrame) -> TrackingUpdate:
        """Consume one ordered frame; exact last-frame replay emits no event."""
        if type(frame) is not TrackingFrame:
            raise TypeError('frame must be TrackingFrame')
        previous = self._last_frame
        if previous is not None:
            if frame == previous:
                return self._update()
            if frame.sequence <= previous.sequence:
                raise TrackingError(TrackingReason.FRAME_SEQUENCE_REGRESSION)
            if frame.monotonic_s < previous.monotonic_s:
                raise TrackingError(TrackingReason.FRAME_TIME_REGRESSION)
        # Invalid ordering cannot mutate lifecycle or replay history.
        self._last_frame = frame
        if self._state in (TrackState.LOST, TrackState.WAIT_AREA_CLEAR):
            return self._update()
        self._reason = None
        count = len(frame.observations)
        if count > 1:
            self._relation = None
            if self._state == TrackState.IDLE:
                self._reason = TrackingReason.AMBIGUOUS_TRACK_START
                return self._update()
            return self._lose(TrackingReason.AMBIGUOUS_ACTIVE_OBSERVATIONS)
        if count == 0:
            return self._empty_frame()

        center, relation = self._position(frame.observations[0].bbox)
        box = frame.observations[0].bbox
        cross = box.center_y if self.config.axis == 'x' else box.center_x
        self._relation = relation
        if relation is None:
            if self._state == TrackState.IDLE:
                self._reason = TrackingReason.WINDOW_CROSS_AXIS_OUTSIDE
                return self._update()
            return self._lose(TrackingReason.WINDOW_CROSS_AXIS_OUTSIDE)
        if self._state == TrackState.IDLE:
            if relation == WindowRelation.DOWNSTREAM:
                self._reason = TrackingReason.DOWNSTREAM_WITHOUT_ACTIVE_TRACK
                return self._update()
            self._generation += 1
            self._track_id = self._generation
            self._state = TrackState.TRACKING
        else:
            step = center - self._last_center
            forward_step = step * self.config.direction
            elapsed = frame.monotonic_s - self._last_observed_s
            if self.config.max_unobserved_seconds is not None and elapsed > self.config.max_unobserved_seconds:
                return self._lose(TrackingReason.MISSED_OBSERVATION_LIMIT)
            limit = self.config.max_center_step_norm
            distance = math.hypot(step,cross-self._last_cross) if self.config.free_motion else abs(step)
            if self.config.max_center_speed_norm_s is not None:
                limit += self.config.max_center_speed_norm_s * elapsed
                distance = math.hypot(step,cross-self._last_cross)
            if (distance > limit
                    or (not self.config.free_motion and forward_step < -self.config.max_reverse_step_norm)):
                return self._lose(TrackingReason.TRACK_ASSOCIATION_INVALID)
            if self.config.free_motion and self._last_box is not None:
                old = self._last_box
                intersection = max(0,min(old.x2,box.x2)-max(old.x1,box.x1))*max(0,min(old.y2,box.y2)-max(old.y1,box.y1))
                union = old.width*old.height+box.width*box.height-intersection
                iou = intersection/union if union else 0
                if iou < .02 and distance > .12:
                    return self._lose(TrackingReason.TRACK_ASSOCIATION_INVALID)
        self._last_box = box
        self._last_center = center
        self._last_cross = cross
        self._last_observed_s = frame.monotonic_s
        self._missed = 0
        self._clear_count = 0

        if self._state == TrackState.TRACKING:
            if relation == WindowRelation.DOWNSTREAM:
                return self._lose(TrackingReason.MISSED_INSPECTION_WINDOW)
            if relation == WindowRelation.INSIDE:
                self._state = TrackState.INSPECTION_READY
                event = InspectionWindowEvent(self._track_id, frame.frame_id,
                                              frame.sequence, frame.monotonic_s)
                return self._update(event)
        elif self._state == TrackState.INSPECTION_READY and relation == WindowRelation.DOWNSTREAM:
            if not self.config.allow_pending_downstream:
                return self._lose(TrackingReason.MISSED_INSPECTION_COMPLETION)
            self._pending_downstream = True
        elif self._state == TrackState.INSPECTED and relation == WindowRelation.DOWNSTREAM:
            self._state = TrackState.CLEARING
        # CLEARING retains identity even if a permitted jitter re-enters the window.
        return self._update()

    def _empty_frame(self) -> TrackingUpdate:
        self._relation = None
        self._zone_count = 0
        if self._state == TrackState.IDLE:
            return self._update()
        if self._state == TrackState.CLEARING:
            self._clear_count += 1
            if self._clear_count >= self.config.clear_frames:
                self._clear_active()
            return self._update()
        self._missed += 1
        expired = (self._last_frame.monotonic_s - self._last_observed_s > self.config.max_unobserved_seconds
                   if self.config.max_unobserved_seconds is not None else self._missed > self.config.max_missed_frames)
        if expired:
            return self._lose(TrackingReason.MISSED_OBSERVATION_LIMIT)
        return self._update()

    def prepare_visual_clearance(self, track_id: int) -> None:
        """Caller has bounded healthy absence evidence; retirement still goes through H5."""
        if not self.config.free_motion or track_id != self._track_id or self._state in (TrackState.IDLE,TrackState.LOST):
            raise TrackingError(TrackingReason.INVALID_STATE_TRANSITION)
        self._state = TrackState.CLEARING

    def mark_inspected(self, track_id: int, inspection_id: str) -> TrackingUpdate:
        """Attach a process-unique completion reference, never inspection truth."""
        require_integer(track_id, 'track_id', 1)
        require_text(inspection_id, 'inspection_id')
        if track_id != self._track_id:
            raise TrackingError(TrackingReason.TRACK_ID_MISMATCH)
        if inspection_id in self._used_inspection_ids:
            raise TrackingError(TrackingReason.INSPECTION_ALREADY_ATTACHED)
        if self._state not in (TrackState.INSPECTION_READY, TrackState.WAIT_AREA_CLEAR):
            raise TrackingError(TrackingReason.INVALID_STATE_TRANSITION)
        self._used_inspection_ids.add(inspection_id)
        self._inspection_id = inspection_id
        if self._state != TrackState.WAIT_AREA_CLEAR:
            self._state = TrackState.CLEARING if self._pending_downstream else TrackState.INSPECTED
        return self._update()

    def reset_lost(self) -> TrackingUpdate:
        """Explicit reset; keep process identity counter and accepted frame order."""
        if self._state != TrackState.LOST:
            raise TrackingError(TrackingReason.INVALID_STATE_TRANSITION)
        self._clear_active()
        return self._update()
