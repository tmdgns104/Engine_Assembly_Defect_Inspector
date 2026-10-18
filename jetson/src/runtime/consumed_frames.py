"""Bounded observations at the Runtime consumer, not HTTP preview samples.

No image/tensor copies, disk writes or inference. The Runtime lock owns writes;
the read-only diagnostic route snapshots the same lock before copying records.
"""
from src import config as parameters
from collections import deque
from copy import deepcopy


class ConsumedFrames:
    def __init__(self):
        self.frames = deque(maxlen=1024)
        self.total = 0
        self.last_identity = None
        self.last_sequence = None
        self.checkpoints = deque(maxlen=4)

    def record(self, packet, *, consumed_at, outcome=None, passage=None, token=None, passage_state=None):
        identity = (packet.get('camera_epoch'), packet.get('generation'))
        sequence = packet.get('sequence')
        gap = (sequence-self.last_sequence if identity == self.last_identity
               and type(sequence) is int and type(self.last_sequence) is int else None)
        provider = packet.get('provider') or {}
        self.frames.append(dict(frame_id=packet.get('frame_id'), sequence=sequence,
            camera_epoch=identity[0], generation=identity[1],
            source_monotonic=packet.get('monotonic_s'),
            processed_monotonic=packet.get('processed_monotonic'), consumed_monotonic=consumed_at,
            sequence_delta=gap, valid=packet.get('integrity', {}).get('valid'),
            width=packet.get('width'), height=packet.get('height'), package_sha256=packet.get('package_sha256'),
            provider_status=provider.get('status'),
            boxes=[dict(o.get('bbox') or {}) for o in provider.get('observations', [])[:8]],
            outcome=outcome, passage=passage, request_token=token, passage_state=deepcopy(passage_state)))
        self.total += 1
        self.last_identity, self.last_sequence = identity, sequence

    def checkpoint(self, reason, context):
        # Freeze the first failure's lead-in before the live ring overwrites it.
        # Bounded memory only; no synchronous disk work on the health thread.
        self.checkpoints.append(dict(reason=reason, context=deepcopy(context),
            frames=deepcopy(list(self.frames)[-128:])))

    def capture(self, limit=parameters.CONSUMED_FRAME_LIMIT, *, include_checkpoints=False):
        # Call under the owner's lock. Records are append-only after creation,
        # so these references remain stable after the lock is released.
        return dict(source='RUNTIME_CONSUMED', total=self.total, capacity=1024,
            retained=len(self.frames), overwritten=max(0, self.total-1024),
            sequence_gaps_are_exit_evidence=False,
            frames=list(self.frames)[-max(1, min(1024, limit)):],
            checkpoints=list(self.checkpoints) if include_checkpoints else [])

    @staticmethod
    def copy_snapshot(captured):
        return deepcopy(captured)

    def snapshot(self, limit=parameters.CONSUMED_FRAME_LIMIT, *, include_checkpoints=False):
        return self.copy_snapshot(self.capture(limit, include_checkpoints=include_checkpoints))
