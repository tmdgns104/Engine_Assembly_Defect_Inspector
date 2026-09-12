"""Human guidance tests with synthetic frames only; no camera/device operations."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from training.capture_windows.guide import (
    GuidedRound, PLAN_NAME, REVIEWS_NAME, default_guide, load_guide, validate_guide)
from training.capture_windows.session import CollectionSession
from training.scripts import capture_proxy as capture
from training.scripts.verify_proxy_captures import verify_session
from test_windows_capture import PROFILE_PATH, synthetic_frame


class GuideTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='guide_synthetic_')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.profile = capture.load_profile(PROFILE_PATH)
        self.config = load_guide(PROFILE_PATH, self.profile)
        self.session = CollectionSession.create(self.root, self.profile, synthetic_frame(),
                                                'synthetic fixed conditions', source_kind='sample')
        self.guide = GuidedRound.create(self.session, self.config, 'BASELINE')

    def save(self, sequence=1):
        self.guide.prepare()
        return self.guide.save(synthetic_frame(sequence))

    def reopen(self):
        return GuidedRound.open(CollectionSession.open(self.session.folder))

    def test_all_states_require_prepare_save_and_human_review(self):
        for i, scenario in enumerate(self.profile['scenarios']):
            self.assertEqual(self.guide.step['scenario'], scenario)
            with self.assertRaises(capture.CaptureError):
                self.guide.save(synthetic_frame(i+1))
            self.save(i+1)
            self.assertEqual(self.guide.index, i)
            with self.assertRaises(capture.CaptureError):
                self.guide.prepare()
            self.guide.review(True)
        self.assertTrue(self.guide.complete)
        self.assertEqual(len({r['episode_id'] for r in self.session.records}), 4)
        expected = [[], ['earbud_left'], ['earbud_right'], ['earbud_left', 'earbud_right']]
        self.assertEqual([r['object_configuration']['objects_removed'] for r in self.session.records], expected)
        self.assertTrue(all('case' in r['object_configuration']['objects_expected'] for r in self.session.records))
        self.assertEqual(verify_session(self.root, self.session.session_id)['captures'], 4)
        with self.assertRaises(capture.CaptureError):
            self.guide.prepare()

    def test_prepare_requires_new_frame_and_preserves_original_pixels(self):
        old = synthetic_frame()
        self.guide.prepare()
        with self.assertRaises(capture.CaptureError):
            self.guide.save(old)
        self.assertEqual(self.session.records, [])
        self.guide.prepare()
        frame = synthetic_frame(2)
        path = self.guide.save(frame)
        np.testing.assert_array_equal(cv2.imread(str(path)), frame.image)
        self.assertFalse(self.guide.prepared)

    def test_rejected_photo_retained_retake_same_episode_and_requires_reason(self):
        path = self.save()
        original = path.read_bytes()
        episode = self.session.episode_id
        with self.assertRaises(ValueError):
            self.guide.review(False)
        self.guide.review(False, 'synthetic blur example')
        self.assertEqual(self.guide.index, 0)
        self.assertEqual(self.guide.rejected, 1)
        self.save(2)
        self.assertEqual(self.session.episode_id, episode)
        self.guide.review(True)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.session.counts, {'NORMAL': 2})  # saved count includes retained rejected PNG
        self.assertEqual(self.reopen().index, 1)

    def test_resume_pending_review_without_extra_image_or_prepared_state(self):
        self.save()
        resumed = self.reopen()
        self.assertEqual(resumed.pending_record['capture_id'], self.session.records[0]['capture_id'])
        self.assertFalse(resumed.prepared)
        resumed.review(True)
        again = self.reopen()
        self.assertEqual(again.index, 1)
        self.assertEqual(again.step['scenario'], 'MISSING_LEFT')
        self.assertIsNone(again.pending_record)
        self.assertEqual(len(again.session.records), 1)

    def test_save_callback_interruption_restores_pending_from_manifest(self):
        self.guide.prepare()
        # Simulates termination after the shared writer verified a PNG but before UI notification.
        self.session.save(synthetic_frame())
        resumed = self.reopen()
        self.assertEqual(resumed.index, 0)
        self.assertIsNotNone(resumed.pending_record)
        with self.assertRaises(capture.CaptureError):
            resumed.save(synthetic_frame(2))

    def test_storage_failure_does_not_advance_or_claim_review(self):
        with patch('training.scripts.capture_proxy.append_manifest', side_effect=OSError('disk full')):
            with self.assertRaises(capture.CaptureError):
                self.save()
        self.assertEqual(self.guide.index, 0)
        self.assertEqual(self.session.counts, {})
        self.assertIsNone(self.guide.pending_record)
        self.assertTrue(list(self.session.folder.glob('*/images/*.png')))
        self.assertFalse((self.session.folder/REVIEWS_NAME).exists())

    def test_review_flush_failure_freezes_until_verified_reopen(self):
        path = self.save()
        with patch('training.capture_windows.guide.os.fsync', side_effect=OSError('disk error')):
            with self.assertRaises(capture.CaptureError):
                self.guide.review(True)
        self.assertTrue(self.session.failed)
        self.assertEqual(self.guide.index, 0)
        self.assertTrue(path.exists())
        # The complete line may have reached disk; reopening reconciles actual bytes, not UI memory.
        self.assertEqual(self.reopen().index, 1)

    def test_corrupt_plan_or_partial_review_blocks_resume_preserving_files(self):
        self.save()
        plan_path = self.session.folder/PLAN_NAME
        original_plan = plan_path.read_bytes()
        plan = json.loads(original_plan)
        plan['config']['setup'] = 'tampered'
        plan_path.write_text(json.dumps(plan), encoding='utf-8')
        with self.assertRaises(ValueError):
            self.reopen()
        plan_path.write_bytes(original_plan)
        review_path = self.session.folder/REVIEWS_NAME
        review_path.write_text('{"partial":', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.reopen()
        self.assertEqual(review_path.read_text(encoding='utf-8'), '{"partial":')
        self.assertTrue(self.session.last_path.exists())
        plan_path.rename(self.session.folder/'guide-plan.backup.json')
        with self.assertRaises(ValueError):
            self.reopen()  # a missing plan with review data must not silently become manual mode

    def test_changed_review_identity_or_extra_unreviewed_images_rejected(self):
        self.save()
        self.guide.review(True)
        review_path = self.session.folder/REVIEWS_NAME
        original = review_path.read_text(encoding='utf-8')
        review = json.loads(original)
        review['capture_id'] = 'WRONG_ID'
        review_path.write_text(json.dumps(review)+'\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.reopen()
        review_path.write_text(original, encoding='utf-8')
        self.session.save(synthetic_frame(2))
        self.session.save(synthetic_frame(3))
        with self.assertRaises(ValueError):
            self.reopen()

    def test_profile_and_plan_validation_and_generic_product(self):
        for change in ('missing_state', 'duplicate_state', 'unknown_state', 'duplicate_condition', 'bool_version'):
            config = deepcopy(self.config)
            if change == 'missing_state': config['steps'].pop()
            if change == 'duplicate_state': config['steps'][1] = config['steps'][0]
            if change == 'unknown_state': config['steps'][0]['scenario'] = 'UNKNOWN'
            if change == 'duplicate_condition': config['conditions'].append(config['conditions'][0])
            if change == 'bool_version': config['guide_schema_version'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_guide(config, self.profile)
        other = {'profile_schema_version': 1, 'product_id': 'synthetic_product', 'profile_version': 1,
                 'objects': ['holder', 'part'], 'scenarios': {
                     'NORMAL': {'objects_removed': [], 'unexpected_object': False},
                     'ABSENT': {'objects_removed': ['part'], 'unexpected_object': False}}}
        config = validate_guide(default_guide(other), other)
        session = CollectionSession.create(self.root, other, synthetic_frame(), source_kind='sample')
        guide = GuidedRound.create(session, config, 'BASELINE')
        for i in range(2):
            guide.prepare()
            guide.save(synthetic_frame(i+1))
            guide.review(True)
        self.assertTrue(guide.complete)
        self.assertEqual(session.records[-1]['object_configuration']['objects_removed'], ['part'])

    def test_new_condition_new_session_and_manual_record_not_reclassified(self):
        self.save()
        with self.assertRaises(capture.CaptureError):
            GuidedRound.create(self.session, self.config, 'LIGHTING')
        new = CollectionSession.create(self.root, self.profile, synthetic_frame(), source_kind='sample')
        self.assertIsNone(GuidedRound.open(new))
        guide = GuidedRound.create(new, self.config, 'LIGHTING')
        self.assertNotEqual(guide.session.session_id, self.session.session_id)
        self.assertEqual(guide.index, 0)


if __name__ == '__main__':
    unittest.main()
