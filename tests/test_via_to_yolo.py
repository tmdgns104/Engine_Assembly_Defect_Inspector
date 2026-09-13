"""Generic synthetic fixtures only; never read or modify real capture data."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from PIL import Image

from training.scripts.prepare_via_project import digest, read_json
from training.scripts.via_to_yolo import convert, capture_stem, verify_label_file


class ViaToYoloTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('.cache/tests').resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='via_yolo_test_', dir=scratch)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(scratch))
        self.addCleanup(self.temp.cleanup)
        self.original = self.root / 'original'
        source = self.original / 'sessions' / 'SYNTHETIC.png'
        source.parent.mkdir(parents=True)
        Image.new('RGB', (100, 80), 'red').save(source)
        self.workspace = self.root / 'via'
        (self.workspace / 'images').mkdir(parents=True)
        shutil.copyfile(source, self.workspace / 'images' / '0001.png')
        self.project_path = self.workspace / 'reviewed.json'
        self.schema_path = self.workspace / 'schema.json'
        self.provenance_path = self.workspace / 'provenance.json'
        self.review_path = self.workspace / 'review.json'
        self.output = self.root / 'candidates'
        self.region = {'shape_attributes': {'name': 'rect', 'x': 10, 'y': 20, 'width': 30, 'height': 40},
                       'region_attributes': {'class_id': '0'}}
        self.project = {'_via_image_id_list': ['id1'], '_via_attributes': {
            'region': {'class_id': {'options': {'0': '공통 부품'}}}},
            '_via_img_metadata': {'id1': {'filename': '0001.png', 'size': source.stat().st_size,
                'file_attributes': {'review_status': 'confirmed', 'note': 'historical uncertainty accepted by human'},
                'regions': [self.region]}}}
        self.schema = {'product_id': 'generic_fixture', 'classes': [{'id': 0, 'name': 'generic_component'}]}
        self.rows = [{'via_image_id': 'id1', 'working_image': 'images/0001.png',
            'collection_id': 'COLLECTION', 'capture_id': 'CAPTURE1', 'source_kind': 'camera',
            'purpose': 'train_candidate', 'product_id': 'generic_fixture', 'round_id': 'ROUND1',
            'origin_group_id': 'ORIGINAL_GROUP', 'image_path': str(source), 'image_sha256': digest(source),
            'width': 100, 'height': 80, 'scenario': 'metadata_only', 'objects_removed': []}]
        self.approved, self.deferred = ['id1'], []

    def save(self):
        for path, value in ((self.project_path, self.project), (self.schema_path, self.schema),
                            (self.provenance_path, self.rows)):
            path.write_text(json.dumps(value, allow_nan=True), encoding='utf-8')
        review = {'reviewed_project': {'sha256': digest(self.project_path)},
                  'schema': {'sha256': digest(self.schema_path)}, 'provenance': {'sha256': digest(self.provenance_path)},
                  'approved_image_ids': self.approved, 'deferred_image_ids': self.deferred,
                  'user_statement': 'SYNTHETIC TEST approval only', 'recorded_at': '2026-09-13T00:00:00+00:00'}
        self.review_path.write_text(json.dumps(review), encoding='utf-8')

    def run_conversion(self, save=True, **kwargs):
        if save:
            self.save()
        return convert(self.project_path, self.schema_path, self.provenance_path, self.review_path,
                       self.original, kwargs.pop('output', self.output), **kwargs)

    def test_exact_normalization_pixel_preservation_and_provenance(self):
        self.save()
        before = {path: digest(path) for path in self.workspace.rglob('*') if path.is_file()}
        result = self.run_conversion(save=False)
        self.assertEqual((result['status'], result['converted_images'], result['objects']), ('PASS', 1, 1))
        manifest = read_json(self.output / 'candidate_manifest.json')
        item = manifest['images'][0]
        self.assertEqual(item['provenance'], self.rows[0])
        self.assertEqual(manifest['classes'][0]['name'], 'generic_component')
        self.assertEqual((self.output / item['label']).read_text().strip(), '0 0.2500000000 0.5000000000 0.3000000000 0.5000000000')
        self.assertEqual(digest(self.output / item['image']), self.rows[0]['image_sha256'])
        self.assertEqual(before, {path: digest(path) for path in before})
        self.assertFalse(result['dataset_split_ready'])
        self.assertFalse((self.output / 'dataset.yaml').exists())

    def test_bad_geometry_withholds_whole_image(self):
        for value in (-1, 80, float('nan'), float('inf')):
            with self.subTest(x=value):
                self.region['shape_attributes']['x'] = value
                output = self.root / ('geometry_' + str(value))
                result = self.run_conversion(output=output)
                self.assertEqual((result['converted_images'], result['withheld_images'], result['objects']), (0, 1, 0))
                self.assertTrue(read_json(output / 'withheld_images.json')[0]['reasons'])

    def test_invalid_class_never_drops_only_bad_object(self):
        other = deepcopy(self.region)
        other['region_attributes']['class_id'] = '9'
        self.project['_via_img_metadata']['id1']['regions'].append(other)
        result = self.run_conversion()
        self.assertEqual((result['converted_images'], result['withheld_images']), (0, 1))
        self.assertEqual(list((self.output / 'labels').iterdir()), [])

    def test_nonpositive_box_is_withheld(self):
        self.region['shape_attributes']['height'] = 0
        self.assertEqual(self.run_conversion()['withheld_images'], 1)

    def test_pending_file_is_withheld_even_when_receipt_lists_it(self):
        self.project['_via_img_metadata']['id1']['file_attributes']['review_status'] = 'pending'
        self.assertEqual(self.run_conversion()['withheld_images'], 1)

    def test_pending_region_withholds_confirmed_image(self):
        self.region['region_attributes']['review_status'] = 'pending'
        self.assertEqual(self.run_conversion()['withheld_images'], 1)

    def test_unapproved_or_deferred_image_is_withheld(self):
        self.approved, self.deferred = [], ['id1']
        self.assertEqual(self.run_conversion()['withheld_images'], 1)

    def test_no_labels_is_not_a_background_example(self):
        self.project['_via_img_metadata']['id1']['regions'] = []
        self.assertEqual(self.run_conversion()['withheld_images'], 1)

    def test_same_local_number_has_distinct_capture_names(self):
        another = dict(self.rows[0], capture_id='CAPTURE2', working_image='images/0001.png')
        self.assertNotEqual(capture_stem(self.rows[0]), capture_stem(another))

    def test_windows_filename_collision_rejected_before_output(self):
        self.rows.append(dict(self.rows[0], via_image_id='id2', capture_id='capture1'))
        self.project['_via_img_metadata']['id2'] = deepcopy(self.project['_via_img_metadata']['id1'])
        self.project['_via_image_id_list'].append('id2')
        self.approved.append('id2')
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_existing_output_and_original_folder_are_protected(self):
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('preserve', encoding='utf-8')
        for output in (self.output, self.original / 'new', self.workspace / 'new'):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, 'new output'):
                self.run_conversion(output=output)
        self.assertEqual(sentinel.read_text(), 'preserve')

    def test_modified_project_cannot_reuse_old_approval(self):
        self.save()
        self.project_path.write_text(self.project_path.read_text() + ' ', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.run_conversion(save=False)

    def test_wrong_original_hash_is_rejected(self):
        self.rows[0]['image_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.run_conversion()

    def test_test_reserved_row_rejected_before_image_access(self):
        self.rows[0]['purpose'] = 'test_reserved'
        self.rows[0]['image_path'] = str(self.root / 'do_not_open.png')
        with self.assertRaisesRegex(ValueError, 'purpose'):
            self.run_conversion()
        self.assertFalse(self.output.exists())

    def test_validation_candidate_keeps_actual_origin(self):
        self.rows[0].update(purpose='validation_candidate', round_id='ROUND3', origin_group_id='NEW_PHYSICAL_GROUP')
        result = self.run_conversion(purpose='validation_candidate')
        self.assertEqual(result['origin_groups'], ['NEW_PHYSICAL_GROUP'])

    def test_actual_written_label_tampering_fails_roundtrip(self):
        self.run_conversion()
        label = next((self.output / 'labels').iterdir())
        label.write_text('0 0.3500000000 0.5000000000 0.3000000000 0.5000000000\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'roundtrip'):
            verify_label_file(label, [self.region], {'0': 'generic_component'}, 100, 80)


if __name__ == '__main__':
    unittest.main()
