"""Read only allowlisted accepted TRAIN metadata and hashes; never open E04 images."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label_root', type=Path)
    parser.add_argument('raw_root', type=Path)
    args = parser.parse_args()
    index_path = args.label_root / 'source_index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    allowed = {row['capture_id']: row for row in index['rows']
               if row['split'] == 'train' and row['round_id'] in ('E01', 'E02')
               and row['purpose'] == 'train_candidate' and row['capture_human_accepted']
               and not row['test_reserved'] and not row['rejected']}
    saved, intents = {}, {}
    events = args.raw_root / 'collection-events.jsonl'
    # Select event type and exact top-level capture/attempt ID before deserializing.
    with events.open('rb') as source:
        for line in source:
            if b'"type": "attempt_saved"' not in line:
                continue
            match = re.search(rb'"capture_id":\s*"([^"]+)"', line)
            if match and match[1].decode('ascii') in allowed:
                event = json.loads(line)
                saved[event['data']['record']['capture_id']] = event['data']
    attempt_ids = {data['attempt_id'] for data in saved.values()}
    with events.open('rb') as source:
        for line in source:
            if b'"type": "attempt_intent"' not in line:
                continue
            match = re.search(rb'"attempt_id":\s*"([^"]+)"', line)
            if match and match[1].decode('ascii') in attempt_ids:
                data = json.loads(line)['data']
                assert data['round_id'] in ('E01', 'E02') and data['purpose'] == 'train_candidate'
                intents[data['attempt_id']] = data
    evidence, coverage = [], {}
    for capture_id, row in allowed.items():
        record = saved[capture_id]['record']
        intent = intents[saved[capture_id]['attempt_id']]
        assert record['scenario'] == row['scenario_capture_truth'] == intent['scenario']
        assert record['image_sha256'] == row['image_sha256']
        assert record['object_configuration']['expected_counts'] == row['expected_counts']
        raw = args.raw_root / Path(row['image_member']).relative_to(args.raw_root.name)
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == row['image_sha256']
        angle = intent['target_angle_deg']
        assert angle == intent['engine_metadata']['target_engine_angle_deg']
        scenario = row['scenario_capture_truth']
        coverage.setdefault(scenario, set()).add(angle)
        evidence.append(dict(capture_id=capture_id, scenario_id=scenario, target_engine_angle=angle,
                             round_id=row['round_id'], split='train', raw_sha256=row['image_sha256'],
                             origin_group_id=row['origin_group_id'], condition_id=intent['condition_id'],
                             label_source='existing_capture_human_accepted', measured_angle=None))
    result = dict(scope='accepted TRAIN E01/E02 only; state and recorded target angle coverage; conditions pooled',
                  source_index_sha256=hashlib.sha256(index_path.read_bytes()).hexdigest(),
                  coverage={key: sorted(value) for key, value in coverage.items()}, evidence=evidence,
                  matching_policy='same scenario and exact recorded target angle; no interpolation; no measured-angle claim',
                  excluded='validation, test_reserved, E04, rejected, unaccepted',
                  existing_images_bundled=False)
    (Path(__file__).parent/'existing-angle-coverage.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(accepted_train_rows=len(evidence), coverage=result['coverage']), ensure_ascii=False))


if __name__ == '__main__':
    main()
