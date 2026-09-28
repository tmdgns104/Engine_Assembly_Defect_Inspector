"""실제 하단 진행 이력과 정상 빈 프레임에 한정된 영상 추정 이탈 정책."""
import math


class VisionExitPolicy:
    def __init__(self, *, exit_y, min_empty_frames, min_empty_seconds, max_frame_gap):
        if not 0 < exit_y < 1 or min_empty_frames < 2 or min_empty_seconds <= 0 or max_frame_gap <= 0:
            raise ValueError('영상 이탈 정책의 영역/시간/개수를 확인하세요')
        self.exit_y = exit_y
        self.min_empty_frames = min_empty_frames
        self.min_empty_seconds = min_empty_seconds
        self.max_frame_gap = max_frame_gap
        self.reset()

    def reset(self):
        self.sequence = None
        self.time = None
        self.last_center = None
        self.exit_observation = None
        self.empty_start = None
        self.empty_sequences = []

    def update(self, sequence, monotonic_s, bbox, healthy):
        if not math.isfinite(monotonic_s) or (self.sequence is not None and
                (sequence <= self.sequence or monotonic_s <= self.time)):
            raise ValueError('이탈 증거의 순서/시간이 역행했습니다')
        gap = self.time is not None and monotonic_s - self.time > self.max_frame_gap
        self.sequence, self.time = sequence, monotonic_s
        if gap:
            self.last_center = None
            self.exit_observation = None
        if not healthy or bbox is not None or gap:
            self.empty_start = None
            self.empty_sequences = []
        if not healthy:
            return None
        if bbox is not None:
            center = (bbox[1] + bbox[3]) / 2
            forward = self.last_center is not None and center > self.last_center
            if center < self.exit_y:
                self.exit_observation = None
            elif forward and bbox[3] >= .95:
                self.exit_observation = {'sequence': sequence, 'monotonic_s': monotonic_s, 'bbox': list(bbox)}
            elif self.last_center is not None and center < self.last_center:
                self.exit_observation = None
            self.last_center = center
            return None
        if self.exit_observation is None:
            return None
        if self.empty_start is None:
            self.empty_start = monotonic_s
        self.empty_sequences.append(sequence)
        if len(self.empty_sequences) < self.min_empty_frames or monotonic_s - self.empty_start + 1e-9 < self.min_empty_seconds:
            return None
        return {'source': 'VISION_INFERRED_EXIT', 'physical_clearance_verified': False,
                'exit_observation': dict(self.exit_observation),
                'empty_sequences': list(self.empty_sequences), 'confirmed_at': monotonic_s}
