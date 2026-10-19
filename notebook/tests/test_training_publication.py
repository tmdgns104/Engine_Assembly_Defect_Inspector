"""공개한 학습 도구의 입력 경계. 실제 사진·라벨·GPU 학습은 사용하지 않는다."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'notebook'))
from training.scripts.build_grouped_dataset import check_disjoint

spec = importlib.util.spec_from_file_location('published_parts',
    ROOT/'notebook/training/engine_detection/parts/train_engine_parts.py')
parts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parts)


def synthetic_annotations():
    records = []
    for number in range(1, 217):
        split = 'train' if number <= 144 else 'val'
        row = dict(review_id=f'D{number:03}', capture_id=f'fixture-{number}',
                   image_member=f'fixture/{number}.png', image_sha256=f'{number:064x}',
                   split=split, round_id='E01' if number <= 72 else 'E02' if number <= 144 else 'E03',
                   scenario_capture_truth='NORMAL', origin_group_id='fixture-'+split,
                   width=1280, height=720, test_reserved=False, rejected=False,
                   capture_human_accepted=True, expected_counts=dict(gray_pipe=2, exhaust_top=1, symbol_module=1),
                   boxes=[dict(class_id=cid, class_name=parts.CLASS_NAMES[cid],
                               bbox_xyxy=[10.25+index*150, 20.5, 90.75+index*150, 160.25])
                          for index, cid in enumerate((0, 0, 1, 2))])
        records.append(row)
    return dict(class_names=parts.CLASS_NAMES, items=deepcopy(records)), dict(class_names=parts.CLASS_NAMES, rows=records)


class TrainingPublicationTests(unittest.TestCase):
    def test_original_detector_split_contract(self):
        data, index = synthetic_annotations()
        result = parts.validate_annotations(data, index)
        self.assertEqual(result['images'], {'train':144, 'val':72})
        self.assertEqual(result['test_images_used'], 0)

    def test_reserved_source_and_changed_source_rejected(self):
        for mutate in ('reserved', 'group', 'path'):
            data, index = synthetic_annotations()
            if mutate == 'reserved':
                index['rows'][0]['test_reserved'] = True
            elif mutate == 'group':
                data['items'][0]['origin_group_id'] = 'other'
            else:
                index['rows'][0]['image_member'] = data['items'][0]['image_member'] = '../private.png'
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                parts.validate_annotations(data, index)

    def test_box_coordinate_roundtrip_and_invalid_bounds(self):
        data, index = synthetic_annotations()
        row = data['items'][0]
        for original, line in zip(row['boxes'], parts.yolo_text(row).splitlines()):
            _, cx, cy, w, h = map(float, line.split())
            actual = [(cx-w/2)*1280, (cy-h/2)*720, (cx+w/2)*1280, (cy+h/2)*720]
            self.assertLess(max(abs(a-b) for a,b in zip(actual, original['bbox_xyxy'])), 1e-5)
        row['boxes'][0]['bbox_xyxy'][0] = -1
        with self.assertRaises(ValueError):
            parts.validate_annotations(data, index)

    def test_approval_cannot_be_inferred_from_execution(self):
        with self.assertRaises(ValueError):
            parts.make_approval('', 'fixture-hash', 216)
        receipt = parts.make_approval('APPROVE 216', 'fixture-hash', 216)
        self.assertEqual(receipt['annotations_sha256'], 'fixture-hash')

    def test_group_or_image_leakage_rejected(self):
        def row(prefix):
            return dict(image_sha256=prefix, provenance={key:prefix+key for key in
                        ('origin_group_id', 'session_id', 'episode_id', 'capture_id')})
        train, val = row('train'), row('val')
        check_disjoint([train], [val])
        val['image_sha256'] = train['image_sha256']
        with self.assertRaises(ValueError):
            check_disjoint([train], [val])
        val = row('val')
        val['provenance']['origin_group_id'] = train['provenance']['origin_group_id']
        with self.assertRaises(ValueError):
            check_disjoint([train], [val])

    def test_new_training_sources_compile_without_executing(self):
        files = []
        for folder in ('engine_detection', 'engine_baseline', 'engine_recovery'):
            files.extend((ROOT/'notebook/training'/folder).rglob('*.py'))
        self.assertGreaterEqual(len(files), 25)
        for path in files:
            with self.subTest(file=path.name):
                compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')


if __name__ == '__main__':
    unittest.main()
