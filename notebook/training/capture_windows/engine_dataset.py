"""Engine acquisition contracts. These declarations never infer boxes or masks.

The controller owns events and the existing session writer owns immutable PNGs.
This module owns target schedules, physical checklists and derived handoff rows.
"""
from collections import Counter
from copy import deepcopy
import re
import socket


CLASSES = ['gray_pipe', 'exhaust_top', 'symbol_module']
CRANK_PHASES = tuple(f'CRANK_{angle:03d}' for angle in range(0, 360, 45))
MAIN_SCENARIOS = ('NORMAL', 'MISSING_PIPE_LEFT', 'MISSING_PIPE_RIGHT',
                  'MISSING_EXHAUST_TOP', 'MISSING_SYMBOL_MODULE', 'MISSING_ALL_TARGETS')
CHALLENGES = {
    'LIGHT_LEFT_WEAK': '왼쪽 조명만 약하게 조정하고 검사 대상 부품은 모두 장착하세요.',
    'LIGHT_RIGHT_WEAK': '오른쪽 조명만 약하게 조정하고 검사 대상 부품은 모두 장착하세요.',
    'BOTH_TOO_DIM': '양쪽 조명을 어둡게 조정하고 검사 대상 부품은 모두 장착하세요.',
    'OCCLUSION': '검사 대상은 모두 장착하고 별도 물체로 일부를 가리세요.',
    'POSITION_OUT_OF_RANGE': '검사 대상은 모두 장착하고 기준 위치에서 크게 벗어나게 놓으세요.',
    'OTHER_PART_MISSING': '검사 대상 4개는 모두 장착하고 다른 부품만 제거하세요.',
    'CONVEYOR_MOVING': '실제 Conveyor 속도·조명·exposure를 기록하고 별도 Motion Pilot으로 촬영하세요.',
}
CRANK_CHECKS = {
    'target_set': '손잡이를 목표 위치에 맞춤',
    'parts_stopped': '빨간색/갈색 가동부가 정지함',
    'body_kept': '엔진 본체 위치를 크게 옮기지 않음',
}
UNLOCK_PHRASE = 'UNLOCK FINAL TEST LABELING'


def engine_v1(plan):
    return plan.get('collection_plan_schema_version') == 3


def station_settings(station_id='STATION_A', capture_pc_id=None, camera_id='TOP_CAMERA_01', e02_lighting_id=None):
    result = {'station_id': station_id, 'capture_pc_id': capture_pc_id or socket.gethostname(),
              'camera_id': camera_id,
              'e02_lighting_id': e02_lighting_id or ('RIGHT_DOMINANT' if station_id == 'STATION_B' else 'LEFT_DOMINANT')}
    validate_station(result)
    return result


def validate_station(station):
    if not isinstance(station, dict) or set(station) != {'station_id', 'capture_pc_id', 'camera_id', 'e02_lighting_id'}:
        raise ValueError('Station/PC/Camera/조명 식별자를 확인하세요.')
    if not isinstance(station['station_id'], str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,31}', station['station_id']):
        raise ValueError('Station ID는 영문 대문자로 시작하는 1~32자 영문/숫자/_입니다.')
    if station['station_id'] in {'CUSTOM', 'CON', 'PRN', 'AUX', 'NUL', *[f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)]}:
        raise ValueError('CUSTOM 대신 고유 Station ID를 입력하세요. Windows 예약 이름은 사용할 수 없습니다.')
    if any(not isinstance(station[k], str) or not station[k].strip() or len(station[k]) > 128
           for k in ('capture_pc_id', 'camera_id')):
        raise ValueError('PC와 카메라 식별자는 비어 있지 않은 128자 이내 문자열입니다.')
    if station['e02_lighting_id'] not in ('LEFT_DOMINANT', 'RIGHT_DOMINANT'):
        raise ValueError('E02는 LEFT_DOMINANT 또는 RIGHT_DOMINANT입니다.')


