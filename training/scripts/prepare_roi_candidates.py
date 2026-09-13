"""Create fixed-ROI candidate sets for train/validation from reviewed YOLO candidates.

The script transforms source images/labels from an existing split manifest into a new
candidate workspace. It keeps the same image identity fields and updates label/geometry
for the fixed ROI.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from training.scripts.prepare_via_project import digest, read_json, write_json


DEFAULT_ROI = (287, 168, 863, 628)
DEFAULT_SOURCE_SIZE = (1280, 720)


def yolo_to_xyxy(class_id: int, x: float, y: float, w: float, h: float, width: int, height: int):
    x1 = (x - w / 2) * width
    y1 = (y - h / 2) * height
    x2 = (x + w / 2) * width
    y2 = (y + h / 2) * height
    return class_id, x1, y1, x2, y2


def xyxy_to_yolo(x1: float, y1: float, x2: float, y2: float, width: int, height: int):
    bw = (x2 - x1) / width
    bh = (y2 - y1) / height
    cx = (x1 + x2) / (2 * width)
    cy = (y1 + y2) / (2 * height)
    return cx, cy, bw, bh


def clip_box_to_roi(box: tuple[float, float, float, float], roi: tuple[int, int, int, int]):
    x1, y1, x2, y2 = box
    r_x1, r_y1, r_x2, r_y2 = roi
    clipped = (max(x1, r_x1), max(y1, r_y1), min(x2, r_x2), min(y2, r_y2))
    if clipped[2] <= clipped[0] or clipped[3] <= clipped[1]:
        return None
    return clipped


def transform_manifest(split_manifest_path: Path, split_name: str, output_dir: Path,
                     roi: tuple[int, int, int, int], schema_path: Path) -> dict:
    split_manifest = read_json(Path(split_manifest_path).resolve())
    rows = split_manifest.get(split_name)
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'Missing or empty split rows for {split_name}')

    if split_name not in {'train', 'val'}:
        raise ValueError('split_name must be train or val')

    expected_purpose = 'train_candidate' if split_name == 'train' else 'validation_candidate'
    for row in rows:
        if row.get('review_status') != 'confirmed':
            raise ValueError(f'Row not confirmed: {row.get("via_image_id")}')
        if row['provenance'].get('purpose') != expected_purpose:
            raise ValueError(f'Wrong row purpose for {split_name}: {row.get("via_image_id")}')

    source_sizes = {(row['provenance'].get('width'), row['provenance'].get('height')) for row in rows}
    if source_sizes != {tuple(DEFAULT_SOURCE_SIZE)}:
        raise ValueError(f'Unexpected source sizes: {sorted(source_sizes)}')

    manifest_schema = read_json(Path(schema_path).resolve())
    if 'classes' not in manifest_schema:
        raise ValueError('Schema must contain classes')

    output = Path(output_dir).resolve()
    if output.exists():
        raise ValueError('Output already exists; provide a fresh folder for ROI conversion')
    (output / 'images').mkdir(parents=True)
    (output / 'labels').mkdir()

    r_x1, r_y1, r_x2, r_y2 = roi
    roi_w = r_x2 - r_x1
    roi_h = r_y2 - r_y1
    if roi_w <= 0 or roi_h <= 0:
        raise ValueError('ROI width/height must be positive')

    transformed_rows = []
    conversion_log = []
    class_counts = Counter()
    clipping_examples = []

    for row in rows:
        source_image = Path(row['image_absolute']).resolve()
        source_label = Path(row['label_absolute']).resolve()

        if digest(source_image) != row['image_sha256']:
            raise ValueError(f'Image hash mismatch: {source_image}')
        if digest(source_label) != row['label_sha256']:
            raise ValueError(f'Label hash mismatch: {source_label}')

        output_name = Path(row['image']).name
        output_image = output / 'images' / output_name
        output_label = output / 'labels' / output_name.replace('.png', '.txt')

        with Image.open(source_image) as picture:
            if picture.size != DEFAULT_SOURCE_SIZE:
                raise ValueError(f'Expected source size {DEFAULT_SOURCE_SIZE} but got {picture.size} for {row["via_image_id"]}')
            cropped = picture.crop((r_x1, r_y1, r_x2, r_y2))
            if cropped.size != (roi_w, roi_h):
                raise ValueError('Crop shape mismatch')
            cropped.save(output_image)

        source_lines = [line.strip() for line in source_label.read_text(encoding='utf-8').splitlines() if line.strip()]
        out_lines = []
        kept = dropped = clipped = 0

        for line in source_lines:
            fields = line.split()
            if len(fields) != 5:
                raise ValueError(f'Invalid YOLO label line in {source_label}: {line}')
            class_id = int(fields[0])
            x, y, w, h = map(float, fields[1:])
            _, x1, y1, x2, y2 = yolo_to_xyxy(class_id, x, y, w, h, DEFAULT_SOURCE_SIZE[0], DEFAULT_SOURCE_SIZE[1])
            clipped_box = clip_box_to_roi((x1, y1, x2, y2), roi)
            if clipped_box is None:
                dropped += 1
                continue

            c_x1, c_y1, c_x2, c_y2 = clipped_box
            clipped_now = (c_x1 == r_x1 or c_y1 == r_y1 or c_x2 == r_x2 or c_y2 == r_y2)
            if clipped_now:
                clipped += 1
                clipping_examples.append({
                    'via_image_id': row['via_image_id'],
                    'class_id': class_id,
                    'source_box_xyxy': [x1, y1, x2, y2],
                    'clipped_box_xyxy': [c_x1, c_y1, c_x2, c_y2],
                })

            shifted = (c_x1 - r_x1, c_y1 - r_y1, c_x2 - r_x1, c_y2 - r_y1)
            cx, cy, bw, bh = xyxy_to_yolo(*shifted, width=roi_w, height=roi_h)
            if not (0 < bw <= 1 and 0 < bh <= 1 and 0 <= cx <= 1 and 0 <= cy <= 1):
                raise ValueError(f'Normalized ROI box out of bounds: {row["via_image_id"]}')
            out_lines.append(f'{class_id} {cx:.10f} {cy:.10f} {bw:.10f} {bh:.10f}')
            kept += 1
            class_counts[str(class_id)] += 1

        output_label.write_text('\n'.join(out_lines) + ('\n' if out_lines else ''), encoding='utf-8')

        conversion_log.append({'via_image_id': row['via_image_id'], 'kept': kept, 'dropped': dropped, 'clipped': clipped})

        transformed_rows.append({
            'via_image_id': row['via_image_id'],
            'filename': row['filename'],
            'image': f'images/{output_name}',
            'label': f'labels/{output_name.replace(".png", ".txt")}',
            'image_absolute': str(output_image.resolve()),
            'label_absolute': str(output_label.resolve()),
            'source_image_absolute': row['image_absolute'],
            'source_label_absolute': row['label_absolute'],
            'source_image_sha256': row['provenance']['image_sha256'],
            'source_label_sha256': row['label_sha256'],
            'image_sha256': digest(output_image),
            'label_sha256': digest(output_label),
            'width': roi_w,
            'height': roi_h,
            'object_count': len(out_lines),
            'review_status': 'confirmed',
            'provenance': row['provenance'],
            'roi_source': {'x1': r_x1, 'y1': r_y1, 'x2': r_x2, 'y2': r_y2},
            'roi_transform_mode': 'clip',
        })

    source_hashes = {
        str(path): digest(Path(path))
        for path in split_manifest.get('sources', {})
    }

    if len(transformed_rows) != len(rows):
        raise ValueError('Transformation dropped image rows; expected one output per input')

    input_objects = sum(row['object_count'] for row in rows)
    output_objects = sum(row['object_count'] for row in transformed_rows)
    dropped_objects = sum(item['dropped'] for item in conversion_log)
    clipped_objects = sum(item['clipped'] for item in conversion_log)

    candidate_payload = {
        'format_version': 1,
        'product_id': manifest_schema['product_id'],
        'purpose': expected_purpose,
        'classes': manifest_schema['classes'],
        'inputs_sha256': source_hashes,
        'images': transformed_rows,
        'roi_transform': {
            'source': {'width': DEFAULT_SOURCE_SIZE[0], 'height': DEFAULT_SOURCE_SIZE[1]},
            'roi_xyxy': {'x1': r_x1, 'y1': r_y1, 'x2': r_x2, 'y2': r_y2},
            'roi_size': {'width': roi_w, 'height': roi_h},
            'mode': 'clip',
            'input_objects': input_objects,
            'output_objects': output_objects,
            'dropped_objects': dropped_objects,
            'clipped_objects': clipped_objects,
        },
    }
    write_json(output / 'candidate_manifest.json', candidate_payload)
    write_json(output / 'roi_transform_report.json', {
        'status': 'PASS',
        'split': split_name,
        'purpose': expected_purpose,
        'source_rows': len(rows),
        'output_rows': len(transformed_rows),
        'source_objects': input_objects,
        'output_objects': output_objects,
        'dropped_objects': dropped_objects,
        'clipped_objects': clipped_objects,
        'class_counts': dict(sorted(class_counts.items())),
        'roi': {'x1': r_x1, 'y1': r_y1, 'x2': r_x2, 'y2': r_y2, 'width': roi_w, 'height': roi_h},
        'transform_mode': 'clip',
        'generated_at': datetime.now(timezone.utc).isoformat(),
    })
    write_json(output / 'roi_transform_conversion_log.json', conversion_log)
    write_json(output / 'roi_transform_clipped_examples.json', {'items': clipping_examples[:200]})

    return {
        'status': 'PASS',
        'split': split_name,
        'source_rows': len(rows),
        'output_rows': len(transformed_rows),
        'source_object_count': input_objects,
        'output_object_count': output_objects,
        'dropped_objects': dropped_objects,
        'clipped_objects': clipped_objects,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split-manifest', required=True)
    parser.add_argument('--split', choices=('train', 'val'), required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--roi', nargs=4, type=int, default=DEFAULT_ROI)
    parser.add_argument('--schema', default='training/datasets/proxy/earbud_case_v0/label_schema.json')
    args = parser.parse_args()

    report = transform_manifest(
        split_manifest_path=Path(args.split_manifest),
        split_name=args.split,
        output_dir=Path(args.output),
        roi=tuple(args.roi),
        schema_path=Path(args.schema),
    )
    print(report)


if __name__ == '__main__':
    main()
