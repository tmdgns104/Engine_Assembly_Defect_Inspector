"""Regenerate the fixed pilot plan; counts come from the verified source audit."""
import json
from pathlib import Path

folder = Path(__file__).parent
correct = {part: 'CORRECT' for part in ('pipe_left', 'pipe_right', 'exhaust', 'symbol')}
states = [
    ('NORMAL', '정상 대조군', None, None, 'normal_reference.png'),
    ('LEFT_PIPE_UP', '왼쪽 파이프 위로 돌아감', 'pipe_left', 'UPWARD_ROTATED', 'example_pipe_left_up.png'),
    ('LEFT_PIPE_OUT', '왼쪽 파이프 바깥으로 벌어짐', 'pipe_left', 'OUTWARD_SPLAYED', 'example_pipe_left.png'),
    ('RIGHT_PIPE_UP', '오른쪽 파이프 위로 돌아감', 'pipe_right', 'UPWARD_ROTATED', 'example_pipe_right.png'),
    ('RIGHT_PIPE_OUT', '오른쪽 파이프 바깥으로 벌어짐', 'pipe_right', 'OUTWARD_SPLAYED', 'example_pipe_right_out.png'),
    ('EXHAUST_REVERSED', '배기구 반대 방향', 'exhaust', 'REVERSED', 'example_exhaust.png'),
    ('EXHAUST_SIDE', '배기구 옆 방향', 'exhaust', 'SIDEWAYS', 'example_exhaust_side.png'),
    ('SYMBOL_UPSIDE_DOWN', '문양 부품 거꾸로', 'symbol', 'UPSIDE_DOWN', 'example_symbol.png'),
]
coverage_path = folder / 'existing-angle-coverage.json'
coverage_audit = json.loads(coverage_path.read_text(encoding='utf-8'))
coverage = coverage_audit['coverage']
missing_states = [
    ('NORMAL', '정상 · 부족한 각도 보충', None, None, 'normal_reference.png'),
    ('MISSING_PIPE_LEFT', '왼쪽 파이프 결품', 'pipe_left', 'MISSING', 'normal_reference.png'),
    ('MISSING_PIPE_RIGHT', '오른쪽 파이프 결품', 'pipe_right', 'MISSING', 'normal_reference.png'),
    ('MISSING_EXHAUST_TOP', '배기구 결품', 'exhaust', 'MISSING', 'normal_reference.png'),
    ('MISSING_SYMBOL_MODULE', '문양 부품 결품', 'symbol', 'MISSING', 'normal_reference.png'),
    ('MISSING_ALL_TARGETS', '대상 부품 모두 결품', None, 'MISSING', 'normal_reference.png'),
]
steps = []
for scenario, label, target_part, target_value, example_image in states:
    part_states = dict(correct)
    if target_part:
        part_states[target_part] = target_value
    angles = tuple(range(0, 360, 10)) if target_part else (0, 120, 240)
    for position in ('CENTER', 'OFFSET_RIGHT'):
        for angle in angles:
            steps.append({
                'step_id': f'MA_{scenario}_{position}_{angle:03d}',
                'scenario_id': scenario, 'scenario_label': label,
                'part_states': part_states, 'target_engine_angle': angle,
                'target_position': position,
                'assembly_episode_id': f'ASSEMBLY_{scenario}',
                'source_group_id': f'GROUP_{scenario}',
                'target_part': target_part,
                'example_image': example_image,
                'target_example_status': 'PART_CROP_FROM_MIXED_SOURCE' if target_part else 'NORMAL_REFERENCE',
                'capture_reason': 'new_misassembly_coverage' if target_part else 'new_device_control',
            })

