"""Product-independent tracking contracts; no device or model dependencies."""

from .contracts import (
    InspectionWindow, InspectionWindowEvent, NormalizedBox, ProductObservation,
    SingleActiveTrackerConfig, TrackingError, TrackingFrame, TrackingReason,
    TrackingUpdate, TrackState, WindowRelation,
)
from .single_active import SingleActiveTracker

__all__ = [
    'InspectionWindow', 'InspectionWindowEvent', 'NormalizedBox', 'ProductObservation',
    'SingleActiveTracker', 'SingleActiveTrackerConfig', 'TrackingError', 'TrackingFrame',
    'TrackingReason', 'TrackingUpdate', 'TrackState', 'WindowRelation',
]
