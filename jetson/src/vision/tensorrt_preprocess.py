"""CPU-only static640 letterbox; integer padding is retained for inverse geometry."""
from dataclasses import dataclass

import cv2
import numpy as np

from src.contracts import DetectorError


@dataclass(frozen=True)
class ImageTransform:
    original_shape: tuple[int, int]
    resized_shape: tuple[int, int]
    gain: float
    padding: tuple[int, int, int, int]  # left, top, right, bottom


def preprocess(image, dtype="float32"):
    """Return contiguous batch1 RGB /255 and the exact resize/padding geometry.

    The selected contract uses auto=False, scale_fill=False, scaleup=True,
    centered padding114 and linear interpolation. Other policies fail at package validation.
    """
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
            or image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) <= 0
            or dtype not in ("float32", "float16")):
        raise DetectorError("INPUT_CONTRACT_MISMATCH: uint8 HWC BGR and declared float dtype required")
    height, width = image.shape[:2]
    gain = min(640 / height, 640 / width)
    resized_width, resized_height = round(width * gain), round(height * gain)
    if min(resized_width, resized_height) <= 0:
        raise DetectorError("INPUT_CONTRACT_MISMATCH: unrepresentable aspect ratio")
    half_x, half_y = (640 - resized_width) / 2, (640 - resized_height) / 2
    left, right = round(half_x - .1), round(half_x + .1)
    top, bottom = round(half_y - .1), round(half_y + .1)
    resized = image if (height, width) == (resized_height, resized_width) else cv2.resize(
        image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right,
                               cv2.BORDER_CONSTANT, value=(114, 114, 114))
    tensor = np.ascontiguousarray(padded[:, :, ::-1].transpose(2, 0, 1)[None], dtype=dtype)
    tensor /= 255
    return tensor, ImageTransform((height, width), (resized_height, resized_width),
                                  gain, (left, top, right, bottom))
