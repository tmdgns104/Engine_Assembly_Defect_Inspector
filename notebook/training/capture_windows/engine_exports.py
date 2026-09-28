"""Verified annotation handoffs and metadata-only station merging.

Exports are immutable snapshots outside raw/. No box, mask, image transform or
training labels are manufactured here. Original PNGs are only read for validation.
"""
from collections import Counter
from copy import deepcopy
import csv
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from training.scripts import capture_proxy as capture
from .guide import read_json
from .wizard_store import write_new_json
from . import engine_dataset as engine
from .engine_contract import (ANNOTATION_FIELDS, make_contract, semantic_contract,
    render_human_contract, render_labeling_rules, render_summary, dataset_statistics)

QUEUE_FIELDS = ('capture_id', 'image_path', 'image_sha256', 'scenario', 'expected_counts', 'removed_slots',
                'reference_normal_capture_id', 'engine_angle_target_deg', 'crank_phase_id', 'lighting_id',
                'station_id', 'capture_pc_id', 'camera_id', 'split', 'round_id', 'test_reserved')
CSV_FIELDS = ('filename', 'capture_id', 'station_id', 'split', 'capture_truth_result', 'defect_type', 'defect_part',
              'scenario', 'engine_angle_deg', 'crank_phase_id', 'lighting_id', 'reference_normal_capture_id',
              'human_review_status', 'exclude_from_training', 'test_reserved')


def write_jsonl(path, rows):
    capture.plain_path(Path(path))
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')


