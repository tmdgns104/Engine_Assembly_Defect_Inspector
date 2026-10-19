"""Independently audit saved recovery artifacts; never modify inputs or models."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
OUTPUT = PROJECT / 'runs/engine_preprocessing_recovery_001/v001_20261003T033452Z'
BASELINE = PROJECT / 'runs/engine_misassembly_baseline_training_001/v001_20261002T191929Z'
PARTS = ('pipe_left', 'pipe_right', 'exhaust', 'symbol')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main():
    checks = []

    def check(name, condition, detail):
        checks.append(dict(name=name, status='PASS' if condition else 'FAIL', detail=detail))
        assert condition, (name, detail)

    protected = load(OUTPUT / 'protected_hashes_before.json')
    differences = [path for path, before in protected.items()
                   if not Path(path).is_file() or sha(path) != before['sha256']]
    check('baseline_labels_models_source_preserved', not differences,
          dict(files=len(protected), changed=differences))
    sources = {split: rows(BASELINE / f'export_{split.lower()}_candidates.jsonl')
               for split in ('TRAIN', 'VALIDATION')}
    by_id = {r['capture_id']: r for group in sources.values() for r in group}
    fixed = load(OUTPUT / 'fixed_populations.json')
    check('frozen_populations', all([r['capture_id'] for r in sources[s]] == fixed[s] for s in sources),
          {s: len(r) for s, r in sources.items()})
    check('expected_counts', [len(sources[s]) for s in sources] == [694, 155], [694, 155])
    for key in ('raw_sha256', 'source_group_id', 'collection_round_id', 'lineage_root_id'):
        overlap = {r[key] for r in sources['TRAIN']} & {r[key] for r in sources['VALIDATION']}
        check('cross_split_' + key, not overlap, list(overlap))
    all_reviewed = rows(PROJECT / 'data/guided_capture_20261001/labeling_review_manifest.jsonl')
    # Hash only authorized original session paths, not discovery of protected evaluation roots.
    raw_checks = []
    for row in all_reviewed:
        path = Path(row['raw_image_path'])
        assert path.is_relative_to(PROJECT / 'data/guided_capture_20261001')
        assert 'sessions' in path.parts and 'images' in path.parts
        assert not {'E04', 'TEST_RESERVED'} & set(path.parts)
        raw_checks.append(dict(capture_id=row['capture_id'], raw_image_path=str(path),
                               sha256=sha(path), expected_sha256=row['raw_sha256']))
    check('all_original_hashes', all(x['sha256'] == x['expected_sha256'] for x in raw_checks), len(raw_checks))
    (OUTPUT / 'raw_hashes_verified.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in raw_checks), encoding='utf-8')
    unresolved = rows(PROJECT / 'data/guided_capture_20261001/labeling_unresolved_cases.jsonl')
    check('unresolved_excluded', not ({r['capture_id'] for r in unresolved} & set(by_id)), len(unresolved))
    review_by_id = {r['capture_id']: r for r in all_reviewed}
    for row in by_id.values():
        original = review_by_id[row['capture_id']]
        assert row['split'] in sources and not original['is_superseded'] and original['candidate_eligible']
        assert row['approved_part_states'] == original['approved_part_states']
        assert row['source_capture_metadata'] == original['source_capture_metadata']
        assert row['training_accepted'] is False and row['human_reviewed'] is False
    check('review_truth_provenance_and_flags_preserved', True, len(by_id))
    cfg = load(OUTPUT / 'alignment/config_frozen.json')
    old_cfg = load(BASELINE / 'alignment/config_frozen.json')
    keys = ['registration', 'min_orientation_anchor_correlation', 'crop_regions_xyxy', 'preprocessing']
    check('thresholds_rectangles_pixel_transform_unchanged', all(cfg[k] == old_cfg[k] for k in keys), keys)
    bank = cfg['reference_bank']
    check('train_only_bank', all(r['capture_id'] in fixed['TRAIN'] and r['split'] == 'TRAIN' for r in bank['references']),
          dict(references=len(bank['references']), descriptors=sum(r['descriptor_count'] for r in bank['references'])))
    check('bank_hash', sha(OUTPUT / 'alignment' / bank['path']) == bank['sha256'], bank['sha256'])
    records = rows(OUTPUT / 'preprocessing_records.jsonl')
    check('one_preprocess_record_per_source', len(records) == len(by_id) and {r['capture_id'] for r in records} == set(by_id), len(records))
    crop_count = 0
    for part in PARTS:
        for split in sources:
            manifest = rows(OUTPUT / f'{part}_{split.lower()}_crop_manifest.jsonl')
            assert len(manifest) == len(sources[split])
            assert {r['capture_id'] for r in manifest} == set(fixed[split])
            for row in manifest:
                source = by_id[row['capture_id']]
                assert row['split'] == split and row['part'] == part
                assert row['approved_state'] == source['approved_part_states'][part]
                for key in ('raw_sha256', 'source_group_id', 'collection_round_id', 'lineage_root_id', 'supersedes_capture_id'):
                    assert row[key] == source[key]
                assert row['alignment_config_sha256'] == sha(OUTPUT / 'alignment/config_frozen.json')
                if row['status'] == 'VALID':
                    assert sha(row['crop_path']) == row['crop_sha256']
                    image = cv2.imdecode(np.fromfile(row['crop_path'], dtype=np.uint8), cv2.IMREAD_COLOR)
                    assert image.shape == (224, 224, 3) and image.dtype == np.uint8
                    assert row['essential_support']['unsupported_pixels'] == 0
                    crop_count += 1
                else:
                    assert row['crop_path'] is None and row['crop_sha256'] is None
    check('all_crop_dimensions_hashes_labels_lineage_support', crop_count == 3348, crop_count)
    check('no_untracked_crop', len(list((OUTPUT / 'crops').rglob('*.png'))) == crop_count, crop_count)
    predictions = rows(OUTPUT / 'validation_predictions.jsonl')
    check('all_validation_slots', len(predictions) == 620 and len({(r['capture_id'], r['part']) for r in predictions}) == 620, len(predictions))
    metrics = load(OUTPUT / 'before_after_metrics.json')
    independent = {}
    for part in PARTS:
        mapping = load(OUTPUT / f'{part}_class_mapping.json')
        names = [mapping[str(i)] for i in range(len(mapping))]
        expected = load(BASELINE / 'full' / part / 'class_mapping.json')
        assert mapping == expected, (mapping, expected)
        selected = [r for r in predictions if r['part'] == part and r['predicted_state'] is not None]
        matrix = [[0] * len(names) for _ in names]
        for row in selected:
            assert row['model_sha256'] == sha(BASELINE / 'full' / part / 'weights/best.pt')
            assert row['approved_state'] == by_id[row['capture_id']]['approved_part_states'][part]
            assert set(row['class_scores']) == set(names)
            assert abs(sum(row['class_scores'].values()) - 1) < 1e-5
            assert row['predicted_state'] == max(row['class_scores'], key=row['class_scores'].get)
            matrix[names.index(row['approved_state'])][names.index(row['predicted_state'])] += 1
        actual = metrics['parts'][part]
        assert names == actual['class_order'] and matrix == actual['confusion_matrix_rows_true_columns_pred']
        f1_values = []
        for i, name in enumerate(names):
            tp = matrix[i][i]; support = sum(matrix[i]); predicted = sum(r[i] for r in matrix)
            precision = tp / predicted if predicted else 0
            recall = tp / support if support else 0
            f1 = 2 * tp / (support + predicted) if support + predicted else 0
            for key, value in dict(support=support, precision=precision, recall=recall, f1=f1).items():
                assert abs(actual['classes'][name][key] - value) < 1e-10
            f1_values.append(f1)
        assert abs(actual['macro_f1'] - sum(f1_values) / len(names)) < 1e-10
        for key, predicate in [('misassembled_to_correct', lambda r: r['approved_state'] not in ('CORRECT', 'MISSING')),
                               ('missing_to_correct', lambda r: r['approved_state'] == 'MISSING'),
                               ('correct_to_defective', lambda r: r['approved_state'] == 'CORRECT')]:
            subset = [r for r in selected if predicate(r)]
            numerator = sum((r['predicted_state'] != 'CORRECT' if key == 'correct_to_defective' else r['predicted_state'] == 'CORRECT') for r in subset)
            assert actual[key]['count'] == numerator and actual[key]['denominator'] == len(subset)
        independent[part] = dict(class_order=names, confusion=matrix, predicted=len(selected), macro_f1=sum(f1_values) / len(names))
    check('independent_metrics_and_weight_mapping', True, independent)
    failed = [r for r in predictions if r['predicted_state'] is None]
    check('failed_never_normal', len(failed) == 16 and all(r['class_scores'] is None and r['crop_path'] is None for r in failed), len(failed))
    changes = rows(OUTPUT / 'case_changes.jsonl')
    old_success = [r for r in changes if r['subset'] == 'original_success_110']
    check('old_110_crop_and_prediction_identical', len(old_success) == 110 and all(r['after_status'] == 'VALID' and all(p['same_input'] and p['before_prediction'] == p['after_prediction'] for p in r['parts'].values()) for r in old_success), 110)
    sims = rows(OUTPUT / 'classifier_only_simulation.jsonl')
    counts = Counter(r['simulation_output'] for r in sims)
    check('simulation_all_155', len(sims) == 155 and dict(counts) == metrics['classifier_only_simulation']['output_counts'], dict(counts))
    for row in sims:
        outputs = [r for r in predictions if r['capture_id'] == row['capture_id']]
        complete = all(r['predicted_state'] is not None for r in outputs)
        expected = 'NO_DECISION_PREPROCESSING_FAILED' if not complete else 'ALL_CORRECT' if all(r['predicted_state'] == 'CORRECT' for r in outputs) else 'DEFECT_DETECTED'
        assert row['simulation_output'] == expected
    check('baseline_reproduction', load(OUTPUT / 'baseline_reproduction_verification.json')['status'] == 'PASS', 849)
    result = dict(status='PASS', verified_at=datetime.now(timezone.utc).isoformat(), checks=checks,
                  preprocessing={s: dict(Counter(r['status'] for r in records if r['split'] == s)) for s in sources},
                  train_failed=[r['display_index'] for r in records if r['split'] == 'TRAIN' and r['status'] != 'VALID'],
                  validation_failed=[r['display_index'] for r in records if r['split'] == 'VALIDATION' and r['status'] != 'VALID'])
    (OUTPUT / 'artifact_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(status='PASS', checks=len(checks), protected_files=len(protected), raw_images=len(raw_checks), crops=crop_count)))


if __name__ == '__main__':
    main()
