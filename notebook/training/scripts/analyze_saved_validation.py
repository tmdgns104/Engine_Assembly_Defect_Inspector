"""Analyze existing validation detections only: no model load, inference or training."""
import argparse
import csv
from pathlib import Path
import shutil
import statistics

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from training.scripts.prepare_via_project import digest, read_json, write_json


def box_iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return intersection / ((a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection)


def distribution(values):
    if not values:
        return None
    return dict(zip(('min', 'p10', 'median', 'p90', 'max'), map(float, np.percentile(values, [0, 10, 50, 90, 100]))), mean=float(statistics.mean(values)))


def summary(images, objects):
    confidences = [p['confidence'] for image in images for p in image['predictions']]
    ious = [row['iou'] for row in objects]
    return {'images': len(images), 'objects': sum(len(i['targets']) for i in images),
            'predictions': len(confidences), 'matched_objects': len(objects),
            'confidence': distribution(confidences), 'iou': distribution(ious),
            'iou_below_0_5': sum(v < .5 for v in ious), 'iou_below_0_75': sum(v < .75 for v in ious),
            'iou_below_0_85': sum(v < .85 for v in ious), 'iou_below_0_9': sum(v < .9 for v in ious),
            'fp': sum(len(i['false_positive_indices']) for i in images),
            'fn': sum(len(i['false_negative_indices']) for i in images)}


def render_review(rows, output):
    """New scientific review cards: actual original, GT/pred overlay, saved prediction."""
    output.mkdir()
    (output / 'originals').mkdir()
    (output / 'predictions').mkdir()
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
    cards = []
    for row in rows:
        stem = f"{Path(row['filename']).stem}_{row['class']}"
        original_path = Path(row['original_image'])
        prediction_path = Path(row['prediction_image'])
        shutil.copyfile(original_path, output / 'originals' / original_path.name)
        shutil.copyfile(prediction_path, output / 'predictions' / prediction_path.name)
        original = Image.open(original_path).convert('RGB')
        predicted = Image.open(prediction_path).convert('RGB')
        # A common context crop shows the entire case and nearby background; never model input.
        case = row['context_box']
        crop = (max(0, int(case[0])-45), max(0, int(case[1])-45), min(original.width, int(case[2])+45), min(original.height, int(case[3])+45))
        overlay = original.copy()
        draw = ImageDraw.Draw(overlay)
        draw.rectangle(row['target_box'], outline='#00ff50', width=2)
        draw.rectangle(row['prediction_box'], outline='#ff00dc', width=2)
        card = Image.new('RGB', (1350, 510), 'white')
        draw = ImageDraw.Draw(card)
        draw.text((12, 5), f"{row['filename']} {row['class']}  IoU={row['iou']:.4f} conf={row['confidence']:.4f}  {row['condition']} / {row['placement']} / {row['scenario']}", fill='black', font=font)
        for index, (picture, title) in enumerate(((original, 'Original context'), (overlay, 'GT green / prediction magenta'), (predicted, 'Existing saved prediction'))):
            panel = picture.crop(crop)
            panel.thumbnail((440, 440))
            card.paste(panel, (index*450+(450-panel.width)//2, 65))
            draw.text((index*450+12, 36), title, fill='black', font=font)
        card.save(output / f'{stem}.png')
        row['review_card'] = str((output / f'{stem}.png').resolve())
        cards.append(card)
    pages = []
    for start in range(0, len(cards), 3):
        page = Image.new('RGB', (1350, 510*len(cards[start:start+3])), 'white')
        for index, card in enumerate(cards[start:start+3]):
            page.paste(card, (0, 510*index))
        path = output / f'page_{start//3+1:02d}.png'
        page.save(path)
        pages.append(str(path.resolve()))
    return pages


def analyze(experiment, split_path):
    experiment, split_path = Path(experiment).resolve(), Path(split_path).resolve()
    output = experiment / 'error_analysis_detailed.json'
    review = experiment / 'error_review_v001'
    if output.exists() or review.exists():
        raise ValueError('Analysis already exists; retain it instead of overwriting.')
    baseline = read_json(experiment / 'baseline_result.json')
    saved = read_json(experiment / 'validation_error_analysis.json')
    split = read_json(split_path)
    # Only declared validation provenance is dereferenced. No test rows/images are read.
    val = split['val']
    by_capture = {row['provenance']['capture_id']: row for row in val}
    assert len(by_capture) == len(val) == saved['images'] == 60
    assert digest(split_path) == baseline['split_sha256']
    dataset = read_json(Path(next(iter(split['sources']))))
    names = {item['id']: item['name'] for item in dataset['classes']}
    sources = [experiment/'BASELINE_REPORT.md', experiment/'baseline_result.json',
               experiment/'validation_error_analysis.json', experiment/'baseline/results.csv', split_path,
               Path(saved['checkpoint']['path'])]
    original_hashes = {str(path): digest(path) for path in sources}
    assert digest(saved['checkpoint']['path']) == saved['checkpoint']['sha256']
    objects, images = [], saved['images_detail']
    for image in images:
        provenance_row = by_capture[image['capture_id']]
        provenance = provenance_row['provenance']
        assert provenance['purpose'] == 'validation_candidate' and provenance['round_id'] == 'B03'
        assert digest(provenance['image_path']) == provenance_row['image_sha256']
        original_hashes[provenance['image_path']] = provenance_row['image_sha256']
        original_hashes[image['prediction_image']] = digest(image['prediction_image'])
        image.update(condition=provenance['condition_id'], placement=provenance['placement_id'], scenario=provenance['scenario'])
        assert len(image['matches']) + len(image['false_negative_indices']) == len(image['targets'])
        assert len(image['matches']) + len(image['false_positive_indices']) == len(image['predictions'])
        context_box = [min(t['xyxy'][0] for t in image['targets']), min(t['xyxy'][1] for t in image['targets']),
                       max(t['xyxy'][2] for t in image['targets']), max(t['xyxy'][3] for t in image['targets'])]
        for match in image['matches']:
            target = image['targets'][match['target_index']]
            prediction = image['predictions'][match['prediction_index']]
            assert target['class_id'] == prediction['class_id']
            iou = box_iou(target['xyxy'], prediction['xyxy'])
            assert abs(iou-match['iou']) < 1e-12
            box = target['xyxy']
            objects.append({'filename': image['filename'], 'capture_id': image['capture_id'],
                            'condition': image['condition'], 'placement': image['placement'], 'scenario': image['scenario'],
                            'class': names[target['class_id']], 'class_id': target['class_id'],
                            'confidence': prediction['confidence'], 'iou': iou, 'target_box': box,
                            'prediction_box': prediction['xyxy'], 'edge_delta_pixels': [p-t for p,t in zip(prediction['xyxy'], box)],
                            'target_size_original': [box[2]-box[0], box[3]-box[1]],
                            'target_size_at_640': [(box[2]-box[0])*.5, (box[3]-box[1])*.5],
                            'original_image': provenance['image_path'], 'prediction_image': image['prediction_image'], 'context_box': context_box})
    groups = {}
    for field in ('condition', 'placement', 'scenario'):
        groups[field] = {value: summary([i for i in images if i[field]==value], [o for o in objects if o[field]==value])
                         for value in sorted({i[field] for i in images})}
    # Class groups count only that class's targets/predictions, and images containing either.
    def class_summary(class_id, condition=None):
        subset = []
        for image in images:
            if condition is not None and image['condition'] != condition:
                continue
            targets = [t for t in image['targets'] if t['class_id']==class_id]
            predictions = [p for p in image['predictions'] if p['class_id']==class_id]
            if not targets and not predictions:
                continue
            subset.append({'targets': targets, 'predictions': predictions,
                'false_positive_indices': [i for i in image['false_positive_indices'] if image['predictions'][i]['class_id']==class_id],
                'false_negative_indices': [i for i in image['false_negative_indices'] if image['targets'][i]['class_id']==class_id]})
        return summary(subset, [o for o in objects if o['class_id']==class_id and (condition is None or o['condition']==condition)])
    groups['class'] = {name: class_summary(key) for key,name in names.items()}
    groups['condition_class'] = {condition: {name: class_summary(key, condition) for key,name in names.items()} for condition in groups['condition']}
    low_iou = sorted(objects, key=lambda row:(row['iou'],row['filename'],row['class']))[:10]
    low_confidence = sorted(objects, key=lambda row:(row['confidence'],row['filename'],row['class']))[:10]
    selected = list({(row['capture_id'], row['class']):row for row in low_iou+low_confidence}.values())
    pages = render_review(selected, review)
    totals = summary(images, objects)
    assert totals['objects'] == totals['matched_objects'] == 120
    for field in ('condition','placement','scenario'):
        assert sum(g['images'] for g in groups[field].values()) == 60
        assert sum(g['objects'] for g in groups[field].values()) == 120
        weighted = sum(g['iou']['mean']*g['matched_objects'] for g in groups[field].values())/120
        assert abs(weighted-totals['iou']['mean']) < 1e-12
    thresholds = {str(t):sum(o['iou']>=t for o in objects) for t in (.5,.75,.8,.85,.9,.95)}
    csv_rows = list(csv.DictReader((experiment/'baseline/results.csv').open(encoding='utf-8')))
    report = {'format_version':1, 'scope':'Existing B03 validation predictions only; no training/inference/test access',
              'source_sha256':original_hashes, 'framework_metrics':baseline['metrics'], 'fixed_prediction_config':saved['prediction_config'],
              'metric_definitions': {'confidence':'Saved predictions after confidence>=0.25/NMS; matched-only low lists because every prediction matches here. Not calibration or pre-threshold distribution.',
                'iou':'Original 1280x720 continuous xyxy; matched same-class pairs only. Unmatched IoU is not invented; FN reported separately.',
                'below_counts':'Strictly below threshold among matched objects; not group AP. Class images include images with that class GT/prediction.',
                'percentiles':'numpy linear percentiles; object-weighted means. Group observations are correlated within one capture origin.'},
              'overall':totals, 'groups':groups, 'fixed_confidence_localization_survival':thresholds,
              'lowest_iou_10':low_iou, 'lowest_confidence_10':low_confidence, 'objects':objects,
              'review_pages':pages, 'unique_review_objects':len(selected), 'unique_review_images':len({o['capture_id'] for o in selected}),
              'epochs_existing':len(csv_rows), 'verification':{'status':'PASS','iou_recomputed_pairs':120,'group_count_and_weighted_mean_conservation':True},
              'visual_review_status':'pending assistant inspection; no label modifications or human approval requested'}
    for path, expected in original_hashes.items():
        assert digest(path)==expected, path
    write_json(output, report)
    assert len(read_json(output)['objects'])==120
    print({'overall':totals, 'groups':groups, 'low_iou':[(r['filename'],r['class'],r['iou']) for r in low_iou],
           'low_confidence':[(r['filename'],r['class'],r['confidence']) for r in low_confidence], 'pages':pages})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', required=True)
    parser.add_argument('--split', required=True)
    args = parser.parse_args()
    analyze(args.experiment, args.split)
