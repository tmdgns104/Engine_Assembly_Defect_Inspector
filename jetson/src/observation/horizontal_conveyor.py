"""Horizontal texture observation, isolated-development qualification only.

Native colour, local weave energy and straight residuals are measured afresh.
No detector absence, pixel-reference matching, erosion or online learning.
A numerical appearance envelope is calibration data, not field qualification;
real-PLC admission remains blocked until separate residue/motion validation.
"""
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

MODE = 'CONVEYOR_HORIZONTAL_TEXTURE_V1'
FEATURES = ('gray', 'local_mean_9', 'local_std_9', 'saturation', 'red_minus_blue')


def validate_horizontal_config(config):
    if (config.get('mode') != MODE or config.get('schema_version') != 1
            or config.get('roi') != 'FULL_WIDTH_CALIBRATED_BELT'
            or config.get('shape') != [720, 1280, 3] or config.get('color') != 'BGR_UINT8'
            or config.get('qualification') != 'ISOLATED_ONLY' or config.get('references')
            or not isinstance(config.get('calibration_id'), str) or not config['calibration_id']):
        raise ValueError('HORIZONTAL_CONFIG_OR_QUALIFICATION_INVALID')
    for key, expected in dict(clear_seconds=1.2, clear_minimum_frames=6,
                              maximum_gap_seconds=.5, maximum_age_seconds=1.).items():
        if type(config.get(key)) not in (int, float) or config[key] != expected:
            raise ValueError('UNSUPPORTED_AREA_CONTINUITY_POLICY:' + key)
    bounds = config.get('belt_bounds')
    if not isinstance(bounds, list) or not 2 <= len(bounds) <= 16:
        raise ValueError('HORIZONTAL_BOUNDS_REQUIRED')
    previous = -1
    for row in bounds:
        if not isinstance(row, list) or len(row) != 3 or any(type(v) is not int for v in row):
            raise ValueError('HORIZONTAL_INTEGER_BOUNDS_REQUIRED')
        x, top, bottom = row
        if not (previous < x <= 1279 and 24 <= top < bottom < 696 and 256 <= bottom-top <= 672):
            raise ValueError('HORIZONTAL_BOUNDS_INVALID')
        previous = x
    if bounds[0][0] != 0 or bounds[-1][0] != 1279:
        raise ValueError('HORIZONTAL_BOTH_EXITS_REQUIRED')
    low, high = config.get('feature_low'), config.get('feature_high')
    if not all(isinstance(v, list) and len(v) == len(FEATURES) for v in (low, high)):
        raise ValueError('HORIZONTAL_FEATURE_ENVELOPE_REQUIRED')
    # Broad envelopes cannot be substituted to manufacture empty evidence.
    limits = [(0, 255), (0, 255), (0, 128), (0, 255), (-255, 255)]
    for a, b, (floor, ceiling) in zip(low, high, limits):
        if (type(a) not in (int, float) or type(b) not in (int, float)
                or not math.isfinite(a) or not math.isfinite(b) or not floor <= a < b <= ceiling):
            raise ValueError('HORIZONTAL_FEATURE_RANGE_INVALID')
    if low[2] < 2 or high[3] > 150 or high[4] > 35 or high[0] > 240:
        raise ValueError('HORIZONTAL_FEATURE_DISCRIMINATION_INSUFFICIENT')
    variance = config.get('minimum_line_variance')
    if type(variance) not in (int, float) or not math.isfinite(variance) or not 0 < variance <= 25:
        raise ValueError('HORIZONTAL_NATIVE_WEAVE_EVIDENCE_REQUIRED')
    evidence = config.get('calibration_evidence', {})
    digest = evidence.get('manifest_sha256', '')
    if (evidence.get('human_empty_confirmed') is not True
            or type(evidence.get('sample_count')) is not int or evidence['sample_count'] < 9
            or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)
            or evidence.get('scope') not in ('DEVELOPMENT_EMPTY_CALIBRATION', 'SYNTHETIC_TEST_ONLY')):
        raise ValueError('HORIZONTAL_CALIBRATION_PROVENANCE_REQUIRED')


