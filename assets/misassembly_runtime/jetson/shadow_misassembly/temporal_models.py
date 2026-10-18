"""Same frozen classifiers with opt-in, explicitly identified sequence input."""
from live import ShadowModels
from temporal_preprocessing import TemporalShadowPreprocessor


class TemporalShadowModels(ShadowModels):
    def __init__(self):
        super().__init__(robustness=True)
        self.processor = TemporalShadowPreprocessor(self.processor)

    def process(self, image, context=None):
        self.processor.context = context
        return super().process(image)
