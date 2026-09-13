"""Small ROI metrics and a bounded capture gate, never semantic AI judgments."""
import math
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .wizard_plan import target_polygon, validate_roi

WARNING_TEXT = {
    'BLUR': '윤곽이 약합니다. 원본에서 선명도를 확인하세요.',
    'DARK': '검사 부분이 어둡습니다. 빈자리와 부품이 구별되는지 확인하세요.',
    'BRIGHT_REFLECTION': '검사 부분에 밝은 반사가 많을 수 있습니다.',
    'DUPLICATE_EXACT': '이전 사진과 원본 픽셀이 같습니다. 실제 배치와 수집 의도를 확인하세요.',
    'SIMILAR_IMAGE': '이전 사진과 매우 비슷합니다. 대칭 상태일 수도 있어 자동 제외하지 않습니다.'}


def roi_gray(image, roi):
    validate_roi(roi)
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError('원본 BGR 영상 형식이 올바르지 않습니다.')
    h, w = image.shape[:2]
    x, y, rw, rh = roi
    part = image[int(y*h):max(int((y+rh)*h), int(y*h)+1), int(x*w):max(int((x+rw)*w), int(x*w)+1)]
    gray = cv2.cvtColor(part, cv2.COLOR_BGR2GRAY)
    scale = min(1, 320/max(gray.shape))
    return cv2.resize(gray, (max(2, round(gray.shape[1]*scale)), max(2, round(gray.shape[0]*scale))))


def metrics(image, roi, rules, scenario=None):
    gray = roi_gray(image, roi)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean = float(gray.mean())
    bright = float((gray >= 245).mean())
    tiny = cv2.resize(gray, (9, 8))
    bits = (tiny[:, 1:] > tiny[:, :-1]).flatten()
    dhash = sum(int(bit) << i for i, bit in enumerate(bits))
    limit = rules.get('blur_by_state', {}).get(scenario, rules['blur_variance'])
    warnings = []
    if variance < limit: warnings.append('BLUR')
    if mean < rules['dark_mean']: warnings.append('DARK')
    if bright > rules['bright_fraction']: warnings.append('BRIGHT_REFLECTION')
    return {'metric_schema_version': 1, 'rules_version': rules['version'], 'roi': list(roi),
            'analysis_size': [gray.shape[1], gray.shape[0]], 'laplacian_variance': variance,
            'mean_brightness': mean, 'bright_fraction': bright, 'dark_fraction': float((gray <= 15).mean()),
            'dhash': f'{dhash:016x}', 'warnings': warnings,
            'semantics': 'advisory_only_not_hand_detection_or_state_validation'}


class CaptureGate:
    def __init__(self, rules, roi, frame, now=None):
        self.rules, self.roi = rules, roi
        self.started = time.monotonic() if now is None else now
        self.stream, self.size = frame.stream_id, frame.image.shape
        self.previous, self.last_token = None, None
        self.stable = 0
        self.active = True
        self.message = '손을 빼세요. 잠시 기다린 뒤 한 장만 촬영합니다.'

    def cancel(self):
        self.active = False

    def observe(self, frame, now=None):
        now = time.monotonic() if now is None else now
        if not self.active:
            return None
        if now-self.started > self.rules['timeout_seconds']:
            self.cancel()
            raise ValueError('안정된 영상을 기다리는 시간이 끝났습니다. 배치를 확인하고 다시 준비를 누르세요.')
        if frame is None or not frame.fresh(now) or frame.stream_id != self.stream or frame.image.shape != self.size:
            self.cancel()
            raise ValueError('카메라 연결/신선도/해상도가 바뀌어 촬영을 취소했습니다.')
        if frame.received_mono <= self.started+self.rules['settle_seconds']:
            return None
        token = (frame.stream_id, frame.sequence)
        if token == self.last_token:
            return None
        self.last_token = token
        gray = cv2.resize(roi_gray(frame.image, self.roi), (96, 96))
        change = None if self.previous is None else float(np.abs(gray.astype(float)-self.previous).mean())
        self.previous = gray.astype(float)
        self.stable = self.stable+1 if change is not None and change <= self.rules['motion_mae'] else 0
        self.message = '흔들림을 확인 중입니다. 정지한 손/잘못된 배치는 자동 확인하지 못합니다.'
        if self.stable >= self.rules['stable_frames']:
            self.cancel()
            return frame
        return None


def overlay(image, roi, placement):
    """A fresh RGB preview; never writes on the camera's BGR array."""
    preview = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)).convert('RGBA')
    layer = Image.new('RGBA', preview.size)
    draw = ImageDraw.Draw(layer)
    points = target_polygon(roi, placement, preview.size)
    draw.polygon(points, fill=(255, 220, 25, 25))
    draw.line(points+[points[0]], fill=(255, 225, 30, 230), width=4)
    cx, cy = np.mean(points, axis=0)
    draw.line([(cx-12, cy), (cx+12, cy)], fill='yellow', width=2)
    draw.line([(cx, cy-12), (cx, cy+12)], fill='yellow', width=2)
    angle = math.radians(placement['angle_deg'])
    tip = (cx+45*math.sin(angle), cy-45*math.cos(angle))
    draw.line([(cx, cy), tip], fill='yellow', width=4)
    draw.ellipse((tip[0]-5, tip[1]-5, tip[0]+5, tip[1]+5), fill='yellow')
    return Image.alpha_composite(preview, layer).convert('RGB')