def surface_features(image, belt):
    """Native colour plus local statistics; outside-rail pixels never enter means."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    weight = belt.astype(np.float32)
    count = cv2.boxFilter(weight, -1, (9, 9), normalize=False)
    total = cv2.boxFilter(gray*weight, -1, (9, 9), normalize=False)
    squares = cv2.boxFilter(gray*gray*weight, -1, (9, 9), normalize=False)
    mean = total/np.maximum(count, 1)
    std = np.sqrt(np.maximum(0, squares/np.maximum(count, 1)-mean*mean))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return np.dstack((gray, mean, std, hsv[:, :, 1],
                       image[:, :, 2].astype(np.float32)-image[:, :, 0]))


class HorizontalTextureOccupancy:
    def __init__(self, config, config_version):
        import numpy as np
        self.config, self.config_version = config, config_version
        bounds = np.asarray(config['belt_bounds'])
        self.columns = np.arange(1280)
        self.top = np.ceil(np.interp(self.columns, bounds[:, 0], bounds[:, 1])).astype(int)
        self.bottom = np.floor(np.interp(self.columns, bounds[:, 0], bounds[:, 2])).astype(int)
        self.belt = (np.arange(720)[:, None] >= self.top) & (np.arange(720)[:, None] <= self.bottom)

    @classmethod
    def from_config(cls, path, raw=None):
        raw = Path(path).read_bytes() if raw is None else raw
        config = json.loads(raw)
        validate_horizontal_config(config)
        return cls(config, hashlib.sha256(raw).hexdigest())

    def evaluate(self, image):
        import cv2
        import numpy as np
        started = perf_counter()
        result = dict(config_version=self.config_version,
                      reference_version=self.config['calibration_id'],
                      reference_valid=False, classification='UNKNOWN', regions={},
                      qualification='ISOLATED_ONLY')
        def finish(reason, classification='UNKNOWN', valid=False):
            return dict(result, reason=reason, classification=classification, reference_valid=valid,
                        comparison_ms=(perf_counter()-started)*1000)

        if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
                or list(image.shape) != self.config['shape']):
            return finish('IMAGE_GEOMETRY_OR_FORMAT_INVALID')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        offsets = np.arange(6, 14)
        upper = gray[self.top[:, None]-offsets, self.columns[:, None]]
        lower = gray[self.bottom[:, None]+offsets, self.columns[:, None]]
        support = (np.mean(upper > 155, axis=1) >= .75) & (np.mean(lower > 155, axis=1) >= .75)
        blocks = [float(np.mean(support[x:x+60])) for x in range(0, 1280, 60)]
        result['regions']['surface_geometry'] = dict(full_width=True,
            belt_bounds=self.config['belt_bounds'], rail_support_by_60_columns=blocks)
        if min(blocks) < .8:
            return finish('CONVEYOR_RAIL_GEOMETRY_OR_OCCLUSION')

        values = surface_features(image, self.belt)
        low, high = np.asarray(self.config['feature_low']), np.asarray(self.config['feature_high'])
        outside = (values < low) | (values > high)
        native = (outside[:, :, 0] | outside[:, :, 3] | outside[:, :, 4]) & self.belt
        uncertain = (outside[:, :, 1] | outside[:, :, 2]) & self.belt
        # A same-colour thin remnant can erase the weave without introducing
        # brightness contrast. Test native one-pixel lines before any smoothing.
        # Only lines wholly inside the belt count, including both full exits.
        straight = np.zeros(self.belt.shape, bool)
        for kernel in ((30, 1), (1, 30)):
            inside = cv2.boxFilter(self.belt.astype(np.float32), -1, kernel,
                                  normalize=False, borderType=cv2.BORDER_CONSTANT)
            line_mean = cv2.boxFilter(values[:, :, 0], -1, kernel, normalize=True,
                                     borderType=cv2.BORDER_REFLECT_101)
            line_square = cv2.boxFilter(values[:, :, 0]**2, -1, kernel, normalize=True,
                                       borderType=cv2.BORDER_REFLECT_101)
            line_variance = np.maximum(0, line_square-line_mean**2)
            straight |= (inside == 30) & (line_variance < self.config['minimum_line_variance'])
        def largest(mask, x_offset=0):
            count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
            if count <= 1:
                return dict(pixels=0, box=None)
            index = int(stats[1:, 4].argmax())+1
            box = stats[index, :4].tolist()
            box[0] += x_offset
            return dict(pixels=int(stats[index, 4]), box=box)
        whole = largest(native)
        left, right = largest(native[:, :64]), largest(native[:, -64:], 1216)
        uncertain_whole = largest(uncertain)
        uncertain_exit = max(largest(uncertain[:, :64])['pixels'], largest(uncertain[:, -64:])['pixels'])
        straight_count = int(np.count_nonzero(straight & self.belt))
        result['regions'].update(whole=whole, left_exit=left, right_exit=right,
            uncertain_whole=uncertain_whole, uncertain_exit_pixels=uncertain_exit,
            native_foreground_pixels=int(native.sum()), straight_residual_pixels=straight_count)
        if whole['pixels'] >= 80 or max(left['pixels'], right['pixels']) >= 30 or straight_count > 0:
            return finish('HORIZONTAL_NATIVE_OBJECT_OR_STRAIGHT_RESIDUE', 'OCCUPIED', True)
        if uncertain_whole['pixels'] >= 80 or uncertain_exit >= 30:
            return finish('HORIZONTAL_TEXTURE_NOT_SUPPORTED')
        return finish('HORIZONTAL_CURRENT_SURFACE_MATCH', 'MATCH', True)