gap_steps = []
for scenario, label, target_part, value, example in missing_states:
    part_states = dict(correct)
    if target_part:
        part_states[target_part] = value
    elif value == 'MISSING':
        part_states = {part: 'MISSING' for part in correct}
    for angle in range(0, 360, 10):
        if angle in coverage.get(scenario, []):
            continue
        gap_steps.append(dict(step_id=f'MA_{scenario}_GAP_{angle:03d}',
                             scenario_id=scenario, scenario_label=label,
                             part_states=part_states, target_engine_angle=angle,
                             target_position='CENTER', assembly_episode_id=f'ASSEMBLY_{scenario}',
                             source_group_id=f'GROUP_{scenario}', target_part=target_part,
                             example_image=example, target_example_status='NORMAL_BEFORE_REMOVAL' if value else 'NORMAL_REFERENCE',
                             capture_reason='missing_recorded_training_angle'))
# Keep NORMAL controls and gap shots together, then each missing/misassembly state.
steps = [s for s in steps if s['scenario_id'] == 'NORMAL'] + gap_steps + [s for s in steps if s['scenario_id'] != 'NORMAL']
normal_steps = sorted((s for s in steps if s['scenario_id'] == 'NORMAL'),
                      key=lambda s: (s['target_position'], s['target_engine_angle']))
steps = normal_steps + [s for s in steps if s['scenario_id'] != 'NORMAL']

plan = {
    'plan_schema_version': 1, 'policy_version': 'operator-declared-one-click-v1',
    'plan_id': 'ENGINE_MISASSEMBLY_CAPTURE_001_10DEG_GAPS_V3',
    'plan_status': 'PILOT_TARGETS_REQUIRE_PHYSICAL_REVIEW',
    'collection_purpose': 'train_candidate',
    'grouping': 'one assembly per scenario; physical independence unverified',
    'target_basis': 'User requested 10-degree full-turn coverage including normal/missing-part gaps. Existing accepted TRAIN E01/E02 covers 12 angles per state. Add missing 24 angles for each of 6 states (144), 7 misassembly states*36 angles*2 positions (504), and 6 explicit normal device controls. Total 654. Existing photos are coverage evidence, not new captures. Sufficiency unverified.',
    'existing_coverage': coverage,
    'coverage_evidence': 'existing-angle-coverage.json',
    'coverage_match_scope': 'scenario + exact recorded target angle; previous lighting conditions pooled, no independence or measured-angle claim',
    'body_direction_guide': '정상 기준처럼 긴 금색 중심축 끝이 아래, 짧은 끝이 위이면 0도입니다. 카메라를 고정하고 엔진 전체를 시계 방향으로 회전하세요. 배기구·문양 방향은 본체 회전 기준으로 쓰지 않습니다.',
    'positions': {
        'CENTER': '엔진 본체 중심을 화면 중심에 맞춤',
        'OFFSET_RIGHT': '카메라 고정, 엔진만 약간 오른쪽으로 이동; 본체 전체가 보이게',
    },
    'quality': {'version': 1, 'settle_seconds': 0.5, 'timeout_seconds': 8,
                'stable_frames': 2, 'motion_mae': 6.0, 'blur_variance': 40,
                'dark_mean': 35, 'bright_fraction': 0.25},
    'steps': steps,
    'normal_reference': {
        'path': 'normal_reference.png', 'source': 'engine_parts_CFA8507_v001/source_index.json + CFA8507BBBF384292.zip',
        'review_id': 'D001', 'split': 'train', 'capture_truth': 'NORMAL',
        'capture_human_accepted': True,
        'source_sha256': '6dc94539570259d7747d8cc2b4d5fb0ed3d782b6b5a881408f427cd80c39f561',
        'bbox_review_status': 'UNREVIEWED', 'guidance_only': True,
    },
    'limitations': [
        '오조립 설명 사진은 복합 상태이며 부품 부분 crop만 안내로 사용; 다른 부품은 NORMAL 기준',
        '사진만으로 실제 장착각 수치를 확정하지 않음',
        '목표 장수는 파일럿 계획이며 학습 충분성을 보장하지 않음',
    ],
}
(folder / 'misassembly-plan.json').write_text(
    json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
