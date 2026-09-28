"""Fixed-reference foreground with conservative, explicit geometry checks.

No component has semantic identity. In particular, a merged foreign/product blob
can pass permissive geometry. This is not a hand classifier or clearance sensor.
"""
from dataclasses import dataclass

import cv2
import numpy as np

from src.tracking.contracts import NormalizedBox, ProductObservation
from .contracts import (
    AmbiguityReason, AuthorizedEmptyReference, ComponentEvidence, ProviderResult,
    ProviderStatus, StaticReferenceConfig, validate_bgr,
)


def _corridor_relation(box: NormalizedBox, corridor: NormalizedBox) -> str:
    if (box.x2 <= corridor.x1 or box.x1 >= corridor.x2
            or box.y2 <= corridor.y1 or box.y1 >= corridor.y2):
        return 'OUTSIDE'
    if (box.x1 >= corridor.x1 and box.x2 <= corridor.x2
            and box.y1 >= corridor.y1 and box.y2 <= corridor.y2):
        return 'INSIDE'
    return 'OVERLAP'


@dataclass(frozen=True, slots=True)
class StaticReferenceProvider:
    """Own a fixed authorized reference/config; observe has no temporal state.

    Component bounds use exclusive right/bottom pixel edges normalized by image
    width/height. Wholly outside components cannot resolve an inside ambiguity.
    """
    reference: AuthorizedEmptyReference
    config: StaticReferenceConfig

    def __post_init__(self):
        if type(self.reference) is not AuthorizedEmptyReference:
            raise TypeError('explicit AuthorizedEmptyReference required')
        if type(self.config) is not StaticReferenceConfig:
            raise TypeError('explicit StaticReferenceConfig required')
        height, width, _ = self.reference.shape
        if max(self.config.open_kernel, self.config.close_kernel) > min(height, width):
            raise ValueError('morphology kernel exceeds reference dimensions')
        if self.config.min_component_area_px > height * width:
            raise ValueError('minimum component area exceeds reference area')

    def observe(self, frame: np.ndarray) -> ProviderResult:
        validate_bgr(frame)
        if frame.shape != self.reference.shape:
            raise ValueError('frame/reference shape mismatch')
        height, width, _ = frame.shape
        difference = cv2.absdiff(frame, self.reference.image).max(axis=2)
        mask = (difference > self.config.absdiff_threshold).astype(np.uint8) * 255
        threshold_pixels = int(np.count_nonzero(mask))
        for operation, size in ((cv2.MORPH_OPEN, self.config.open_kernel),
                                (cv2.MORPH_CLOSE, self.config.close_kernel)):
            mask = cv2.morphologyEx(mask, operation, np.ones((size, size), np.uint8))
        foreground_pixels = int(np.count_nonzero(mask))
        count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        components = []
        for x, y, w, h, area in stats[1:]:
            if area < self.config.min_component_area_px:
                continue
            box = NormalizedBox(int(x) / width, int(y) / height,
                                int(x + w) / width, int(y + h) / height)
            components.append(ComponentEvidence(box, int(area), _corridor_relation(box, self.config.corridor)))
        # Explicit spatial ordering, independent of component-label allocation.
        components.sort(key=lambda c: (c.bbox.y1, c.bbox.x1, c.bbox.y2, c.bbox.x2, c.area_pixels))
        evidence = tuple(components)

        def result(status, reason=None, observations=()):
            return ProviderResult(observations, status, reason, threshold_pixels,
                                  foreground_pixels, int(count - 1), evidence)

        def ambiguous(reason):
            return result(ProviderStatus.AMBIGUOUS_FOREGROUND, reason)

        if foreground_pixels == 0:
            return result(ProviderStatus.NO_FOREGROUND)
        if not components:
            return ambiguous(AmbiguityReason.NO_USABLE_PRODUCT_ENVELOPE)
        intersecting = [component for component in components if component.corridor_relation != 'OUTSIDE']
        if len(intersecting) > 1:
            return ambiguous(AmbiguityReason.MULTIPLE_FOREGROUND_COMPONENTS)
        if not intersecting or intersecting[0].corridor_relation != 'INSIDE':
            return ambiguous(AmbiguityReason.FOREGROUND_OUTSIDE_PRODUCT_CORRIDOR)
        box = intersecting[0].bbox
        if box.width * box.height > self.config.max_normalized_bbox_area:
            return ambiguous(AmbiguityReason.MERGED_FOREGROUND_ENVELOPE)
        observation = ProductObservation(box, 'STATIC_REFERENCE_FOREGROUND_V1')
        return result(ProviderStatus.PRODUCT_OBSERVED, observations=(observation,))
