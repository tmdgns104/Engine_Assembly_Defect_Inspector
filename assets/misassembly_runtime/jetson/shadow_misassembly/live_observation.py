"""Observe three genuinely new frames; this never calls production aggregation."""
from collections import deque


class ThreeFrameObservation:
    def __init__(self):
        self.frames = deque(maxlen=3)
        self.identity = None

    def add(self, value):
        identity = (value['camera_epoch'], value['track_id'], value.get('scenario_id'))
        if identity != self.identity:
            self.frames.clear()
            self.identity = identity
        if self.frames and (value['source_pts_ns'] <= self.frames[-1]['source_pts_ns'] or any(
                value['frame_id'] == previous['frame_id'] or
                value['raw_pixel_sha256'] == previous['raw_pixel_sha256'] for previous in self.frames)):
            return dict(state='REVIEW', reason='DUPLICATE_OR_REORDERED_FRAME', frames=list(self.frames))
        self.frames.append({key: value[key] for key in (
            'frame_id', 'source_pts_ns', 'track_id', 'raw_pixel_sha256', 'shadow_state', 'parts')})
        if len(self.frames) < 3:
            state, reason = 'REVIEW', 'WAITING_FOR_THREE_NEW_FRAMES'
        elif any(frame['shadow_state'] == 'ERROR' for frame in self.frames):
            state, reason = 'ERROR', 'FRAME_RUNTIME_ERROR'
        elif len({frame['shadow_state'] for frame in self.frames}) != 1 or any(
                frame['parts'] != self.frames[0]['parts'] for frame in self.frames):
            state, reason = 'REVIEW', 'FRAME_STATE_CONFLICT'
        else:
            state, reason = self.frames[0]['shadow_state'], 'THREE_STATE_OBSERVATIONS_AGREE'
        return dict(state=state, reason=reason, frames=list(self.frames))
