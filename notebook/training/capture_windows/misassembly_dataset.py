"""Connect additional captures to the prepared, audited dataset without editing it."""
from copy import deepcopy
import hashlib
from pathlib import Path


def select_dataset(path, template, identity, coverage):
    """Recognize only the baseline audited for this package, not arbitrary JSON."""
    path = Path(path).resolve(strict=True)
    expected = identity['files'].get(path.name)
    if expected is None or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('이 패키지의 기준 자료와 다른 파일입니다. 기존 source_index.json 또는 collection.json을 선택하세요. '
                         '변경된 데이터셋은 제작 담당자가 부족 각도를 다시 확인해야 합니다.')
    # Reuse only the pre-audited training scope. Never inspect sealed images here.
    if any(row['split'] != 'train' or row['round_id'] not in ('E01', 'E02')
           for row in coverage['evidence']):
        raise ValueError('기준 자료의 학습용 각도 근거 범위가 올바르지 않습니다.')
    if template['existing_coverage'] != coverage['coverage']:
        raise ValueError('기준 자료의 각도 근거와 촬영 계획이 다릅니다.')
    plan = deepcopy(template)
    plan['collection_mode'] = 'additional'
    plan['dataset_source'] = {
        'dataset_id': identity['dataset_id'],
        'base_collection_id': identity['collection_id'],
        'selected_file_name': path.name, 'selected_file_sha256': expected,
        'source_index_sha256': coverage['source_index_sha256'],
        'existing_coverage': deepcopy(coverage['coverage']),
        'accepted_train_evidence': deepcopy(coverage['evidence']),
        'verification_scope': 'prepared baseline metadata fingerprint and prior accepted TRAIN audit; '
                              'images and labels are not re-reviewed at selection',
        'baseline_files_modified': False,
    }
    return plan, path.parent / 'additional-captures'


def new_dataset_plan(template):
    """All 10-degree states for an explicitly new dataset, with no coverage skip."""
    plan = deepcopy(template)
    plan.update(plan_id='ENGINE_MISASSEMBLY_CAPTURE_001_10DEG_FULL_V4',
                collection_mode='new', dataset_source=None, existing_coverage={},
                coverage_evidence=None,
                target_basis='New dataset: all 36 angles for normal and five missing states, '
                             'seven misassembly states at two positions, three right-position normal controls.')
    states = {}
    for step in template['steps']:
        if step['capture_reason'] == 'missing_recorded_training_angle':
            states.setdefault(step['scenario_id'], step)
    steps = []
    for scenario, example in states.items():
        for angle in range(0, 360, 10):
            step = deepcopy(example)
            step.update(step_id=f'MA_{scenario}_FULL_{angle:03d}',
                        target_engine_angle=angle, capture_reason='new_dataset_full_angle')
            if scenario == 'NORMAL':
                step['scenario_label'] = '정상 · 전체 각도 촬영'
            steps.append(step)
        if scenario == 'NORMAL':
            steps.extend(deepcopy(s) for s in template['steps']
                         if s['capture_reason'] == 'new_device_control' and s['target_position'] != 'CENTER')
    steps.extend(deepcopy(s) for s in template['steps'] if s['capture_reason'] == 'new_misassembly_coverage')
    plan['steps'] = steps
    return plan


def dataset_summary(plan):
    source = plan.get('dataset_source')
    if source:
        return f"기존 자료: {source['dataset_id']} · 추가 촬영 {len(plan['steps'])}장"
    if plan.get('collection_mode') == 'new':
        return f"전체 새 촬영 · 10° 간격 {len(plan['steps'])}장"
    return '이전 추가 촬영 이어가기 · 저장된 계획 유지'
