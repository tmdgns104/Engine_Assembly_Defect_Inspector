"""Focused preparation checks using isolated synthetic files, never captures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from training.scripts.prepare_via_project import prepare, read_json, write_json


class ViaPreparationTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('.cache/tests').resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='via_prepare_test_', dir=scratch)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(scratch))
        self.addCleanup(self.temp.cleanup)
        self.collection = self.root / 'collection'
        self.export = self.collection / 'exports' / 'EXPORT_SYNTHETIC_TEST'
        self.export.mkdir(parents=True)
        self.source = self.collection / 'sessions' / 'SYNTHETIC_UNIT_TEST.png'
        self.source.parent.mkdir()
        Image.new('RGB', (32, 24), 'red').save(self.source)
        self.schema = self.root / 'schema.json'
        write_json(self.schema, {'product_id': 'generic_fixture', 'classes': [
            {'id': 0, 'name': 'generic_part', 'display': '시험 부품'}]})
        self.html = self.root / 'via_test_marker.html'
        self.html.write_text('VGG Image Annotator (synthetic copy fixture)', encoding='utf-8')
        self.output = self.root / 'unlabelled'
        self.row = {
            'attempt_id': 'SYNTHETIC_ATTEMPT_1', 'capture_id': 'SYNTHETIC_CAPTURE_1',
            'source_kind': 'camera', 'purpose': 'train_candidate',
            'product_id': 'generic_fixture', 'image_path': str(self.source),
            'image_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
            'scenario': 'NORMAL', 'round_id': 'B01', 'condition_id': 'BASE',
            'placement_id': 'CENTER', 'origin_group_id': 'SYNTHETIC_ORIGIN',
        }
        self.save_handoff()

    def save_handoff(self):
        for name in ('training_candidates.json', 'images_for_labeling.json'):
            (self.export / name).write_text(json.dumps([self.row]), encoding='utf-8')

    def run_prepare(self, output=None, purpose='train_candidate'):
        return prepare(self.export, output or self.output, self.schema, self.html, purpose)

    def test_prepares_only_pending_copies_and_preserves_inputs(self):
        # A malformed sealed list proves normal preparation does not parse it.
        (self.export / 'test_reserved.json').write_text('DO NOT READ', encoding='utf-8')
        before = {str(p): p.read_bytes() for p in self.collection.rglob('*') if p.is_file()}
        report = self.run_prepare()
        project = read_json(self.output / 'project_initial.json')
        entry = next(iter(project['_via_img_metadata'].values()))
        self.assertEqual((report['image_count'], report['regions'], report['human_reviewed']), (1, 0, 0))
        self.assertEqual(entry['regions'], [])
        self.assertEqual(entry['file_attributes']['review_status'], 'pending')
        self.assertEqual((self.output / 'images/0001.png').read_bytes(), self.source.read_bytes())
        provenance = read_json(self.output / 'provenance.json')[0]
        self.assertEqual((provenance['width'], provenance['height']), (32, 24))
        self.assertEqual(provenance['origin_group_id'], 'SYNTHETIC_ORIGIN')
        self.assertFalse(list(self.output.rglob('*.txt')))
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.collection.rglob('*') if p.is_file()})

    def test_refuses_existing_output_without_overwriting(self):
        self.output.mkdir()
        sentinel = self.output / 'existing_review.json'
        sentinel.write_text('preserve', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'new output'):
            self.run_prepare()
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'preserve')

    def test_refuses_output_inside_original_collection(self):
        with self.assertRaisesRegex(ValueError, 'outside the original'):
            self.run_prepare(self.collection / 'labels')
        self.assertFalse((self.collection / 'labels').exists())

    def test_refuses_source_hash_mismatch_before_output(self):
        self.source.write_bytes(self.source.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_refuses_handoff_disagreement(self):
        self.row['scenario'] = 'DIFFERENT'
        (self.export / 'training_candidates.json').write_text(json.dumps([self.row]), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            self.run_prepare()

    def test_refuses_sample_and_product_mismatch(self):
        for field, value in [('source_kind', 'sample'), ('product_id', 'wrong_product')]:
            with self.subTest(field=field):
                original = self.row[field]
                self.row[field] = value
                self.save_handoff()
                with self.assertRaises(ValueError):
                    self.run_prepare()
                self.assertFalse(self.output.exists())
                self.row[field] = original

    def test_refuses_reserved_test_purpose(self):
        with self.assertRaisesRegex(ValueError, 'Sealed test'):
            self.run_prepare(purpose='test_reserved')
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
