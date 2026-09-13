"""Versioned collection recipes, distinct from product ground-truth scenarios."""
from copy import deepcopy
import math
from pathlib import Path
import re

from .guide import read_json, validate_guide

PURPOSES = ('train_candidate', 'validation_candidate', 'test_reserved')


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,39}', value) is not None


def finite(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_plan(plan, profile, guide):
    validate_guide(guide, profile)
    keys = {'collection_plan_schema_version', 'plan_id', 'plan_version', 'product_id',
            'rounds', 'conditions', 'placements', 'state_order', 'references', 'quality'}
    if not isinstance(plan, dict) or set(plan) != keys:
        raise ValueError('수집 계획 필드를 확인하세요.')
    if type(plan['collection_plan_schema_version']) is not int or plan['collection_plan_schema_version'] != 1:
        raise ValueError('지원하지 않는 수집 계획 형식입니다.')
    if not identifier(plan['plan_id']) or type(plan['plan_version']) is not int or plan['plan_version'] < 1:
        raise ValueError('수집 계획 ID/버전을 확인하세요.')
    if plan['product_id'] != profile['product_id']:
        raise ValueError('제품과 수집 계획이 다릅니다.')
    states = plan['state_order']
    if not isinstance(states, list) or len(states) != len(profile['scenarios']) or set(states) != set(profile['scenarios']):
        raise ValueError('계획은 제품의 모든 상태를 중복 없이 포함해야 합니다.')
    specs = [('rounds', {'id', 'label', 'purpose'}),
             ('conditions', {'id', 'label', 'instruction', 'requires_lamp', 'lamp_xy'}),
             ('placements', {'id', 'label', 'instruction', 'dx', 'dy', 'angle_deg'})]
    for key, fields in specs:
        items = plan[key]
        if not isinstance(items, list) or not 1 <= len(items) <= 20:
            raise ValueError(f'{key}: 1~20개 항목이 필요합니다.')
        ids = []
        for item in items:
            if not isinstance(item, dict) or set(item) != fields or not identifier(item['id']):
                raise ValueError(f'{key}: 항목 형식/ID 오류입니다.')
            for field in fields & {'label', 'instruction'}:
                if not isinstance(item[field], str) or not item[field].strip() or len(item[field]) > 1500:
                    raise ValueError(f'{key}: 안내 문구 오류입니다.')
            ids.append(item['id'])
        if len(ids) != len(set(ids)):
            raise ValueError(f'{key}: ID가 중복됩니다.')
    if any(r['purpose'] not in PURPOSES for r in plan['rounds']):
        raise ValueError('회차 용도 예약이 올바르지 않습니다.')
    for c in plan['conditions']:
        if type(c['requires_lamp']) is not bool or not isinstance(c['lamp_xy'], list) or len(c['lamp_xy']) != 2:
            raise ValueError('조명 요구/그림 좌표를 확인하세요.')
        if not all(finite(n, -1, 1) for n in c['lamp_xy']):
            raise ValueError('조명 그림 좌표는 -1~1입니다.')
    if plan['conditions'][0]['requires_lamp']:
        raise ValueError('첫 기준 조명은 별도 스탠드 없이도 사용할 수 있어야 합니다.')
    for p in plan['placements']:
        if not all(finite(p[k], -.5, .5) for k in ('dx', 'dy')) or not finite(p['angle_deg'], -30, 30):
            raise ValueError('배치 이동/각도 안내 범위를 확인하세요.')
    if any(plan['placements'][0][k] != 0 for k in ('dx', 'dy', 'angle_deg')):
        raise ValueError('첫 배치는 이동/회전 없는 기준 위치여야 합니다.')
    refs = plan['references']
    if not isinstance(refs, list) or len(refs) != 2 or any(s not in states for s in refs) or len(set(refs)) != 2:
        raise ValueError('서로 다른 정상/빈자리 기준 상태 2개를 지정하세요.')
    q = plan['quality']
    ranges = {'settle_seconds': (.5, 5), 'timeout_seconds': (3, 30), 'stable_frames': (2, 10),
              'motion_mae': (.1, 30), 'blur_variance': (0, 1000), 'dark_mean': (0, 80),
              'bright_fraction': (.01, .8), 'similar_hash_distance': (0, 10)}
    if not isinstance(q, dict) or set(q) != {'version', *ranges} or type(q['version']) is not int or q['version'] != 1:
        raise ValueError('품질 시작 규칙 v1을 확인하세요.')
    if any(not finite(q[k], *bounds) for k, bounds in ranges.items()):
        raise ValueError('품질 시작값 범위가 올바르지 않습니다.')
    if any(type(q[k]) is not int for k in ('stable_frames', 'similar_hash_distance')) or q['settle_seconds'] >= q['timeout_seconds']:
        raise ValueError('안정 프레임 수/대기 제한을 확인하세요.')
    return plan


def load_plan(profile_path, profile, guide, plan_path=None):
    path = Path(plan_path) if plan_path else Path(profile_path).with_name('collection-plan.json')
    return validate_plan(read_json(path), profile, guide)


def expand_plan(template, has_lamp):
    if type(has_lamp) is not bool:
        raise ValueError('조명 설치 가능 여부를 확인하세요.')
    plan = deepcopy(template)
    excluded = [{'condition_id': c['id'], 'reason': '최초 설정: 조절 가능한 스탠드 없음'}
                for c in template['conditions'] if c['requires_lamp'] and not has_lamp]
    plan['conditions'] = [c for c in template['conditions'] if has_lamp or not c['requires_lamp']]
    blocks = []
    for phase, rounds, placements in (
            ('pilot', [{'id': 'PREP', 'label': '준비 시험', 'purpose': 'preparation'}], plan['placements'][:1]),
            ('main', plan['rounds'], plan['placements'])):
        for round_info in rounds:
            for condition in plan['conditions']:
                for placement in placements:
                    block_id = f"{phase}_{round_info['id']}_{condition['id']}_{placement['id']}"
                    blocks.append({'block_id': block_id, 'phase': phase, 'round_id': round_info['id'],
                        'purpose': round_info['purpose'], 'condition_id': condition['id'], 'placement_id': placement['id'],
                        'steps': [{'step_id': block_id+'_'+s, 'scenario': s} for s in plan['state_order']]})
    if len({b['block_id'] for b in blocks}) != len(blocks):
        raise ValueError('회차/조건/배치 조합의 ID가 충돌합니다. 설정 ID를 구분하세요.')
    return {'effective_plan_version': 1, 'has_lamp': has_lamp, 'excluded_at_setup': excluded,
            'conditions': plan['conditions'], 'blocks': blocks}


def validate_roi(roi):
    if not isinstance(roi, (list, tuple)) or len(roi) != 4 or not all(finite(n, 0, 1) for n in roi):
        raise ValueError('검사 영역은 영상 안의 정규화된 x/y/폭/높이여야 합니다.')
    x, y, w, h = roi
    if min(w, h) < .08 or x+w > 1 or y+h > 1:
        raise ValueError('검사 영역이 너무 작거나 영상 밖입니다.')


def target_polygon(roi, placement, size):
    """Pixel-space clockwise angle, always relative to the saved reference ROI."""
    validate_roi(roi)
    width, height = size
    x, y, w, h = roi
    w, h = w*width, h*height
    cx = (x+roi[2]/2)*width + placement['dx']*w
    cy = (y+roi[3]/2)*height + placement['dy']*h
    angle = math.radians(placement['angle_deg'])
    cosine, sine = math.cos(angle), math.sin(angle)
    return [(cx+dx*cosine-dy*sine, cy+dx*sine+dy*cosine)
            for dx, dy in [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]]


def validate_targets(roi, placements, size):
    for placement in placements:
        if any(not (2 <= x <= size[0]-2 and 2 <= y <= size[1]-2)
               for x, y in target_polygon(roi, placement, size)):
            raise ValueError('이 검사 영역은 이동/회전하면 영상 밖으로 나갑니다. 중앙에 더 작은 기준 영역을 지정하세요.')


def target_roi(roi, placement, size):
    points = target_polygon(roi, placement, size)
    xs, ys = zip(*points)
    return [min(xs)/size[0], min(ys)/size[1], (max(xs)-min(xs))/size[0], (max(ys)-min(ys))/size[1]]