def validate_crank_schedule(plan):
    if plan['product_id'] != 'engine_model_top_v0' or plan['state_order'] != list(MAIN_SCENARIOS):
        raise ValueError('Engine V1은 3클래스/6상태 Main 계약을 사용합니다.')
    if set(plan['crank_schedule']) != {'E01', 'E02', 'E03', 'E04'}:
        raise ValueError('4회차의 Crank 계획이 필요합니다.')
    if {c['id'] for c in plan['conditions']} != {'BALANCED', 'ASYMMETRIC'}:
        raise ValueError('Main에는 BALANCED와 Station별 ASYMMETRIC만 사용할 수 있습니다.')
    if [r['id'] for r in plan['rounds']] != ['E01', 'E02', 'E03', 'E04']:
        raise ValueError('E01~E04 회차 순서를 유지하세요.')
    for row, offset, diagonal, purpose in zip(plan['rounds'], (0, 0, 15, 8), (False, True, False, True),
                                             ('train_candidate', 'train_candidate', 'validation_candidate', 'test_reserved')):
        expected_angles = [f'ANGLE_{offset + 30*n:03d}' for n in range(12)]
        if row['placement_ids'] != expected_angles or row['purpose'] != purpose:
            raise ValueError('회차별 12개 목표 각도와 split 예약을 유지하세요.')
        expected = [{'crank_phase_id': f'CRANK_{phase*90 + (45 if diagonal else 0):03d}',
                     'placement_ids': expected_angles[phase::4]} for phase in range(4)]
        if plan['crank_schedule'][row['id']] != expected:
            raise ValueError('각 Crank당 3각도와 회차별 cardinal/diagonal 분포를 유지하세요.')
        if row['condition_id'] != ('ASYMMETRIC' if row['id'] == 'E02' else 'BALANCED'):
            raise ValueError('Main 조명은 BALANCED/E02 ASYMMETRIC입니다.')


def physical_checklist(profile, scenario):
    if scenario in CHALLENGES:
        return {'targets_installed': 'gray pipe 2개 / exhaust_top / symbol_module 정상 장착',
                'challenge_prepared': CHALLENGES[scenario], 'hands_clear': '손이 화면에서 빠짐'}
    removed = profile['scenarios'][scenario]['removed_slots']
    names = {'PIPE_LEFT': '왼쪽 파이프', 'PIPE_RIGHT': '오른쪽 파이프',
             'EXHAUST_TOP': '상단 배기구', 'SYMBOL_MODULE': '문양 모듈'}
    checks = {slot: names[slot]+('만 제거' if len(removed) == 1 and slot in removed
                               else ' 제거' if slot in removed else ' 정상 장착')
              for slot in profile['slots']}
    checks['hands_clear'] = '손이 화면에서 빠짐'
    return checks


def require_checks(values, checklist):
    if not isinstance(values, dict) or set(values) != set(checklist) or any(v is not True for v in values.values()):
        raise ValueError('모든 물리 상태 확인 항목을 체크해야 합니다.')


def challenge_profile(profile):
    result = deepcopy(profile)
    for scenario in CHALLENGES:
        result['scenarios'][scenario] = deepcopy(profile['scenarios']['NORMAL'])
    return result


def crank_for_action(action):
    block = action.get('block')
    if not block:
        return 'CRANK_000'
    role = action.get('role_id') or action.get('attempt', {}).get('role_id')
    return next((s['crank_phase_id'] for s in block['steps'] if s['step_id'] == role), block['steps'][0]['crank_phase_id'])


def crank_gate_key(action):
    return (action['block']['block_id'] if action.get('block') else action['role_id'])+'_'+crank_for_action(action)


def lighting_id(collection, condition, scenario=None):
    if scenario in ('LIGHT_LEFT_WEAK', 'LIGHT_RIGHT_WEAK', 'BOTH_TOO_DIM'):
        return scenario
    if condition == 'ASYMMETRIC':
        return collection.info['station']['e02_lighting_id']
    return 'BALANCED' if condition == 'SETUP' else condition


def truth_fields(profile, scenario):
    rule = (profile['scenarios']['NORMAL'] if scenario in CHALLENGES else profile['scenarios'][scenario])
    removed = rule['removed_slots']
    return {'capture_truth_source': 'human_declared_physical_state_not_inference',
            'capture_truth_result': 'REVIEW' if scenario in CHALLENGES else 'FAIL' if removed else 'PASS',
            'defect_type': 'MULTIPLE_MISSING' if len(removed) > 1 else 'MISSING_PART' if removed else 'NONE',
            'defect_part': 'ALL_INSPECTION_TARGETS' if len(removed) > 1 else removed[0] if removed else 'NONE',
            'expected_counts': deepcopy(rule['expected_counts']), 'removed_slots': list(removed)}


def capture_identity(collection, record):
    # Namespace metadata IDs as well as station directories. Two stations remain
    # distinct even if an imported raw session happens to reuse a UUID/name.
    return collection.info['station']['station_id']+'__'+record['capture_id']


def pair_key(row):
    return tuple(row[k] for k in ('station_id', 'capture_pc_id', 'camera_id', 'collection_id', 'setup_id',
                                 'round_id', 'lighting_id', 'engine_angle_target_deg', 'crank_phase_id', 'split'))


