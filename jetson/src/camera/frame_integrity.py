"""알려진 광폭 수평 줄무늬 손상을 거절한다. 모든 손상 검출을 보증하지 않는다."""
import numpy as np


def inspect_integrity(image):
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        return {'valid': False, 'reason': 'INVALID_BGR_FRAME', 'horizontal_discontinuities': None}
    if min(image.shape[:2]) < 2:
        return {'valid': False, 'reason': 'EMPTY_FRAME', 'horizontal_discontinuities': None}
    differences = np.abs(np.diff(image.astype(np.int16), axis=0)).mean(axis=2)
    broad_lines = int(((differences > 30).mean(axis=1) > .65).sum())
    # 정상 경계선 한두 개를 손상으로 간주하지 않는다. 기존 손상 원본은 16줄이다.
    valid = broad_lines < 6
    return {'valid': valid, 'reason': None if valid else 'BROAD_HORIZONTAL_CORRUPTION',
            'horizontal_discontinuities': broad_lines, 'detector': 'KNOWN_STRIPE_PATTERN_V1'}
