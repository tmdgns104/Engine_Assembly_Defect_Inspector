"""One bilingual vocabulary for the operator UI and future annotation handoff.

Human documents are generated views of this contract, not separately maintained
descriptions. Export verification regenerates them and rejects any divergence.
"""
from collections import Counter
from copy import deepcopy

from .engine_dataset import CLASSES, CRANK_PHASES, MAIN_SCENARIOS, CHALLENGES, truth_fields

PRODUCT_NAME = 'Engine Model Top View Dataset V1'
CLASS_LABELS = {'gray_pipe': '회색 파이프', 'exhaust_top': '상단 배기구', 'symbol_module': '문양 모듈'}
SCENARIO_LABELS = {
    'NORMAL': '정상', 'MISSING_PIPE_LEFT': '왼쪽 파이프 누락', 'MISSING_PIPE_RIGHT': '오른쪽 파이프 누락',
    'MISSING_EXHAUST_TOP': '상단 배기구 누락', 'MISSING_SYMBOL_MODULE': '문양 모듈 누락',
    'MISSING_ALL_TARGETS': '검사 대상 전체 누락',
    'LIGHT_LEFT_WEAK': '왼쪽 조명 약함', 'LIGHT_RIGHT_WEAK': '오른쪽 조명 약함', 'BOTH_TOO_DIM': '양쪽 조명 너무 어두움',
    'OCCLUSION': '가림', 'POSITION_OUT_OF_RANGE': '기준 위치 크게 이탈', 'OTHER_PART_MISSING': '비검사 부품 누락',
    'CONVEYOR_MOVING': 'Conveyor 이동 Pilot (예약·비활성)',
}
LIGHT_LABELS = {'BALANCED': '양쪽 균형 조명', 'LEFT_DOMINANT': '왼쪽 우세 · 좌100 / 우약70',
                'RIGHT_DOMINANT': '오른쪽 우세 · 좌약70 / 우100',
                **{key: SCENARIO_LABELS[key] for key in ('LIGHT_LEFT_WEAK', 'LIGHT_RIGHT_WEAK', 'BOTH_TOO_DIM')}}
BOX_RULES = {
    'gray_pipe': '보이는 회색 파이프 하나당 box 1개. 정상 2개, 한쪽 누락 1개, 전체 누락 0개. 파이프 그림자는 포함하지 않음.',
    'exhaust_top': '보이는 회색 상단 배기구 전체를 box 1개로 표시.',
    'symbol_module': '검은 문양이 붙은 회색 모듈 전체를 box 1개로 표시. 문양만 따로 box하지 않음.',
}
MASK_RULES = {
    'missing_part': '동일 조건 NORMAL Reference에서 해당 부품이 차지하던 Slot/Expected Region을 anomaly 영역으로 표시. 없는 부품의 실루엣을 상상해서 그리지 않음.',
    'alignment': '목표 각도가 같아도 실제 위치는 다를 수 있음. 두 원본을 보고 대응 영역을 확인하고 정합이 불확실하면 needs_review.',
    'format': 'black=normal(0), white=anomaly(255). single-channel PNG, 원본 이미지와 동일 width/height.',
    'scope': 'missing-object anomaly region 평가용(MVTec LOCO 스타일). 실제 부품 실루엣 분할 정답이라는 의미가 아님.',
}
PROHIBITIONS = [
    'raw 이미지 crop/resize/overwrite/rename 금지', 'Scenario만 보고 box 위치 추측 금지',
    '없는 부품에 fake box 생성 금지', 'Test Reserved 자동 열람 금지',
    '가림/경계 불명/불확실한 box 또는 mask는 needs_review',
    'generated annotation에는 annotation_source, annotation_version, confidence, needs_review 기록',
    'Human Ground Truth를 Codex 추론으로 덮어쓰지 않음',
]
GROUND_TRUTH_FIELDS = ['capture_truth_*', 'scenario', 'removed_slots', 'expected_counts',
                       'engine_angle_human_confirmed', 'crank_phase_human_confirmed', 'human_review_status']
ANNOTATION_FIELDS = ['annotation_source', 'annotation_version', 'confidence', 'bbox', 'mask', 'needs_review']