def read_jsonl(path):
    capture.plain_path(Path(path))
    return [json.loads(line, object_pairs_hook=capture.unique_json_object)
            for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def queue_row(row):
    item = {key: deepcopy(row[key]) for key in QUEUE_FIELDS}
    item.update(engine_angle=row['engine_angle_target_deg'], crank_phase=row['crank_phase_id'], lighting=row['lighting_id'])
    return item


def queues_for(rows, unlocked=False, similar_distance=2):
    eligible = [r for r in rows if r['labeling_ready'] and (unlocked or not r['test_reserved'])]
    yolo = [queue_row(r) for r in eligible if r['yolo_label_required']]
    masks = [queue_row(r) for r in engine.select_mask_candidates(rows, similar_distance=similar_distance)]
    pairs = []
    for row in eligible:
        if row['capture_truth_result'] != 'FAIL':
            continue
        pairs.append({'defect_capture_id': row['capture_id'], 'normal_capture_id': row['reference_normal_capture_id'],
                      **{k: row[k] for k in ('scenario', 'defect_type', 'defect_part', 'station_id', 'round_id',
                                            'lighting_id', 'engine_angle_target_deg', 'crank_phase_id')}})
    return yolo, masks, pairs


def csv_row(row):
    return {key: (Path(row['image_path']).name if key == 'filename' else row['engine_angle_target_deg'] if key == 'engine_angle_deg'
                  else row.get(key)) for key in CSV_FIELDS}


def validate_manifest(rows, profile, verify_raw=True, reject_duplicate_hashes=False):
    """Fail closed on inconsistent GT, split, identity, reference or raw bytes."""
    seen, hashes = {}, {}
    for row in rows:
        required = {*QUEUE_FIELDS, 'raw_capture_id', 'raw_relative_path', 'raw_root', 'capture_truth_source',
                    'capture_truth_result', 'defect_type', 'defect_part', 'session_id', 'collection_id', 'setup_id',
                    'purpose', 'engine_angle_id', 'engine_angle_human_confirmed', 'angle_sensor_verified',
                    'crank_phase_target_deg', 'crank_phase_human_confirmed', 'crank_sensor_verified',
                    'captured_at', 'quality_metrics', 'human_review_status', 'labeling_ready',
                    'exclude_from_training', 'yolo_label_required', 'anomaly_mask_candidate', 'source_kind'}
        if not isinstance(row, dict) or not required <= set(row) or set(ANNOTATION_FIELDS) & set(row):
            raise ValueError('GT manifest 필드 누락 또는 Codex annotation 필드 혼입')
        if row['capture_id'] in seen:
            raise ValueError('duplicate capture_id')
        if row['capture_id'] != row['station_id']+'__'+row['raw_capture_id']:
            raise ValueError('Station namespace/capture_id 불일치')
        engine.validate_station({k: row[k] for k in ('station_id', 'capture_pc_id', 'camera_id', 'e02_lighting_id')})
        wanted = engine.truth_fields(profile, row['scenario'])
        if any(row[k] != value for k, value in wanted.items()):
            raise ValueError('Scenario와 capture_truth/expected_counts/removed_slots 의미 불일치')
        expected_split = {'E01': 'train_candidate', 'E02': 'train_candidate', 'E03': 'validation_candidate', 'E04': 'test_reserved'}.get(row['round_id'], 'excluded')
        if row['split'] != expected_split or row['test_reserved'] != (expected_split == 'test_reserved'):
            raise ValueError('회차/split/test_reserved 불일치')
        if row['split'] != 'excluded' and row['purpose'] != row['split']:
            raise ValueError('purpose/split 불일치')
        if row['scenario'] in engine.CHALLENGES and (row['purpose'] != 'review_challenge' or row['split'] != 'excluded'):
            raise ValueError('Challenge가 Main에 혼입됨')
        for key in ('angle_sensor_verified', 'crank_sensor_verified'):
            if row[key] is not False:
                raise ValueError('실제 각도 센서 검증을 주장할 수 없습니다.')
        for key in ('engine_angle_human_confirmed', 'crank_phase_human_confirmed', 'test_reserved', 'exclude_from_training', 'labeling_ready'):
            if type(row[key]) is not bool:
                raise ValueError('사람 확인/정책 필드는 bool이어야 합니다.')
        if (row['crank_phase_id'] not in engine.CRANK_PHASES or row['crank_phase_target_deg'] != int(row['crank_phase_id'][-3:])
                or row['engine_angle_id'] != f"ANGLE_{row['engine_angle_target_deg']:03d}"):
            raise ValueError('목표각도 ID/값 불일치')
        if row['test_reserved'] and (row['exclude_from_training'] is not True or row['anomaly_mask_candidate'] is not False):
            raise ValueError('E04 학습/기본 Mask 보호 위반')
        expected_exclusion = not (row['split'] == 'train_candidate' and row['human_review_status'] == 'ACCEPT' and row['source_kind'] == 'camera')
        if row['exclude_from_training'] != expected_exclusion:
            raise ValueError('training 제외 정책 불일치')
        if row['source_kind'] not in ('camera', 'sample') or row['human_review_status'] not in ('ACCEPT', 'PENDING', 'REVIEW', 'RETAKE'):
            raise ValueError('입력/사람 검토 상태 오류')
        root, path = Path(row['raw_root']).resolve(), Path(row['image_path']).resolve()
        relative = Path(row['raw_relative_path'])
        if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root) or path != (root/relative).resolve():
            raise ValueError('원본 root/상대경로 불일치')
        if not relative.parts or relative.parts[0] != row['station_id']:
            raise ValueError('원본 Station 폴더 불일치')
        if verify_raw:
            capture.plain_path(path)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['image_sha256']:
                raise ValueError('Raw image SHA256 불일치 또는 파일 없음: '+str(path))
        if reject_duplicate_hashes and row['image_sha256'] in hashes:
            raise ValueError('duplicate image hash / hash collision: '+row['capture_id'])
        seen[row['capture_id']] = row
        hashes[row['image_sha256']] = row['capture_id']
    for row in rows:
        reference = seen.get(row['reference_normal_capture_id'])
        if row['scenario'] == 'NORMAL':
            if row['reference_normal_capture_id'] != row['capture_id']:
                raise ValueError('NORMAL은 자기 capture_id를 참조해야 합니다.')
        elif reference is not None:
            if reference['scenario'] != 'NORMAL' or engine.pair_key(reference) != engine.pair_key(row) or reference['human_review_status'] != 'ACCEPT':
                raise ValueError('잘못된 NORMAL Pair: angle/crank/station/setup/split/검토 확인 필요')
        elif row['reference_normal_capture_id'] is not None:
            raise ValueError('manifest에 없는 NORMAL 참조')
        ready = (row['split'] != 'excluded' and row['human_review_status'] == 'ACCEPT' and reference is not None
                 and row['source_kind'] == 'camera' and row['engine_angle_human_confirmed'] and row['crank_phase_human_confirmed'])
        if row['labeling_ready'] != ready:
            raise ValueError('labeling_ready와 실제 Reference/검토 상태 불일치')
    return seen


