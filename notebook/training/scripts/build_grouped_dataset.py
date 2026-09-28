"""Compose reviewed candidate manifests without copying or randomly splitting frames."""
import argparse
from collections import Counter
import math
from pathlib import Path

from PIL import Image
import yaml

from training.scripts.prepare_via_project import digest, read_json, write_json
from training.scripts.via_to_yolo import load_classes


GROUP_KEYS = ('origin_group_id', 'session_id', 'episode_id', 'capture_id')


def check_disjoint(train, val):
    """Reject shared acquisition groups and byte-identical images across splits."""
    overlaps = {}
    for key in GROUP_KEYS:
        left = {row['provenance'][key] for row in train}
        right = {row['provenance'][key] for row in val}
        if not all(left | right):
            raise ValueError(f'Missing acquisition identifier: {key}')
        overlaps[key] = sorted(left & right)
    overlaps['image_sha256'] = sorted({r['image_sha256'] for r in train} & {r['image_sha256'] for r in val})
    if any(overlaps.values()):
        raise ValueError(f'Train/val leakage: {overlaps}')
    return overlaps


def resolve_input_sources(row, expected_purpose):
    provenance = row['provenance']
    if provenance['purpose'] != expected_purpose or provenance['source_kind'] != 'camera':
        raise ValueError('Wrong provenance purpose or source kind.')

    if not (row['review_status'] == 'confirmed' and provenance['product_id']):
        raise ValueError('Unapproved row.')

    source_image_path = Path(row.get('source_image_absolute', provenance['image_path']))
    source_label_path = row.get('source_label_absolute')
    if source_label_path is not None:
        source_label_path = Path(source_label_path)
    return provenance, source_image_path, source_label_path


def inspect_candidates(manifest_path, expected_purpose):
    """Verify approved input hashes, originals and serialized label coordinates."""
    manifest_path = Path(manifest_path).resolve()
    manifest = read_json(manifest_path)
    if manifest['purpose'] != expected_purpose:
        raise ValueError('Candidate purpose does not match the requested split.')
    classes = load_classes(manifest)
    for path, expected in manifest['inputs_sha256'].items():
        if digest(path) != expected:
            raise ValueError(f'Approval input hash changed: {path}')
    rows = manifest['images']
    if not rows:
        raise ValueError('The split has no approved images.')

    counts = Counter()
    identities = set()
    hashes = set()

    for row in rows:
        provenance = row['provenance']

        if row['review_status'] != 'confirmed' or provenance['purpose'] != expected_purpose \
                or provenance['product_id'] != manifest['product_id'] or provenance['source_kind'] != 'camera':
            raise ValueError('Unapproved, wrong-purpose or non-camera input.')

        image = (manifest_path.parent / row['image']).resolve()
        label = (manifest_path.parent / row['label']).resolve()
        if not image.is_relative_to(manifest_path.parent / 'images') or not label.is_relative_to(manifest_path.parent / 'labels'):
            raise ValueError('Invalid image/label linkage.')
        if image.stem != label.stem:
            raise ValueError('Image/label stem mismatch.')

        identity = (provenance['collection_id'], provenance['capture_id'])
        if identity in identities or row['image_sha256'] in hashes:
            raise ValueError('Duplicate capture or image inside a split.')
        identities.add(identity)
        hashes.add(row['image_sha256'])

        source_provenance_path, source_image_path, source_label_path = resolve_input_sources(row, expected_purpose)
        source_image_sha256 = row.get('source_image_sha256', source_provenance_path['image_sha256'])
        source_label_sha256 = row.get('source_label_sha256', row['label_sha256'])

        if digest(image) != row['image_sha256']:
            raise ValueError('Cropped/transformed image hash mismatch.')
        if digest(label) != row['label_sha256']:
            raise ValueError('Cropped/transformed label hash mismatch.')
        if digest(source_image_path) != source_image_sha256:
            raise ValueError('Source image hash mismatch.')
        if source_label_path is not None and digest(source_label_path) != source_label_sha256:
            raise ValueError('Source label hash mismatch.')
        if source_provenance_path['image_sha256'] != source_image_sha256:
            raise ValueError('Provenance image hash changed.')

        with Image.open(image) as picture:
            if picture.format != 'PNG' or picture.size != (row['width'], row['height']):
                raise ValueError('PNG dimensions differ from the manifest.')
            picture.verify()

        lines = label.read_text(encoding='utf-8').splitlines()
        if len(lines) != row['object_count']:
            raise ValueError('Object count differs from the label file.')
        for line in lines:
            fields = line.split()
            if len(fields) != 5 or fields[0] not in classes:
                raise ValueError('Invalid class or label format.')
            x, y, width, height = map(float, fields[1:])
            if (not all(math.isfinite(v) for v in (x, y, width, height))
                    or not (0 < width <= 1 and 0 < height <= 1)
                    or min(x - width / 2, y - height / 2) < -1e-9
                    or max(x + width / 2, y + height / 2) > 1 + 1e-9):
                raise ValueError('Invalid normalized rectangle.')
            counts[fields[0]] += 1

        row['image_absolute'] = image.as_posix()
        row['label_absolute'] = label.as_posix()
    return manifest, dict(counts)


