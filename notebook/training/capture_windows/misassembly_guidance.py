"""Reuse Wizard alignment geometry without marking or measuring the raw image."""
import math
from PIL import ImageDraw

from .engine_alignment import alignment_marks, validate_alignment
from .wizard_quality import overlay

# Saved alignment box from the accepted TRAIN NORMAL D001 setup, not a label bbox.
# Provenance and original pixel dimensions are shipped in reference-framing.json.
DEFAULT_BODY_ROI = [.3816568047337278, .07631578947368421,
                    .2736686390532544, .8263157894736842]
POSITION_OFFSETS = {'CENTER': 0.0, 'OFFSET_RIGHT': .08}
PART_NAMES = {'pipe_left': '왼쪽 파이프', 'pipe_right': '오른쪽 파이프',
              'exhaust': '배기구', 'symbol': '문양 부품'}
ZERO_GUIDE = '0°: 정상 기준처럼 긴 금색 중심축 끝을 아래로, 짧은 끝을 위로. 파이프 좌우는 이 기준의 실물 자리입니다.'


def guide_geometry(body_roi, position, angle, size):
    """A translated, clockwise rectangle; the short shaft end is the top marker."""
    shift = POSITION_OFFSETS[position]
    x, y, w, h = body_roi
    # Validate the whole turn, including both planned positions, before drawing.
    envelope = [.005917159763313609, .007894736842105263,
                .9881656804733727, .9842105263157894]
    for offset in POSITION_OFFSETS.values():
        validate_alignment([x + offset, y, w, h], envelope, size)
    shifted = [x + shift, y, w, h]
    body, center, tip, chevron = alignment_marks(shifted, angle, size)
    # Only extend the narrow shaft end. Enlarging the whole rectangle would
    # shift the existing rotation center or force a different capture scale.
    # D001's tail is ~28 px beyond the old box; 40 px leaves a small margin.
    cx, cy = center
    half_width, half_height = w*size[0]/2, h*size[1]/2
    tail_half = w*size[0]*.12
    tail_length = h*size[1]*(40 / (.8263157894736842*720))
    local = [(-half_width, -half_height), (half_width, -half_height),
             (half_width, half_height), (tail_half, half_height),
             (tail_half, half_height+tail_length), (-tail_half, half_height+tail_length),
             (-tail_half, half_height), (-half_width, half_height)]
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    polygon = [(cx+dx*cosine-dy*sine, cy+dx*sine+dy*cosine) for dx, dy in local]
    radius = max(math.hypot(dx, dy) for dx, dy in local)
    for offset in POSITION_OFFSETS.values():
        center_x = (x+w/2+offset)*size[0]
        if (center_x-radius < envelope[0]*size[0] or center_x+radius > (envelope[0]+envelope[2])*size[0]
                or cy-radius < envelope[1]*size[1] or cy+radius > (envelope[1]+envelope[3])*size[1]):
            raise ValueError('꼬리까지 한 바퀴 회전할 공간이 부족합니다. 최초 배치 박스를 조금 줄여주세요.')
    roi = [(center[0]-radius)/size[0], (center[1]-radius)/size[1],
           radius*2/size[0], radius*2/size[1]]
    return dict(body_roi=shifted, envelope=roi, polygon=polygon,
                center=center, tip=tip, chevron=chevron)


def render_guide(raw, body_roi, position, angle):
    geo = guide_geometry(body_roi, position, angle, (raw.shape[1], raw.shape[0]))
    placement = dict(dx=0, dy=0, angle_deg=angle, rotation_only=True)
    preview = overlay(raw, geo['envelope'], placement)
    draw = ImageDraw.Draw(preview)
    cyan = (35, 235, 255)
    draw.line(geo['polygon']+[geo['polygon'][0]], fill=cyan, width=4)
    draw.line([geo['center'], geo['tip']], fill=cyan, width=3)
    draw.line(geo['chevron'], fill=cyan, width=5)
    cx, cy = geo['center']
    draw.line([(cx-10,cy),(cx+10,cy)], fill=cyan, width=3)
    draw.line([(cx,cy-10),(cx,cy+10)], fill=cyan, width=3)
    return preview