def validate_export(folder, verify_raw=True):
    folder = Path(folder)
    contract = read_json(folder/'LABELING_CONTRACT.json')
    inputs = read_json(folder/'product_and_plan.json')
    expected = make_contract(inputs['profile'], inputs['template'], contract['raw_root'], contract['annotation_root'],
                             unlocked=not contract['test_reserved_policy']['locked'])
    if contract != expected:
        raise ValueError('LABELING_CONTRACT와 공통 의미 사전이 다릅니다.')
    rows = read_jsonl(folder/'dataset_manifest.jsonl')
    validate_manifest(rows, inputs['profile'], verify_raw=verify_raw)
    by_round = {r['id']: r for r in inputs['template']['rounds']}
    for row in rows:
        if row['split'] == 'excluded':
            continue
        schedule = inputs['template']['crank_schedule'][row['round_id']]
        wanted_phase = next((g['crank_phase_id'] for g in schedule if row['engine_angle_id'] in g['placement_ids']), None)
        if row['crank_phase_id'] != wanted_phase:
            raise ValueError('manifest와 회차별 Crank/Engine angle 계획이 다릅니다.')
        condition = by_round[row['round_id']]['condition_id']
        wanted_light = row['e02_lighting_id'] if condition == 'ASYMMETRIC' else condition
        if row['lighting_id'] != wanted_light:
            raise ValueError('manifest와 Main 조명 계획이 다릅니다.')
    yolo, masks, pairs = queues_for(rows, not contract['test_reserved_policy']['locked'],
                                   inputs['quality_rules']['similar_hash_distance'])
    for name, wanted in [('annotation_queue_yolo', yolo), ('annotation_queue_mask', masks), ('normal_defect_pairs', pairs)]:
        if read_jsonl(folder/(name+'.jsonl')) != wanted:
            raise ValueError(name+'와 Dataset 의미/행 연결 불일치')
    selected = {r['capture_id'] for r in masks}
    if any(row['anomaly_mask_candidate'] != (row['capture_id'] in selected) for row in rows):
        raise ValueError('manifest의 Mask 후보와 실제 Queue 불일치')
    stats = dataset_statistics(rows, yolo, masks, pairs)
    if read_json(folder/'dataset_statistics.json') != stats:
        raise ValueError('Dataset 집계 불일치')
    documents = {'HUMAN_CODEX_DATASET_CONTRACT_KO.md': render_human_contract(contract),
                 'LABELING_RULES_KO.md': render_labeling_rules(contract), 'DATASET_SUMMARY_KO.md': render_summary(contract, stats)}
    for name, expected_text in documents.items():
        if (folder/name).read_text(encoding='utf-8') != expected_text:
            raise ValueError(name+'와 Machine-readable metadata의 의미 불일치')
    with (folder/'labels.csv').open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        csv_rows = list(reader)
    expected_csv = [{k: '' if v is None else str(v) for k,v in csv_row(row).items()} for row in rows]
    if reader.fieldnames != list(CSV_FIELDS) or csv_rows != expected_csv:
        raise ValueError('labels.csv와 촬영 Ground Truth 불일치')
    training = read_jsonl(folder/'training_candidates.jsonl')
    if training != [queue_row(r) for r in rows if r['labeling_ready'] and not r['exclude_from_training']]:
        raise ValueError('training export 정책 위반')
    return stats