def build(train_path, val_path, output):
    """Write an exclusive dataset directory after all source and leakage checks pass."""
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output already exists; preserve the previous dataset version.')
    train, train_counts = inspect_candidates(train_path, 'train_candidate')
    val, val_counts = inspect_candidates(val_path, 'validation_candidate')
    if train['product_id'] != val['product_id'] or train['classes'] != val['classes']:
        raise ValueError('Product/class schemas differ between train and val.')
    overlaps = check_disjoint(train['images'], val['images'])
    shared_setup = sorted({r['provenance']['setup_id'] for r in train['images']} &
                          {r['provenance']['setup_id'] for r in val['images']})
    output.mkdir(parents=True)
    for split, manifest in (('train', train), ('val', val)):
        (output / f'{split}.txt').write_text(''.join(r['image_absolute'] + '\n' for r in manifest['images']), encoding='utf-8')
    config = {'path': output.as_posix(), 'train': 'train.txt', 'val': 'val.txt',
              'names': {item['id']: item['name'] for item in train['classes']}}
    (output / 'dataset.yaml').write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding='utf-8')
    report = {
        'status': 'PASS', 'counts': {'train': len(train['images']), 'val': len(val['images']), 'test': 0},
        'class_counts': {'train': train_counts, 'val': val_counts}, 'cross_split_overlaps': overlaps,
        'shared_calibration_setup_ids': shared_setup,
        'independence_basis': 'Existing acquisition origin groups retained. B03 physical re-preparation was human-declared; independent physical verification is not claimed. Shared setup is the retained camera calibration.',
        'similarity_limit': 'Exact bytes and acquisition boundaries checked. Similar appearance of the same product is not proof of duplicate acquisition; no broad real-world independence claim.',
        'model_input': 'Only hash-matched candidate images/labels are used for train/val; state metadata and review overlays excluded.',
        'test_status': 'B04 reserved for final evaluation, no test images read or included.',
        'roi_transforms': {
            'train_source': (Path(train_path).resolve()).name,
            'val_source': (Path(val_path).resolve()).name,
            'train_roi': train.get('roi_transform'),
            'val_roi': val.get('roi_transform'),
        },
    }
    write_json(output / 'split_manifest.json', {
        'format_version': 1, 'product_id': train['product_id'], 'split_method': 'existing_acquisition_groups',
        'random_split_seed': None, 'sources': {str(Path(p).resolve()): digest(p) for p in (train_path, val_path)},
        'train': train['images'], 'val': val['images'], 'test': [], 'test_reservation': 'B04',
    })
    write_json(output / 'leakage_check_report.json', report)
    (output / 'leakage_check_report.md').write_text(
        '# Grouped split verification\n\nPASS: approved train/val candidates verified.\n\n'
        + f"Counts: {report['counts']}. Cross-split hash/origin/session/episode/capture overlap: zero.\n\n"
        + report['independence_basis'] + '\n\n' + report['similarity_limit'] + '\n\n' + report['test_status'] + '\n', encoding='utf-8')
    write_json(output / 'dataset_integrity.json', {path.name: digest(path) for path in output.iterdir() if path.is_file()})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', required=True)
    parser.add_argument('--val', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(build(args.train, args.val, args.output))


if __name__ == '__main__':
    main()