def scenario_instruction(profile, scenario):
    truth = truth_fields(profile, scenario)
    counts = ', '.join(f'{CLASS_LABELS[name]} {count}' for name,count in truth['expected_counts'].items())
    removed = ', '.join(truth['removed_slots']) or '없음'
    return (f"{SCENARIO_LABELS[scenario]} [{scenario}] · 촬영 Ground Truth {truth['capture_truth_result']}. "
            f'남길 수량: {counts}. 제거 슬롯: {removed}. 다른 부품은 모두 복원하세요. '
            '부품 상태·Crank를 유지하며 해당 Engine 목표각도로 돌리고 손을 빼세요.')


def validate_guide_meaning(profile, guide):
    expected = [{'scenario': name, 'instruction': scenario_instruction(profile, name)} for name in MAIN_SCENARIOS]
    if guide['steps'] != expected:
        raise ValueError('사람용 촬영 안내와 machine Scenario/수량 의미가 다릅니다.')


def semantic_contract(profile, plan):
    from training.scripts.capture_proxy import validate_profile
    from .engine_dataset import validate_crank_schedule
    validate_profile(profile)
    validate_crank_schedule(plan)
    if profile['objects'] != CLASSES or set(profile['scenarios']) != set(MAIN_SCENARIOS):
        raise ValueError('UI/metadata 클래스 또는 Main Scenario 계약이 다릅니다.')
    expected_slots = {'NORMAL': [], 'MISSING_PIPE_LEFT': ['PIPE_LEFT'], 'MISSING_PIPE_RIGHT': ['PIPE_RIGHT'],
                      'MISSING_EXHAUST_TOP': ['EXHAUST_TOP'], 'MISSING_SYMBOL_MODULE': ['SYMBOL_MODULE'],
                      'MISSING_ALL_TARGETS': ['PIPE_LEFT', 'PIPE_RIGHT', 'EXHAUST_TOP', 'SYMBOL_MODULE']}
    if any(profile['scenarios'][key]['removed_slots'] != slots for key,slots in expected_slots.items()):
        raise ValueError('Scenario 이름과 물리적 제거 슬롯의 의미가 다릅니다.')
    return {
        'product_name_ko': PRODUCT_NAME,
        'classes': [{'id': i, 'name': name, 'label_ko': CLASS_LABELS[name]} for i, name in enumerate(CLASSES)],
        'class_ids': {name: i for i, name in enumerate(CLASSES)},
        'scenarios': {name: {'label_ko': SCENARIO_LABELS[name], **truth_fields(profile, name),
                            'purpose': 'motion_pilot' if name == 'CONVEYOR_MOVING' else 'review_challenge' if name in CHALLENGES else 'main',
                            'enabled': name != 'CONVEYOR_MOVING'} for name in (*MAIN_SCENARIOS, *CHALLENGES)},
        'crank_phases': {name: {'target_deg': int(name[-3:]), 'label_ko': f'손잡이 {int(name[-3:])}도'} for name in CRANK_PHASES},
        'lighting': deepcopy(LIGHT_LABELS), 'rounds': deepcopy(plan['rounds']),
        'crank_schedule': deepcopy(plan['crank_schedule']),
        'human_ground_truth_fields': GROUND_TRUTH_FIELDS, 'codex_annotation_fields': ANNOTATION_FIELDS,
        'box_rules': BOX_RULES, 'mask_rules': MASK_RULES,
        'image_level_label_rules': 'Scenario 기반 촬영자 Ground Truth. NORMAL=PASS, 5종 누락=FAIL, Challenge=REVIEW. ERROR는 시스템 Fault Test이며 이미지 Scenario/label이 아님.',
        'prohibitions': PROHIBITIONS,
        'defect_types_active': ['NONE', 'MISSING_PART', 'MULTIPLE_MISSING'],
        'defect_types_reserved': ['WRONG_POSITION', 'WRONG_ORIENTATION', 'WRONG_PART', 'EXTRA_PART', 'SURFACE_DEFECT'],
        'reference_pair_contract': {
            'match_fields': ['station_id', 'capture_pc_id', 'camera_id', 'collection_id', 'setup_id', 'round_id',
                             'lighting_id', 'engine_angle_target_deg', 'crank_phase_id', 'split'],
            'normal_reference': 'self capture_id', 'fail_reference': 'current human-accepted NORMAL in the same conditions',
            'missing_reference': 'labeling_ready=false; excluded from queues',
            'retake_policy': 'old raw retained; re-export resolves current accepted reference; previous exports are historical snapshots',
        },
    }


