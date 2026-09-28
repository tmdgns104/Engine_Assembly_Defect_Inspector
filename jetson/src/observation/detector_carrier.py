"""패키지가 지정한 독립 본체 클래스만 제품 관측으로 변환한다."""
from src.observation.contracts import ProviderResult, ProviderStatus, AmbiguityReason
from src.tracking.contracts import NormalizedBox, ProductObservation


def observe_carrier(detections, width, height, profile):
    if width <= 0 or height <= 0:
        raise ValueError('관측 영상 크기가 유효하지 않습니다')
    candidates = [d for d in detections if d['class_name'] == profile['carrier_class']]
    accepted = [d for d in candidates if d['confidence'] >= profile['carrier_confidence']]
    observations = ()
    reason = None
    if not candidates:
        status = ProviderStatus.NO_FOREGROUND
    elif len(candidates) != 1 or len(accepted) != 1:
        status = ProviderStatus.AMBIGUOUS_FOREGROUND
        reason = (AmbiguityReason.MULTIPLE_FOREGROUND_COMPONENTS if len(candidates) > 1
                  else AmbiguityReason.NO_USABLE_PRODUCT_ENVELOPE)
    else:
        box = accepted[0]['bounding_box']
        bbox = NormalizedBox(box['x1']/width, box['y1']/height, box['x2']/width, box['y2']/height)
        if bbox.width <= 0 or bbox.height <= 0:
            raise ValueError('제품 본체 관측 면적이 없습니다')
        observations = (ProductObservation(bbox, 'PACKAGE_CARRIER_DETECTOR'),)
        status = ProviderStatus.PRODUCT_OBSERVED
    return ProviderResult(observations, status, reason, 0, 0, len(candidates), ())
