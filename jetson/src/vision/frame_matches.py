"""Avoid repeated native matching of identical descriptors in one image.

Pose estimation and its rejection gates still run on every route. This cache
holds descriptor matches only, and its lifetime ends before the next image.
"""
from contextlib import contextmanager


class _FrameMatches:
    def __init__(self, matcher):
        self.matcher = matcher
        self.entries = {}

    @staticmethod
    def _descriptor_key(array):
        # Byte content, shape and dtype prevent stale hits after in-place edits
        # or allocation reuse. Keeping bytes also avoids hash-collision assumptions.
        return array.dtype.str, array.shape, array.tobytes()

    def _call(self, method, left, right, **kwargs):
        key = (method, tuple(kwargs.items()), self._descriptor_key(left), self._descriptor_key(right))
        if key in self.entries:
            return self.entries[key]
        result = getattr(self.matcher, method)(left, right, **kwargs)
        # The observed reference pipeline has three distinct matching queries.
        # Additional queries remain correct and are simply computed uncached.
        if len(self.entries) < 4:
            self.entries[key] = result
        return result

    def knnMatch(self, left, right, k):
        return self._call('knnMatch', left, right, k=k)

    def match(self, left, right):
        return self._call('match', left, right)


@contextmanager
def same_frame_matches(estimator):
    original = estimator.matcher
    estimator.matcher = _FrameMatches(original)
    try:
        yield
    finally:
        estimator.matcher = original
