"""Convert hash-bound, human-reviewed VIA rectangles to YOLO candidates.

Product classes come from the schema. Capture states are audit metadata only.
An unreviewed or invalid object withholds its entire image, never just that box.
This creates an exclusive candidate folder; it does not assign train/val splits.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import shutil

from PIL import Image

from training.scripts.prepare_via_project import digest, read_json, write_json


DECIMAL_PLACES = 10
ALLOWED_PURPOSES = {'train_candidate', 'validation_candidate'}


def load_classes(schema):
    classes = schema['classes']
    ids = [item['id'] for item in classes]
    names = [item['name'] for item in classes]
    if (not classes or any(type(value) is not int for value in ids)
            or ids != list(range(len(ids)))):
        raise ValueError('Schema class IDs must be consecutive integers from zero.')
    if any(not isinstance(name, str) or not name.strip() for name in names) or len(set(names)) != len(names):
        raise ValueError('Schema class names must be nonempty and unique.')
    return {str(item['id']): item['name'] for item in classes}


def rectangle(region, classes, width, height):
    shape = region['shape_attributes']
    class_id = str(region['region_attributes']['class_id'])
    if class_id not in classes:
        raise ValueError('Class is not in the product schema.')
    if shape.get('name') != 'rect':
        raise ValueError('Only visible axis-aligned rectangles are supported.')
    coordinates = [shape[key] for key in ('x', 'y', 'width', 'height')]
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in coordinates):
        raise ValueError('Rectangle coordinates must be finite numbers.')
    x, y, box_width, box_height = coordinates
    if (x < 0 or y < 0 or box_width <= 0 or box_height <= 0
            or x + box_width > width or y + box_height > height):
        raise ValueError('Rectangle is outside the image or has a nonpositive size.')
    return class_id, coordinates


def yolo_line(class_id, box, width, height):
    x, y, box_width, box_height = box
    values = ((x + box_width / 2) / width, (y + box_height / 2) / height,
              box_width / width, box_height / height)
    return class_id + ' ' + ' '.join(f'{value:.{DECIMAL_PLACES}f}' for value in values)


def roundtrip_tolerance(width, height):
    # Center and size each round by <= 0.5e-10; edge error <= 0.75e-10 pixels/axis.
    return max(1e-6, max(width, height) * 10 ** -DECIMAL_PLACES)


def verify_label_file(path, regions, classes, width, height):
    """Read serialized labels and compare class/order/coordinates against VIA."""
    lines = path.read_text(encoding='utf-8').splitlines()
    if len(lines) != len(regions):
        raise ValueError('Written YOLO object count differs from VIA.')
    tolerance = roundtrip_tolerance(width, height)
    maximum_error = 0.0
    for line, region in zip(lines, regions):
        fields = line.split()
        expected_class, expected_box = rectangle(region, classes, width, height)
        if len(fields) != 5 or fields[0] != expected_class:
            raise ValueError('Written YOLO class/line format differs from VIA.')
        cx, cy, bw, bh = map(float, fields[1:])
        if not all(math.isfinite(value) for value in (cx, cy, bw, bh)) or not (0 < bw <= 1 and 0 < bh <= 1):
            raise ValueError('Written YOLO dimensions are invalid.')
        restored = ((cx - bw / 2) * width, (cy - bh / 2) * height, bw * width, bh * height)
        x, y, box_width, box_height = restored
        if (x < -tolerance or y < -tolerance or x + box_width > width + tolerance
                or y + box_height > height + tolerance):
            raise ValueError('Written YOLO rectangle is outside the image.')
        error = max(abs(actual - expected) for actual, expected in zip(restored, expected_box))
        if error > tolerance:
            raise ValueError('YOLO to VIA roundtrip exceeds the declared pixel tolerance.')
        maximum_error = max(maximum_error, error)
    return maximum_error


def capture_stem(row):
    parts = [row['collection_id'], row['capture_id']]
    if any(not isinstance(part, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,119}', part)
           for part in parts):
        raise ValueError('Collection/capture IDs must be safe bounded filename components.')
    return '__'.join(parts)


def check_review_record(record, project_path, schema_path, provenance_path, image_ids):
    for key, path in (('reviewed_project', project_path), ('schema', schema_path), ('provenance', provenance_path)):
        if record[key]['sha256'] != digest(path):
            raise ValueError(f'Human review record does not bind the current {key} hash.')
    approved = record['approved_image_ids']
    deferred = record['deferred_image_ids']
    if (len(set(approved)) != len(approved) or len(set(deferred)) != len(deferred)
            or not set(approved + deferred).issubset(image_ids) or set(approved) & set(deferred)):
        raise ValueError('Human review scope has duplicate, unknown, or conflicting image IDs.')
    if not record.get('user_statement') or not record.get('recorded_at'):
        raise ValueError('Human review requires an explicit statement and recording time.')
    return set(approved), set(deferred)


def convert(project_path, schema_path, provenance_path, review_path, original_root, output,
            purpose='train_candidate'):
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError('Only train/validation candidates are allowed; final test stays reserved.')
    project_path, schema_path, provenance_path, review_path, original_root, output = (
        Path(path).resolve() for path in
        (project_path, schema_path, provenance_path, review_path, original_root, output))
    workspace = project_path.parent
    if output.exists() or output.is_relative_to(original_root) or output.is_relative_to(workspace):
        raise ValueError('Use a new output directory outside originals and the VIA workspace.')
    input_hashes = {str(path): digest(path) for path in (project_path, schema_path, provenance_path, review_path)}
    project, schema, rows, record = (read_json(path) for path in
                                    (project_path, schema_path, provenance_path, review_path))
    classes = load_classes(schema)
    metadata = project['_via_img_metadata']
    image_ids = project['_via_image_id_list']
    if (not image_ids or len(set(image_ids)) != len(image_ids) or set(image_ids) != set(metadata)
            or len(rows) != len(metadata) or len({row['via_image_id'] for row in rows}) != len(rows)
            or {row['via_image_id'] for row in rows} != set(metadata)):
        raise ValueError('VIA and provenance must contain the same unique image IDs.')
    via_options = project['_via_attributes']['region']['class_id']['options']
    if set(via_options) != set(classes):
        raise ValueError('VIA class IDs differ from the product schema.')
    approved, deferred = check_review_record(record, project_path, schema_path, provenance_path, set(image_ids))
    # Metadata preflight precedes all image reads, especially for sealed test rows.
    stems = set()
    for row in rows:
        if row['purpose'] != purpose or row['source_kind'] != 'camera' or row['product_id'] != schema['product_id']:
            raise ValueError('Candidate purpose, real-camera source, or product differs from the requested scope.')
        if not row.get('round_id') or not row.get('origin_group_id'):
            raise ValueError('Capture round and origin group are required; never invent them.')
        stem = capture_stem(row).casefold()
        if stem in stems:
            raise ValueError('Capture filename collision (including Windows case-insensitivity).')
        stems.add(stem)

    checked, withheld = [], []
    for row in rows:
        image_id = row['via_image_id']
        item = metadata[image_id]
        source = Path(row['image_path']).resolve()
        working = (workspace / row['working_image']).resolve()
        if not source.is_relative_to(original_root / 'sessions') or not working.is_relative_to(workspace / 'images'):
            raise ValueError('Source/working image is outside its allowed image directory.')
        if working.name != item['filename'] or working.stat().st_size != item['size']:
            raise ValueError('VIA filename/size differs from the working image.')
        if digest(source) != row['image_sha256'] or digest(working) != row['image_sha256']:
            raise ValueError('Original/working image hash differs from provenance.')
        if source.suffix.lower() != '.png':
            raise ValueError('Expected a provenance-bound original PNG.')
        with Image.open(source) as picture:
            width, height = picture.size
            if picture.format != 'PNG' or (width, height) != (row['width'], row['height']):
                raise ValueError('Actual PNG dimensions differ from provenance.')
            picture.verify()
        regions, reasons = item['regions'], []
        if item['file_attributes'].get('review_status') != 'confirmed' or image_id not in approved or image_id in deferred:
            reasons.append('Image is not fully human-confirmed in this project and review record.')
        if not isinstance(regions, list) or not regions:
            reasons.append('No completed object labels; this is not an approved background image.')
        else:
            for index, region in enumerate(regions):
                try:
                    if region.get('region_attributes', {}).get('review_status', 'confirmed') != 'confirmed':
                        reasons.append(f'Region {index}: object review is incomplete; withhold the whole image.')
                    rectangle(region, classes, width, height)
                except (KeyError, TypeError, ValueError) as error:
                    reasons.append(f'Region {index}: {error}')
        if reasons:
            withheld.append({'via_image_id': image_id, 'filename': item['filename'],
                             'capture_id': row['capture_id'], 'reasons': reasons, 'provenance': row})
        else:
            checked.append((row, source, working, regions, width, height))

    output.mkdir(parents=True, exist_ok=False)
    (output / 'images').mkdir()
    (output / 'labels').mkdir()
    candidates, counts, maximum_error = [], Counter(), 0.0
    for row, source, working, regions, width, height in checked:
        stem = capture_stem(row)
        image_path, label_path = output / 'images' / f'{stem}.png', output / 'labels' / f'{stem}.txt'
        with source.open('rb') as original, image_path.open('xb') as target:
            shutil.copyfileobj(original, target)
        with label_path.open('x', encoding='utf-8', newline='\n') as target:
            for region in regions:
                class_id, box = rectangle(region, classes, width, height)
                target.write(yolo_line(class_id, box, width, height) + '\n')
                counts[class_id] += 1
        if digest(image_path) != row['image_sha256']:
            raise ValueError('Written image copy hash mismatch; preserve incomplete output for inspection.')
        maximum_error = max(maximum_error, verify_label_file(label_path, regions, classes, width, height))
        candidates.append({
            'via_image_id': row['via_image_id'], 'filename': metadata[row['via_image_id']]['filename'],
            'image': image_path.relative_to(output).as_posix(), 'label': label_path.relative_to(output).as_posix(),
            'image_sha256': digest(image_path), 'label_sha256': digest(label_path),
            'width': width, 'height': height, 'object_count': len(regions), 'review_status': 'confirmed',
            'provenance': row,  # Capture state/removals are audit data, never YOLO features/classes.
        })
    # Recheck inputs after writing. A concurrent edit must not produce a PASS result.
    for path, expected_hash in input_hashes.items():
        if digest(path) != expected_hash:
            raise ValueError('Input changed during conversion; output is not verified.')
    for row in rows:
        if (digest(row['image_path']) != row['image_sha256']
                or digest(workspace / row['working_image']) != row['image_sha256']):
            raise ValueError('Original/working image changed during conversion.')
    manifest = {'format_version': 1, 'product_id': schema['product_id'], 'purpose': purpose,
                'classes': schema['classes'], 'inputs_sha256': input_hashes, 'images': candidates}
    write_json(output / 'candidate_manifest.json', manifest)
    write_json(output / 'withheld_images.json', withheld)
    # Read the final manifest too, rather than treating an in-memory result as a saved artifact.
    saved = read_json(output / 'candidate_manifest.json')
    for candidate in saved['images']:
        for key in ('image', 'label'):
            if digest(output / candidate[key]) != candidate[key + '_sha256']:
                raise ValueError('Saved manifest does not match its output file.')
    if len(list((output / 'images').iterdir())) != len(candidates) or len(list((output / 'labels').iterdir())) != len(candidates):
        raise ValueError('Output image/label correspondence failed.')
    result = {
        'status': 'PASS' if not withheld else 'INCOMPLETE_WITH_WITHHELD_IMAGES',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'input_images': len(rows), 'converted_images': len(candidates), 'withheld_images': len(withheld),
        'objects': sum(counts.values()), 'class_counts': dict(sorted(counts.items())),
        'yolo_decimal_places': DECIMAL_PLACES, 'maximum_roundtrip_error_pixels': maximum_error,
        'roundtrip_tolerance_pixels': 'max(1e-6, max(image_width, image_height) * 1e-10)',
        'checks': {'source_and_working_hashes_preserved': True, 'input_hashes_preserved': True,
                   'actual_output_pairs_and_hashes': True, 'class_geometry_and_roundtrip': True,
                   'whole_image_review_gate': True, 'provenance_round_origin_preserved': True},
        'origin_groups': sorted({row['provenance']['origin_group_id'] for row in candidates}),
        'dataset_split_ready': False,
        'semantic_acceptance_basis': 'Human review record; geometry verification does not establish semantic accuracy.',
    }
    write_json(output / 'conversion_validation.json', result)
    return read_json(output / 'conversion_validation.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('project', 'schema', 'provenance', 'review-record', 'original-root', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--purpose', choices=sorted(ALLOWED_PURPOSES), default='train_candidate')
    args = parser.parse_args()
    result = convert(args.project, args.schema, args.provenance, args.review_record,
                     args.original_root, args.output, args.purpose)
    print(f"{result['status']}: {result['converted_images']} images, {result['objects']} objects, "
          f"{result['withheld_images']} withheld")
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
