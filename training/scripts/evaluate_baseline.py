"""Save validation predictions and explicit fixed-threshold TP/FP/FN evidence."""
import argparse
from collections import Counter
from pathlib import Path

from ultralytics import YOLO

from training.scripts.prepare_via_project import digest, read_json, write_json


def intersection_over_union(left, right):
    x1, y1 = max(left[0], right[0]), max(left[1], right[1])
    x2, y2 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_left = (left[2] - left[0]) * (left[3] - left[1])
    area_right = (right[2] - right[0]) * (right[3] - right[1])
    return intersection / (area_left + area_right - intersection)


def match_detections(predictions, targets, iou_threshold=0.5):
    """Match in confidence order, at most one same-class target per prediction."""
    unmatched = set(range(len(targets)))
    matches, false_positives = [], []
    for prediction_index in sorted(range(len(predictions)), key=lambda i: predictions[i]['confidence'], reverse=True):
        prediction = predictions[prediction_index]
        candidates = [(intersection_over_union(prediction['xyxy'], targets[i]['xyxy']), i)
                      for i in unmatched if targets[i]['class_id'] == prediction['class_id']]
        best_iou, target_index = max(candidates, default=(0.0, -1))
        if best_iou >= iou_threshold:
            unmatched.remove(target_index)
            matches.append({'prediction_index': prediction_index, 'target_index': target_index, 'iou': best_iou})
        else:
            false_positives.append(prediction_index)
    return {'matches': matches, 'false_positive_indices': false_positives, 'false_negative_indices': sorted(unmatched)}


def evaluate(experiment, prediction_name='validation_predictions'):
    experiment = Path(experiment).resolve()
    baseline = read_json(experiment / 'baseline_result.json')
    if baseline['status'] != 'COMPLETE':
        raise ValueError('Baseline training has not completed.')
    if Path(prediction_name).name != prediction_name or prediction_name in ('.', '..'):
        raise ValueError('Prediction name must be one directory component.')
    output = experiment / prediction_name
    if output.exists() or (experiment / 'validation_error_analysis.json').exists():
        raise ValueError('Prediction evidence already exists; preserve it.')
    config = baseline['requested_config']
    data_path = Path(config['data'])
    split = read_json(data_path.parent / 'split_manifest.json')
    if digest(data_path.parent / 'split_manifest.json') != baseline['split_sha256']:
        raise ValueError('Split changed since training.')
    rows = split['val']
    by_path = {str(Path(row['image_absolute']).resolve()).casefold(): row for row in rows}
    for row in rows:
        if digest(row['image_absolute']) != row['image_sha256'] or digest(row['label_absolute']) != row['label_sha256']:
            raise ValueError('Validation input changed.')
    checkpoint = baseline['checkpoints']['best.pt']
    if digest(checkpoint['path']) != checkpoint['sha256']:
        raise ValueError('Best checkpoint changed.')
    model = YOLO(checkpoint['path'])
    prediction_config = dict(imgsz=config['imgsz'], batch=config['batch'], device=config['device'],
                             conf=0.25, iou=0.7, max_det=300, augment=False, quantize=32,
                             save=True, project=str(experiment), name=output.name, exist_ok=False)
    results = model.predict(source=[row['image_absolute'] for row in rows], stream=True, **prediction_config)
    details = []
    counts = Counter()
    per_class = {str(key): Counter() for key in model.names}
    for result in results:
        row = by_path[str(Path(result.path).resolve()).casefold()]
        predictions = [{'class_id': int(box.cls.item()), 'confidence': float(box.conf.item()),
                        'xyxy': box.xyxy[0].cpu().tolist()} for box in result.boxes]
        targets = []
        for line in Path(row['label_absolute']).read_text(encoding='utf-8').splitlines():
            class_id, x, y, width, height = map(float, line.split())
            targets.append({'class_id': int(class_id), 'xyxy': [(x - width / 2) * row['width'],
                            (y - height / 2) * row['height'], (x + width / 2) * row['width'],
                            (y + height / 2) * row['height']]})
        matching = match_detections(predictions, targets)
        counts.update(tp=len(matching['matches']), fp=len(matching['false_positive_indices']), fn=len(matching['false_negative_indices']))
        for match in matching['matches']:
            per_class[str(targets[match['target_index']]['class_id'])]['tp'] += 1
        for index in matching['false_positive_indices']:
            per_class[str(predictions[index]['class_id'])]['fp'] += 1
        for index in matching['false_negative_indices']:
            per_class[str(targets[index]['class_id'])]['fn'] += 1
        details.append({'filename': row['filename'], 'capture_id': row['provenance']['capture_id'],
                        'round_id': row['provenance']['round_id'], 'condition_id': row['provenance']['condition_id'],
                        'prediction_image': str(output / Path(result.path).with_suffix('.jpg').name),
                        'predictions': predictions, 'targets': targets, **matching})
    if len(details) != len(rows) or not all(Path(row['prediction_image']).is_file() for row in details):
        raise ValueError('Some prediction images were not saved.')
    report = {
        'status': 'PASS', 'split': 'validation', 'rounds': sorted({r['round_id'] for r in details}),
        'test_reservation': split['test_reservation'], 'images': len(details),
        'checkpoint': checkpoint, 'prediction_config': prediction_config, 'matching_iou': 0.5,
        'counts': dict(counts), 'per_class': {key: dict(value) for key, value in per_class.items()},
        'metric_note': 'These are confidence=0.25 class-aware IoU>=0.5 counts. Baseline P/R use the framework validation operating point; AP integrates the confidence curve.',
        'error_filenames': [r['filename'] for r in details if r['false_positive_indices'] or r['false_negative_indices']],
        'images_detail': details,
    }
    write_json(experiment / 'validation_error_analysis.json', report)
    print({key: value for key, value in report.items() if key != 'images_detail'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--prediction-name', default='validation_predictions')
    args = parser.parse_args()
    evaluate(args.experiment, args.prediction_name)
