"""Acquisition leakage failures use small synthetic manifests, never real captures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from training.scripts.build_grouped_dataset import GROUP_KEYS, check_disjoint, inspect_candidates
from training.scripts.prepare_via_project import digest


class GroupedDatasetTests(unittest.TestCase):
    def setUp(self):
        self.train = [{'image_sha256': 'train-hash', 'provenance': {key: 'train-' + key for key in GROUP_KEYS}}]
        self.val = [{'image_sha256': 'val-hash', 'provenance': {key: 'val-' + key for key in GROUP_KEYS}}]

    def test_independent_groups_pass(self):
        self.assertFalse(any(check_disjoint(self.train, self.val).values()))

    def test_each_shared_acquisition_boundary_fails(self):
        for key in GROUP_KEYS:
            with self.subTest(key=key):
                val = deepcopy(self.val)
                val[0]['provenance'][key] = self.train[0]['provenance'][key]
                with self.assertRaisesRegex(ValueError, 'leakage'):
                    check_disjoint(self.train, val)

    def test_renamed_duplicate_image_fails(self):
        self.val[0]['image_sha256'] = 'train-hash'
        with self.assertRaisesRegex(ValueError, 'leakage'):
            check_disjoint(self.train, self.val)

    def test_missing_group_fails(self):
        self.val[0]['provenance']['origin_group_id'] = ''
        with self.assertRaisesRegex(ValueError, 'Missing'):
            check_disjoint(self.train, self.val)


class CandidateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'images').mkdir()
        (self.root / 'labels').mkdir()
        self.image = self.root / 'images/capture.png'
        self.label = self.root / 'labels/capture.txt'
        Image.new('RGB', (100, 100), 'red').save(self.image)
        self.label.write_text('0 0.5 0.5 0.4 0.4\n', encoding='utf-8')
        self.row = {'image': 'images/capture.png', 'label': 'labels/capture.txt', 'image_sha256': digest(self.image),
                    'label_sha256': digest(self.label), 'width': 100, 'height': 100, 'object_count': 1,
                    'review_status': 'confirmed', 'provenance': {'purpose': 'train_candidate', 'product_id': 'fixture',
                    'source_kind': 'camera', 'collection_id': 'C', 'capture_id': 'capture',
                    'image_path': str(self.image), 'image_sha256': digest(self.image)}}
        self.manifest = {'purpose': 'train_candidate', 'product_id': 'fixture', 'classes': [{'id': 0, 'name': 'part'}],
                         'inputs_sha256': {}, 'images': [self.row]}

    def inspect(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest), encoding='utf-8')
        return inspect_candidates(path, 'train_candidate')

    def test_verified_candidate_passes(self):
        self.assertEqual(self.inspect()[1], {'0': 1})

    def test_changed_bytes_fail(self):
        Image.new('RGB', (100, 100), 'blue').save(self.image)
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.inspect()

    def test_pending_image_fails(self):
        self.row['review_status'] = 'pending'
        with self.assertRaisesRegex(ValueError, 'Unapproved'):
            self.inspect()

    def test_outside_rectangle_fails_even_with_matching_label_hash(self):
        self.label.write_text('0 0.1 0.5 0.8 0.4\n', encoding='utf-8')
        self.row['label_sha256'] = digest(self.label)
        with self.assertRaisesRegex(ValueError, 'rectangle'):
            self.inspect()


if __name__ == '__main__':
    unittest.main()