def make_contract(profile, plan, raw_root, annotation_root, unlocked=False):
    return {'contract_schema_version': 1, **semantic_contract(profile, plan),
            'raw_root': str(raw_root), 'annotation_root': str(annotation_root),
            'dataset_manifest': 'dataset_manifest.jsonl', 'yolo_queue': 'annotation_queue_yolo.jsonl',
            'mask_queue': 'annotation_queue_mask.jsonl', 'pair_manifest': 'normal_defect_pairs.jsonl',
            'test_reserved_policy': {'locked': not unlocked, 'unlock_phrase': 'UNLOCK FINAL TEST LABELING',
                'training_forbidden': True, 'tuning_forbidden': True,
                'default_exclusions': ['yolo_queue', 'mask_queue', 'pair_manifest', 'contact_sheets', 'training_export'],
                'unlocked_scope': 'explicit final-test YOLO labeling only; default E03 mask selection unchanged'},
            'annotation_status': 'NOT_STARTED', 'quality_thresholds': deepcopy(plan['quality']),
            'quality_policy': 'Pilot 조정용 잠정 보조 기준. 경고가 있어도 삭제하지 않으며 사람이 ACCEPT/RETAKE/REVIEW.',
            'review_status_labels_ko': {'ACCEPT': '사람 승인', 'RETAKE': '재촬영 · 원본 보존', 'REVIEW': '검토 보류 · 원본 보존', 'PENDING': '사람 검토 대기'},
            'capture_id_policy': 'station_id + __ + raw_capture_id; image_path retains the immutable original filename',
            'manifest_path_policy': 'absolute image_path plus raw_relative_path; merge --station-root can rebase transported raw trees'}


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |',
                      *['| '+' | '.join(str(v).replace('|', '/') for v in row)+' |' for row in rows]])


def render_human_contract(contract):
    text = '# Human ↔ Codex Dataset 공통 계약\n\n'
    text += contract['product_name_ko']+'\n\n촬영자가 확인한 사실과 Codex annotation은 별도 필드·폴더에 저장합니다.\n\n'
    text += '## 클래스 이름 대응\n\n'+table(['화면', 'class', 'id'], [(c['label_ko'], c['name'], c['id']) for c in contract['classes']])
    text += '\n\n## Scenario와 촬영 Ground Truth\n\n'+table(
        ['화면', 'machine id', 'GT', 'defect_type', 'defect_part', 'expected_counts', 'removed_slots', 'purpose'],
        [(v['label_ko'], k, v['capture_truth_result'], v['defect_type'], v['defect_part'],
          ', '.join(f'{name}={n}' for name,n in v['expected_counts'].items()), ', '.join(v['removed_slots']) or '없음', v['purpose'])
         for k,v in contract['scenarios'].items()])
    text += '\n\nLEFT/RIGHT는 엔진 0° 기준의 물리 슬롯이며 회전 후 화면 좌우가 아닙니다. AI 클래스는 gray_pipe 하나입니다.\n'
    text += '\n## 손잡이 목표 대응\n\n'+table(['화면', 'machine id', '목표각도'], [(v['label_ko'], k, v['target_deg']) for k,v in contract['crank_phases'].items()])
    text += '\n\nEngine angle과 Crank phase는 사람이 맞춘 목표입니다. human_confirmed는 사람 확인이며 angle_sensor_verified=false / crank_sensor_verified=false입니다.\n'
    text += '\n## 조명 대응\n\n'+table(['화면', 'lighting_id'], [(v,k) for k,v in contract['lighting'].items()])
    text += '\n\n## 사실과 추론의 경계\n\n'
    text += '- Human Ground Truth: '+', '.join(contract['human_ground_truth_fields'])+'\n'
    text += '- Codex Annotation: '+', '.join(contract['codex_annotation_fields'])+'\n'
    text += '- annotation_status=NOT_STARTED. 이번 도구는 box/mask를 생성하지 않습니다.\n'
    text += '\n'+contract['image_level_label_rules']+'\n'
    text += '\n## NORMAL Pair\n\n조건 키: '+', '.join(contract['reference_pair_contract']['match_fields'])+'.\n'
    text += '정상은 자기 capture_id, FAIL은 현재 사람이 승인한 NORMAL을 참조합니다. 없으면 labeling_ready=false입니다. 재촬영 후에는 새 export를 사용하세요. 실제 정합 불확실성은 annotation에서 needs_review로 남깁니다.\n'
    text += '\n## 원본과 라벨 위치\n\nraw_root: '+contract['raw_root']+'\n\nannotation_root: '+contract['annotation_root']+'\n'
    text += '\n## Test Reserved\n\nE04 lock: '+('LOCKED' if contract['test_reserved_policy']['locked'] else 'EXPLICITLY UNLOCKED FOR LABELING')+'\n'
    text += 'E04 학습·튜닝 금지. UNLOCK FINAL TEST LABELING을 직접 실행하기 전에는 Codex 열람·라벨링 대상에서 제외합니다.\n'
    text += '\n## 일치 검증\n\n이 문서는 LABELING_CONTRACT.json에서 생성됩니다. 문서·manifest·Queue·Pair의 의미 또는 행 연결이 다르면 export 검증 실패입니다. 수동 수정 대신 공통 계약을 수정하고 재생성하세요.\n'
    return text


