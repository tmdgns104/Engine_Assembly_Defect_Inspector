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

# Display text is tied to the same scenario/part states that are saved. Legacy
# plans keep their original labels and hashes; their wording is not a second truth.
STATE_TEXT = {'CORRECT': '정상 장착', 'MISSING': '없음',
              'UPWARD_ROTATED': '위로 돌아가게 장착', 'OUTWARD_SPLAYED': '바깥으로 벌어지게 장착',
              'REVERSED': '반대 방향으로 장착', 'SIDEWAYS': '옆 방향으로 장착',
              'UPSIDE_DOWN': '거꾸로 장착'}
SCENARIO_GUIDES = {
    'NORMAL': (None, 'CORRECT', '모든 부품 정상', 'normal_reference.png'),
    'MISSING_PIPE_LEFT': ('pipe_left', 'MISSING', '왼쪽 파이프 없음', 'normal_reference.png'),
    'MISSING_PIPE_RIGHT': ('pipe_right', 'MISSING', '오른쪽 파이프 없음', 'normal_reference.png'),
    'MISSING_EXHAUST_TOP': ('exhaust', 'MISSING', '배기구 없음', 'normal_reference.png'),
    'MISSING_SYMBOL_MODULE': ('symbol', 'MISSING', '문양 부품 없음', 'normal_reference.png'),
    'MISSING_ALL_TARGETS': ('ALL', 'MISSING', '대상 네 부품 모두 없음', 'normal_reference.png'),
    'LEFT_PIPE_UP': ('pipe_left', 'UPWARD_ROTATED', '왼쪽 파이프\n위로 돌아감', 'example_pipe_left_up.png'),
    'LEFT_PIPE_OUT': ('pipe_left', 'OUTWARD_SPLAYED', '왼쪽 파이프\n바깥으로 벌어짐', 'example_pipe_left.png'),
    'RIGHT_PIPE_UP': ('pipe_right', 'UPWARD_ROTATED', '오른쪽 파이프\n위로 돌아감', 'example_pipe_right.png'),
    'RIGHT_PIPE_OUT': ('pipe_right', 'OUTWARD_SPLAYED', '오른쪽 파이프\n바깥으로 벌어짐', 'example_pipe_right_out.png'),
    'EXHAUST_REVERSED': ('exhaust', 'REVERSED', '배기구 반대 방향', 'example_exhaust.png'),
    'EXHAUST_SIDE': ('exhaust', 'SIDEWAYS', '배기구 옆 방향', 'example_exhaust_side.png'),
    'SYMBOL_UPSIDE_DOWN': ('symbol', 'UPSIDE_DOWN', '문양 부품 거꾸로', 'example_symbol.png'),
}


def scenario_guide(step):
    """Return operator guidance after checking the plan's state/image agreement."""
    if step['scenario_id'] not in SCENARIO_GUIDES:
        raise ValueError('안내가 준비되지 않은 시나리오입니다.')
    target, state, name, example = SCENARIO_GUIDES[step['scenario_id']]
    expected = {p: state if p == target or target == 'ALL' else 'CORRECT' for p in PART_NAMES}
    if (step['part_states'] != expected
            or step['target_part'] != (None if target == 'ALL' else target)):
        raise ValueError('시나리오와 계획의 부품 상태가 다릅니다.')
    if step['example_image'] != example:
        raise ValueError('시나리오와 대상 예시 이미지가 다릅니다.')
    category = '결품' if state == 'MISSING' else ('정상' if state == 'CORRECT' else '오조립')
    correct = [PART_NAMES[p] for p, value in expected.items() if value == 'CORRECT']
    keep = '정상 유지: ' + (' · '.join(correct) if correct else '본체 · 중심축')
    if category == '결품':
        prepare = ('파이프 2개·배기구·문양을 모두 제거하세요.' if target == 'ALL'
                   else PART_NAMES[target] + '만 제거하세요.')
        caption = '제거 전 정상 참고입니다. 위에 적힌 부품을 제거하세요.'
        example_label = '제거 전 정상 참고'
    elif category == '오조립':
        prepare = '예시처럼 ' + STATE_TEXT[state] + '하세요.'
        caption = '오조립 예시: 해당 부품만 참고 · 나머지는 정상'
        example_label = '오조립 목표 부분'
    else:
        prepare, keep = '네 부품을 모두 정상으로 장착하세요.', '파이프 2개 · 배기구 · 문양 모두 정상'
        caption, example_label = '기존 학습용 정상 기준입니다. 네 부품을 모두 유지하세요.', '정상 목표'
    title = f'[{category}] {name}'
    list_title = title.replace('\n위로 돌아감', ' · 위로').replace('\n바깥으로 벌어짐', ' · 바깥')
    return dict(category=category, title=title, list_title=list_title,
                prepare=prepare, keep=keep, example_caption=caption, example_label=example_label,
                part_summary='\n'.join(f'{PART_NAMES[p]}: {STATE_TEXT[value]}' for p, value in expected.items()))


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
