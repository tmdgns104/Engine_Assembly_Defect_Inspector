"""Make an unlabelled offline VIA workspace from reviewed capture exports.

This only prepares copies for human annotation. It never creates bounding boxes,
YOLO labels, split assignments, or human approval records.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image


PURPOSE_FILES = {
    'train_candidate': 'training_candidates.json',
    'validation_candidate': 'validation_candidates.json',
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def prepare(export, output, schema_path, via_html, purpose='train_candidate'):
    """Validate the selected non-test list before creating an exclusive output."""
    if purpose not in PURPOSE_FILES:
        raise ValueError('Sealed test material is not a labeling-development input.')
    export, output = Path(export).resolve(), Path(output).resolve()
    if export.parent.name != 'exports':
        raise ValueError('Expected an exports/EXPORT... directory from the capture app.')
    collection = export.parent.parent
    if output.is_relative_to(collection) or output.exists():
        raise ValueError('Use a new output folder outside the original collection.')
    schema = read_json(schema_path)
    classes = schema['classes']
    if [item['id'] for item in classes] != list(range(len(classes))):
        raise ValueError('Class IDs must be ordered consecutive integers from zero.')
    if not classes or len({item['name'] for item in classes}) != len(classes):
        raise ValueError('Class names must be nonempty and unique.')
    html = Path(via_html).read_bytes()
    if b'VGG Image Annotator' not in html:
        raise ValueError('Expected the official VIA application HTML.')
    rows = read_json(export / PURPOSE_FILES[purpose])
    # Do not read test_reserved.json. The app already separates that material.
    labelable = {item['attempt_id']: item for item in read_json(export / 'images_for_labeling.json')
                 if item['purpose'] == purpose}
    if not rows or len({item['attempt_id'] for item in rows}) != len(rows):
        raise ValueError('Candidate list must contain unique nonempty attempts.')
    checked = []
    for row in rows:
        if row != labelable.get(row['attempt_id']):
            raise ValueError('Candidate disagrees with the app labeling handoff.')
        if row['source_kind'] != 'camera' or row['purpose'] != purpose:
            raise ValueError('Only reviewed real-camera candidates of the selected purpose are allowed.')
        if row['product_id'] != schema['product_id']:
            raise ValueError('Product ID differs from the class schema.')
        source = Path(row['image_path']).resolve()
        if not source.is_relative_to(collection / 'sessions'):
            raise ValueError('Image must stay inside the collection sessions folder.')
        if digest(source) != row['image_sha256']:
            raise ValueError('Source image hash differs from the handoff.')
        with Image.open(source) as picture:
            size = picture.size
            picture.verify()
        checked.append((row, source, size))

    output.mkdir(parents=True, exist_ok=False)
    (output / 'images').mkdir()
    metadata, provenance = {}, []
    for index, (row, source, size) in enumerate(checked, 1):
        filename = f'{index:04d}.png'
        target = output / 'images' / filename
        shutil.copyfile(source, target)
        if digest(target) != row['image_sha256']:
            raise ValueError('Working image copy hash mismatch; preserve the incomplete folder for inspection.')
        image_id = filename + str(target.stat().st_size)
        metadata[image_id] = {
            'filename': filename, 'size': target.stat().st_size, 'regions': [],
            'file_attributes': {
                'review_status': 'pending',
                'capture_state': row['scenario'],
                'capture_condition': f"{row['round_id']} / {row['condition_id']} / {row['placement_id']}",
                'note': '',
            },
        }
        provenance.append({**row, 'via_image_id': image_id, 'working_image': 'images/' + filename,
                           'width': size[0], 'height': size[1]})

    project = {
        '_via_settings': {
            'project': {'name': output.name},
            'core': {'buffer_size': 4, 'filepath': {}, 'default_filepath': './images/'},
            'ui': {'image': {'region_label': 'class_id', 'region_color': 'class_id',
                             'region_label_font': '14px Sans'}},
        },
        '_via_img_metadata': metadata,
        '_via_attributes': {
            'region': {'class_id': {'type': 'dropdown', 'description': '실제 부품 종류',
                                   'options': {str(item['id']): item['display'] for item in classes},
                                   'default_options': {}}},
            'file': {
                'review_status': {'type': 'dropdown', 'description': '위치와 종류의 사람 검토',
                                  'options': {'pending': '미검토', 'confirmed': '사람 검토 완료',
                                              'needs_review': '판단 어려움 / 수정 필요'},
                                  'default_options': {'pending': True}},
                'capture_state': {'type': 'text', 'description': '촬영자가 확인한 상태 (위치 라벨 아님)', 'default_value': ''},
                'capture_condition': {'type': 'text', 'description': '촬영 회차 / 조명 / 배치', 'default_value': ''},
                'note': {'type': 'text', 'description': '모호한 경계나 수정 사유', 'default_value': ''},
            },
        },
        '_via_data_format_version': '2.0.10',
        '_via_image_id_list': list(metadata),
    }
    (output / 'via.html').write_bytes(html)
    write_json(output / 'project_initial.json', project)
    write_json(output / 'label_schema.json', schema)
    write_json(output / 'provenance.json', provenance)
    report = {
        'status': 'UNLABELLED_AWAITING_HUMAN_ANNOTATION',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_export': str(export), 'purpose': purpose,
        'source_list_sha256': digest(export / PURPOSE_FILES[purpose]),
        'via_html_sha256': digest(output / 'via.html'),
        'source_schema_sha256': digest(schema_path),
        'image_count': len(rows), 'regions': 0, 'human_reviewed': 0,
        'original_images_modified': False,
    }
    write_json(output / 'prepare-complete.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--schema', required=True, type=Path)
    parser.add_argument('--via-html', required=True, type=Path)
    parser.add_argument('--purpose', choices=PURPOSE_FILES, default='train_candidate')
    args = parser.parse_args()
    print(json.dumps(prepare(args.export, args.output, args.schema, args.via_html, args.purpose),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