def render_labeling_rules(contract):
    text = '# 라벨링 규칙\n\n'+contract['image_level_label_rules']+'\n'
    for cls in contract['classes']:
        text += f"\n## Class {cls['id']}: {cls['name']} ({cls['label_ko']})\n\n{contract['box_rules'][cls['name']]}\n"
    text += '\n누락 부품은 box 없음. 가림/경계 불명은 needs_review입니다.\n\n## Missing Part Pixel Mask\n'
    for rule in contract['mask_rules'].values():
        text += '\n- '+rule+'\n'
    text += '\n## 금지·기록 규칙\n'
    for rule in contract['prohibitions']:
        text += '\n- '+rule+'\n'
    return text


def dataset_statistics(rows, yolo, masks, pairs):
    main = [r for r in rows if r['split'] in ('train_candidate', 'validation_candidate', 'test_reserved') and r['human_review_status'] == 'ACCEPT']
    return {'manifest_rows': len(rows), 'main_accepted': len(main), 'by_round': dict(Counter(r['round_id'] for r in main)),
            'by_scenario': dict(Counter(r['scenario'] for r in main)), 'by_station': dict(Counter(r['station_id'] for r in main)),
            'yolo_queue': len(yolo), 'mask_candidates': len(masks), 'normal_defect_pairs': len(pairs),
            'challenge_rows': sum(r['purpose'] == 'review_challenge' for r in rows),
            'pilot_rows': sum(r['purpose'] == 'pilot' for r in rows),
            'camera_rows': sum(r['source_kind'] == 'camera' for r in rows),
            'sample_rows': sum(r['source_kind'] == 'sample' for r in rows)}


def render_summary(contract, statistics):
    text = '# Dataset 요약\n\n'+contract['product_name_ko']+'\n\n'
    text += '## 계획 (Station당)\n\n'
    text += 'Main 288장 = 6 Scenario × 48장. E01 Train 72 + E02 Train 72 + E03 Validation 72 + E04 Test Reserved 72.\n'
    text += 'Train 144 / Validation 72 / Test 72. A/B 두 Station이면 Main 576장. 기준2장·Pilot12장·Challenge는 Main 제외.\n'
    text += '기본 YOLO 목표 216장, E03 FAIL mask 후보 목표 40장(5 Scenario × 8). 검토 대기·reference 누락·근접 중복이 있으면 실제 Queue는 줄어듭니다.\n'
    text += '\n## Crank 분산\n\n'
    text += table(['Round', 'Crank', 'Engine 목표각도'], [(rnd, g['crank_phase_id'], ', '.join(str(int(a[-3:])) for a in g['placement_ids']))
        for rnd, groups in contract['crank_schedule'].items() for g in groups])
    text += '\n\n촬영 순서: Round → Lighting → Scenario → Crank Phase → 해당 각도. E02 기본 A=LEFT_DOMINANT / B=RIGHT_DOMINANT, 시작 시 변경 가능.\n'
    text += '\n## 현재 export 실제 집계\n\n'+table(['항목', '값'], list(statistics.items()))+'\n'
    text += '\n합성 sample은 실제 촬영이 아니며 annotation/training Queue에서 제외합니다. 원본과 과거 export는 보존하며 최신 검증 export를 사용하세요.\n'
    text += '\nE04: '+('LOCKED' if contract['test_reserved_policy']['locked'] else '명시적 라벨링 unlock')+' · 학습/튜닝 금지 유지.\n'
    text += '\n품질: '+contract['quality_policy']+'\n'
    text += '\n실제 Bounding Box/Pixel Mask 생성: 0 (annotation_status=NOT_STARTED).\n'
    return text