def write_handoff(destination, rows, profile, template, quality_rules, raw_root, annotation_root, unlocked=False):
    destination = Path(destination)
    capture.plain_path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    contract = make_contract(profile, template, raw_root, annotation_root, unlocked)
    yolo, masks, pairs = queues_for(rows, unlocked, quality_rules['similar_hash_distance'])
    mask_ids = {r['capture_id'] for r in masks}
    for row in rows:
        row['anomaly_mask_candidate'] = row['capture_id'] in mask_ids
    stats = dataset_statistics(rows, yolo, masks, pairs)
    write_new_json(destination/'LABELING_CONTRACT.json', contract)
    write_new_json(destination/'product_and_plan.json', {'profile': profile, 'template': template, 'quality_rules': quality_rules})
    write_new_json(destination/'dataset_statistics.json', stats)
    for name, items in [('dataset_manifest', rows), ('annotation_queue_yolo', yolo), ('annotation_queue_mask', masks),
                        ('normal_defect_pairs', pairs), ('training_candidates', [queue_row(r) for r in rows if r['labeling_ready'] and not r['exclude_from_training']])]:
        write_jsonl(destination/(name+'.jsonl'), items)
    for name, content in [('HUMAN_CODEX_DATASET_CONTRACT_KO.md', render_human_contract(contract)),
                          ('LABELING_RULES_KO.md', render_labeling_rules(contract)), ('DATASET_SUMMARY_KO.md', render_summary(contract, stats))]:
        with (destination/name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    with (destination/'labels.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_row(row) for row in rows)
    validate_export(destination)
    return destination


def write_contact_sheets(destination, rows, unlocked=False):
    """Read allowed originals and render a separate JPEG; never edit raw PNGs."""
    root = Path(destination)/'contact_sheets'
    root.mkdir()
    groups = {}
    for row in rows:
        if row['split'] == 'excluded' or row['human_review_status'] != 'ACCEPT' or (row['test_reserved'] and not unlocked):
            continue
        groups.setdefault((row['station_id'], row['round_id'], row['scenario']), []).append(row)
    index = []
    for (station, rnd, scenario), group in sorted(groups.items()):
        sheet = Image.new('RGB', (1200, math.ceil(len(group)/3)*270), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(group):
            x, y = (i%3)*400, (i//3)*270
            with Image.open(row['image_path']) as original:
                thumb = original.convert('RGB')
            thumb.thumbnail((384, 194))
            sheet.paste(thumb, (x+8, y+8))
            draw.text((x+8,y+204), f"angle {row['engine_angle_target_deg']} / {row['crank_phase_id']}", fill='black')
            identifier = row['capture_id']
            draw.text((x+8,y+220), '\n'.join(identifier[j:j+54] for j in range(0,len(identifier),54)), fill='black')
        name = f'{station}_{rnd}_{scenario}.jpg'
        with (root/name).open('xb') as stream:
            sheet.save(stream, format='JPEG', quality=90)
        index.append({'filename': name, 'capture_ids': [r['capture_id'] for r in group]})
    write_new_json(root/'index.json', index)


def export_collection(collection, contact_sheets=False):
    from .wizard import new_id
    raw_root = collection.folder.parents[2]
    dataset_root = raw_root.parent
    station = collection.info['station']['station_id']
    destination = dataset_root/'exports'/station/collection.info['collection_id']/new_id('EXPORT')
    rows = engine.metadata_rows(collection)
    for row in rows:
        row['raw_root'] = str(raw_root)
        row['raw_relative_path'] = Path(row['image_path']).relative_to(raw_root).as_posix()
    try:
        write_handoff(destination, rows, collection.profile, collection.template, collection.rules,
                      raw_root, dataset_root/'annotations', collection.final_test_unlocked)
        if contact_sheets:
            write_contact_sheets(destination, rows, collection.final_test_unlocked)
        manifests = dataset_root/'manifests'
        capture.plain_path(manifests)
        manifests.mkdir(exist_ok=True)
        write_jsonl(manifests/(station.lower()+'_'+destination.name+'.jsonl'), rows)
        for stage in ('draft', 'reviewed'):
            for kind in ('yolo', 'masks'):
                folder = dataset_root/'annotations'/stage/kind
                capture.plain_path(folder)
                folder.mkdir(parents=True, exist_ok=True)
        write_new_json(destination/'EXPORT_VERIFIED.json', {'status': 'PASS', 'raw_modified': False, 'annotation_status': 'NOT_STARTED'})
        collection._record('export_created', {'folder': str(destination), 'human_labeling_required': True})
    except Exception as exc:
        raise capture.CaptureError(f'Engine 인계 검증 실패. 부분 파일 보존: {destination}: {exc}') from exc
    return destination


def merge_manifests(inputs, output, profile, station_roots=None):
    """Merge verified rows without moving files or modifying split/GT fields.

    roots optionally maps station -> transported raw root (containing STATION_X).
    Only path-location fields are rebased; all source manifests remain untouched.
    """
    station_roots = station_roots or {}
    rows = []
    for path in inputs:
        for original in read_jsonl(path):
            row = deepcopy(original)
            if row['station_id'] in station_roots:
                root = Path(station_roots[row['station_id']]).resolve()
                relative = Path(row['raw_relative_path'])
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('수송 원본 상대경로 오류')
                row['raw_root'] = str(root)
                row['image_path'] = str(root/relative)
            rows.append(row)
    validate_manifest(rows, profile, reject_duplicate_hashes=True)
    rows.sort(key=lambda row: (row['station_id'], row['capture_id']))
    output = Path(output).absolute()
    capture.plain_path(output)
    if any(output.resolve() == Path(path).resolve() for path in inputs):
        raise ValueError('입력 manifest를 덮어쓸 수 없습니다.')
    if any(output.is_relative_to(Path(row['raw_root'])) for row in rows):
        raise ValueError('Combined manifest는 raw 외부에 저장하세요.')
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, rows)
    # Re-read the artifact, not just the in-memory calculation.
    persisted = read_jsonl(output)
    if persisted != rows:
        raise ValueError('Combined manifest 저장 후 대조 실패')
    return {'captures': len(rows), 'stations': dict(Counter(r['station_id'] for r in rows)),
            'splits': dict(Counter(r['split'] for r in rows)), 'raw_modified': False}