def reference_at_capture(collection, intent):
    """Record the approved comparison available at capture time, if any.

    Exports also resolve the current reviewed reference after retakes, keeping
    this historical link separately instead of silently rewriting the event.
    """
    metadata = intent['engine_metadata']
    for row in metadata_rows(collection):
        if (row['scenario'] == 'NORMAL' and row['human_review_status'] == 'ACCEPT'
                and row['setup_id'] == intent['setup_id'] and row['round_id'] == intent['round_id']
                and row['lighting_id'] == metadata['lighting_id']
                and row['engine_angle_target_deg'] == metadata['engine_angle_target_deg']
                and row['crank_phase_id'] == metadata['crank_phase_id']):
            return row['capture_id']
    return None


def metadata_rows(collection):
    accepted = {aid for group in collection.accepted.values() for aid in group.values()}
    rows = []
    for aid, attempt in collection.attempts.items():
        raw = attempt['record']
        block = collection.block_by_id.get(attempt['block_id'])
        purpose = 'pilot' if block and block['phase'] == 'pilot' else attempt['purpose']
        reviewed = aid in accepted and not attempt['rejected']
        is_main = bool(block and block['phase'] == 'main')
        row = {**deepcopy(attempt['engine_metadata']), **truth_fields(collection.profile, attempt['scenario']),
               'capture_id': capture_identity(collection, raw), 'raw_capture_id': raw['capture_id'],
               'session_id': raw['session_id'], 'collection_id': collection.info['collection_id'],
               'setup_id': attempt['setup_id'], 'round_id': attempt['round_id'], 'purpose': purpose,
               'scenario': attempt['scenario'], 'image_path': str(collection.folder/'sessions'/raw['image_path']),
               'image_sha256': raw['image_sha256'], 'width': raw['width'], 'height': raw['height'],
               'captured_at': raw['captured_at'], 'quality_metrics': deepcopy(attempt['metrics']),
               'source_kind': raw['source_kind'], 'split': purpose if is_main else 'excluded',
               'human_review_status': 'REVIEW' if attempt.get('held') else 'RETAKE' if attempt['rejected']
                   else 'ACCEPT' if reviewed else 'PENDING',
               'test_reserved': purpose == 'test_reserved', 'is_reference_normal': attempt['scenario'] == 'NORMAL',
               'exclude_from_training': not (is_main and purpose == 'train_candidate' and reviewed and raw['source_kind'] == 'camera'),
               'yolo_label_required': is_main, 'anomaly_mask_candidate': False,
               'reference_normal_capture_id': None, 'labeling_ready': False,
               'metadata_schema_version': 1}
        if row['scenario'] == 'NORMAL':
            row['reference_normal_capture_id_at_capture'] = row['capture_id']
        rows.append(row)
    normals = {pair_key(row): row for row in rows if row['scenario'] == 'NORMAL' and row['human_review_status'] == 'ACCEPT'}
    for row in rows:
        reference = row if row['scenario'] == 'NORMAL' else normals.get(pair_key(row))
        if reference:
            row['reference_normal_capture_id'] = reference['capture_id']
        row['labeling_ready'] = (row['split'] != 'excluded' and row['human_review_status'] == 'ACCEPT'
                                 and reference is not None and row['source_kind'] == 'camera'
                                 and row['engine_angle_human_confirmed'] and row['crank_phase_human_confirmed'])
        row['labeling_blockers'] = ([] if row['labeling_ready'] else ['PENDING_REVIEW_REFERENCE_OR_NON_MAIN_SOURCE'])
    return rows


def select_mask_candidates(rows, per_scenario=8, similar_distance=2):
    """Deterministic balanced crank selection, then farthest circular angle.

    Exact/perceptually close duplicates are skipped, never replaced just to meet
    a quota. A complete, diverse E03 contributes eight per defect = forty.
    """
    groups = {}
    for row in rows:
        if row['round_id'] == 'E03' and row['capture_truth_result'] == 'FAIL' and row['labeling_ready'] and not row['test_reserved']:
            groups.setdefault((row['station_id'], row['scenario']), []).append(row)
    selected = []
    for key in sorted(groups):
        pool = sorted(groups[key], key=lambda r: (r['engine_angle_target_deg'], r['capture_id']))
        chosen, phase_counts = [], Counter()
        while pool and len(chosen) < per_scenario:
            def priority(row):
                angle = row['engine_angle_target_deg']
                spacing = min((min(abs(angle-r['engine_angle_target_deg']), 360-abs(angle-r['engine_angle_target_deg'])) for r in chosen), default=360)
                return (phase_counts[row['crank_phase_id']], -spacing, angle, row['capture_id'])
            row = min(pool, key=priority)
            pool.remove(row)
            duplicate = any(row['image_sha256'] == old['image_sha256'] or
                (int(row['quality_metrics']['dhash'], 16) ^ int(old['quality_metrics']['dhash'], 16)).bit_count() <= similar_distance
                for old in chosen)
            if duplicate:
                continue
            chosen.append(row)
            phase_counts[row['crank_phase_id']] += 1
        selected.extend(chosen)
    return selected
