"""Opt-in static experiment with the same frozen models and independent-image path."""
from temporal_models import TemporalShadowModels
from static_geometry import StaticPoseGuard

class StaticShadowModels(TemporalShadowModels):
    def __init__(self):
        super().__init__()
        self.processor.guard=StaticPoseGuard(self.processor.cfg)
