"""Synthetic collection plans and failure/recovery checks; no device access."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from training.capture_windows.guide import load_guide, default_guide
from training.capture_windows.wizard import Collection
from training.capture_windows.wizard_plan import expand_plan, load_plan, target_polygon, validate_plan, validate_targets
from training.capture_windows.wizard_quality import CaptureGate, metrics, overlay
from training.scripts import capture_proxy as capture
from test_windows_capture import PROFILE_PATH, synthetic_frame


def wizard_frame(sequence=1):
    frame = synthetic_frame(sequence)
    frame.image = np.random.default_rng(sequence).integers(45, 210, (96, 128, 3), dtype=np.uint8)
    frame.camera.update(width=128, height=96, requested_width=128, requested_height=96)
    return frame


class WizardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dataset_wizard_synthetic_')
        self.addCleanup(self.temp.cleanup)
        self.profile = capture.load_profile(PROFILE_PATH)
        self.guide = load_guide(PROFILE_PATH, self.profile)
        self.plan = load_plan(PROFILE_PATH, self.profile, self.guide)
        self.col = Collection.create(Path(self.temp.name), self.profile, self.guide, self.plan, True, 'sample')
        self.addCleanup(lambda: self.col.close())
        self.col.new_setup(wizard_frame(), [.3, .25, .35, .4], 'screen_left_is_physical_left')
        self.sequence = 0

    def capture_next(self):
        self.sequence += 1
        frame = wizard_frame(self.sequence)
        ticket = self.col.prepare(frame, now=time.monotonic()-2)
        frame = wizard_frame(self.sequence)
        return self.col.save_prepared(ticket, frame)

    def advance_non_capture(self):
        action = self.col.next_action()
        if action['kind'] == 'quality':
            self.col.acknowledge_quality(action['attempt']['attempt_id'], True)
        elif action['kind'] == 'setup_review':
            self.col.confirm_setup(True)
        elif action['kind'] == 'round':
            purpose = action['block']['purpose']
            previous = list(self.col.rounds.values())[-1] if self.col.rounds else None
            self.col.begin_round(independent=bool(previous and previous['purpose'] != purpose))
        elif action['kind'] == 'review':
            self.col.accept_batch(action['block']['block_id'], True)
        else:
            return False
        return True

    def reach(self, predicate, limit=1000):
        for _ in range(limit):
            action = self.col.next_action()
            if predicate(action):
                return action
            if action['kind'] in ('reference', 'capture'):
                self.capture_next()
            elif not self.advance_non_capture():
                self.fail(f'Unexpected state: {action}')
        self.fail('Unbounded workflow')

    def reopen(self):
        folder = self.col.folder
        self.col.close()
        self.col = Collection.open(folder)

    def test_full_240_plan_and_pilot_are_distinct_and_balanced(self):
        self.assertEqual(self.col.summary()['main_target'], 240)
        self.assertEqual(self.col.summary()['pilot_target'], 12)
        self.reach(lambda a: a['kind'] == 'finished')
        summary = self.col.summary()
        self.assertEqual((summary['main_accepted'], summary['pilot_accepted'], summary['saved']), (240, 12, 254))
        self.assertTrue(summary['complete'])
        self.assertEqual(len(self.col.rounds), 4)
        b = self.col.rounds
        self.assertEqual(b['B01']['origin_group_id'], b['B02']['origin_group_id'])
        self.assertNotEqual(b['B02']['origin_group_id'], b['B03']['origin_group_id'])
        self.assertNotEqual(b['B03']['origin_group_id'], b['B04']['origin_group_id'])
        self.reopen()
        self.assertTrue(self.col.summary()['complete'])
        output = self.col.export()
        self.assertEqual(json.loads((output/'images_for_labeling.json').read_text()), [])
        self.assertEqual(len(json.loads((output/'sample_only.json').read_text())), 254)
        self.assertFalse(list(output.glob('*.txt')))

    def test_no_lamp_plan_targets_and_skipped_pilot_cannot_complete(self):
        plan = expand_plan(self.plan, False)
        self.assertEqual(sum(len(b['steps']) for b in plan['blocks'] if b['phase'] == 'main'), 80)
        self.assertEqual(len(plan['excluded_at_setup']), 2)
        self.reach(lambda a: a['kind'] == 'capture')
        self.col.skip_condition('스탠드 사용 불가')
        self.reach(lambda a: a['kind'] == 'pilot_incomplete')
        self.assertFalse(self.col.summary()['complete'])
        self.assertEqual(self.col.summary()['main_accepted'], 0)

    def test_pending_batch_retake_and_resume_never_auto_accepts(self):
        review = self.reach(lambda a: a['kind'] == 'review')
        self.assertEqual(self.col.summary()['pilot_accepted'], 0)
        self.assertFalse(any(e['type'] == 'batch_accepted' for e in self.col.log.events))
        ids = [self.col.current[s['step_id']] for s in review['block']['steps']]
        old = self.col.attempts[ids[1]]
        original_path = self.col.folder/'sessions'/old['record']['image_path']
        original = original_path.read_bytes()
        self.col.reject(ids[1], '잘못된 배치', False)
        self.reopen()
        self.assertEqual(self.col.next_action()['role_id'], old['role_id'])
        new = self.capture_next()
        self.assertEqual(new['record']['episode_id'], old['record']['episode_id'])
        self.assertEqual(original, original_path.read_bytes())
        self.reach(lambda a: a['kind'] == 'review')
        self.col.accept_batch(review['block']['block_id'], True)
        self.assertEqual(self.col.summary()['pilot_accepted'], 4)
        self.assertEqual(self.col.summary()['retained_retake'], 1)

    def test_storage_commit_before_event_failure_recovers_without_retake(self):
        ticket = self.col.prepare(wizard_frame(), now=time.monotonic()-2)
        original = self.col.log.append
        def fail_saved(kind, data):
            if kind == 'attempt_saved':
                raise OSError('simulated event failure after PNG verification')
            return original(kind, data)
        with patch.object(self.col.log, 'append', side_effect=fail_saved):
            with self.assertRaises(OSError):
                self.col.save_prepared(ticket, wizard_frame())
        self.assertEqual(len(self.col.attempts), 0)
        self.reopen()
        self.assertEqual(len(self.col.attempts), 1)
        self.assertTrue(next(iter(self.col.attempts.values()))['recovered'])
        self.assertFalse(any(e['type'] == 'batch_accepted' for e in self.col.log.events))

    def test_writer_lock_and_malformed_event_preserve_originals(self):
        with self.assertRaises(capture.CaptureError):
            Collection.open(self.col.folder)
        folder = self.col.folder
        self.col.close()
        path = folder/'collection-events.jsonl'
        original = path.read_bytes()
        path.write_bytes(original+b'{partial')
        with self.assertRaises(ValueError):
            Collection.open(folder)
        self.assertEqual(path.read_bytes(), original+b'{partial')

    def test_gate_new_frames_motion_timeout_cancel_and_original_overlay(self):
        frame = wizard_frame()
        roi = [.3, .25, .35, .4]
        rules = self.plan['quality']
        started = frame.received_mono
        gate = CaptureGate(rules, roi, frame, now=started)
        self.assertIsNone(gate.observe(frame, now=started))
        for i in range(4):
            next_frame = replace(frame, received_mono=started+1.3+i*.05, sequence=i+2)
            result = gate.observe(next_frame, now=next_frame.received_mono)
        self.assertIsNotNone(result)
        self.assertIsNone(gate.observe(next_frame, now=next_frame.received_mono))
        gate = CaptureGate(rules, roi, frame, now=started)
        with self.assertRaises(ValueError):
            gate.observe(replace(frame, received_mono=started+9), now=started+9)
        self.assertFalse(gate.active)
        before = frame.image.copy()
        rendered = overlay(frame.image, roi, self.plan['placements'][3])
        np.testing.assert_array_equal(frame.image, before)
        self.assertEqual(rendered.size, (128, 96))
        center = target_polygon(roi, self.plan['placements'][0], (128, 96))
        left = target_polygon(roi, self.plan['placements'][1], (128, 96))
        right = target_polygon(roi, self.plan['placements'][2], (128, 96))
        self.assertAlmostEqual(left[0][0]-center[0][0], -(right[0][0]-center[0][0]))

    def test_other_product_two_states_and_changed_plan_keeps_old_snapshot(self):
        profile = {'profile_schema_version': 1, 'product_id': 'fictional_fixture', 'profile_version': 1,
                   'objects': ['tray', 'piece'], 'scenarios': {
                       'NORMAL': {'objects_removed': [], 'unexpected_object': False},
                       'ABSENT': {'objects_removed': ['piece'], 'unexpected_object': False}}}
        plan = deepcopy(self.plan)
        plan.update(product_id=profile['product_id'], state_order=['NORMAL', 'ABSENT'], references=['NORMAL', 'ABSENT'])
        guide = default_guide(profile)
        other = Collection.create(Path(self.temp.name), profile, guide, plan, False, 'sample')
        self.addCleanup(other.close)
        self.assertEqual(other.summary()['main_target'], 40)
        self.assertEqual(other.summary()['pilot_target'], 2)
        other.new_setup(wizard_frame(), [.3, .25, .35, .4], 'screen_left_is_physical_left')
        for scenario in ('NORMAL', 'ABSENT'):
            self.assertEqual(other.next_action()['scenario'], scenario)
            ticket = other.prepare(wizard_frame(), now=time.monotonic()-2)
            a = other.save_prepared(ticket, wizard_frame(10 if scenario == 'ABSENT' else 11))
            self.assertEqual(a['record']['object_configuration']['objects_removed'], profile['scenarios'][scenario]['objects_removed'])
        parent = self.col.lineage_info()
        revised = deepcopy(self.plan)
        revised['placements'] = revised['placements'][:1]
        with self.assertRaises(ValueError):
            Collection.create(Path(self.temp.name), self.profile, self.guide, revised, True, 'sample', parent)
        revised['plan_version'] = 2
        new = Collection.create(Path(self.temp.name), self.profile, self.guide, revised, True, 'sample', parent)
        self.addCleanup(new.close)
        self.assertEqual(new.summary()['main_target'], 48)
        self.assertEqual(new.summary()['main_accepted'], 0)
        self.assertEqual(self.col.summary()['main_target'], 240)
        self.assertEqual(new.info['initial_origin_group_id'], self.col.info['initial_origin_group_id'])

    def test_origin_purpose_conflict_and_reserved_export_never_train(self):
        # A tiny plan exercises the same round/group logic without another 240-image run.
        self.col.close()
        plan = deepcopy(self.plan)
        plan['placements'] = plan['placements'][:1]
        self.col = Collection.create(Path(self.temp.name), self.profile, self.guide, plan, False, 'sample')
        self.col.new_setup(wizard_frame(), [.3, .25, .35, .4], 'screen_left_is_physical_left')
        self.reach(lambda a: a['kind'] == 'round' and a['block']['round_id'] == 'B03')
        before = len(self.col.log.events)
        with self.assertRaises(ValueError):
            self.col.begin_round(False)
        self.assertEqual(len(self.col.log.events), before)
        self.reopen()
        with self.assertRaises(ValueError):
            self.col.begin_round(False)
        self.col.begin_round(True)
        self.reach(lambda a: a['kind'] == 'round' and a['block']['round_id'] == 'B04')
        with self.assertRaises(ValueError):
            self.col.begin_round(False)
        self.col.begin_round(True)
        self.reach(lambda a: a['kind'] == 'finished')
        # Test the real-record routing branch with verified temporary synthetic records.
        # This is an in-memory seam, not a claim of device use or a persisted camera dataset.
        with patch.object(self.col, '_reconcile'):
            for a in self.col.attempts.values():
                a['record']['source_kind'] = 'camera'
            output = self.col.export()
        read = lambda name: json.loads((output/(name+'.json')).read_text(encoding='utf-8'))
        train, reserved, val = read('training_candidates'), read('test_reserved'), read('validation_candidates')
        self.assertEqual((len(train), len(val), len(reserved)), (8, 4, 4))
        self.assertFalse({r['capture_id'] for r in train} & {r['capture_id'] for r in reserved})
        self.assertTrue(all(r['round_id'] == 'B04' for r in reserved))
        self.assertEqual(len(read('excluded_or_pending')), 6)

    def test_same_pixels_advisory_hold_and_new_episode_do_not_accept(self):
        a = self.capture_next()
        # Same PNG in another declared state: a review candidate, never silently discarded.
        ticket = self.col.prepare(wizard_frame(), now=time.monotonic()-2)
        duplicate = self.col.save_prepared(ticket, replace(wizard_frame(1), sequence=2))
        self.assertIn('DUPLICATE_EXACT', duplicate['metrics']['warnings'])
        self.assertIn('SIMILAR_IMAGE', duplicate['metrics']['warnings'])
        self.assertEqual(len(self.col.summary()['exact_duplicate_groups']), 1)
        self.col.reject(duplicate['attempt_id'], '위치 재배치', rearranged=True, held=True)
        self.assertEqual(self.col.summary()['held'], 1)
        self.sequence = 2
        new = self.capture_next()
        self.assertNotEqual(new['record']['episode_id'], duplicate['record']['episode_id'])
        self.assertEqual(self.col.summary()['main_accepted'], 0)
        dark = np.full((96, 128, 3), 10, np.uint8)
        result = metrics(dark, [.3, .25, .35, .4], self.plan['quality'], 'MISSING_BOTH')
        self.assertIn('DARK', result['warnings'])
        self.assertNotIn('accepted', result)

    def test_camera_change_stale_cancelled_gate_and_duplicate_ticket_block(self):
        frame = wizard_frame()
        ticket = self.col.prepare(frame, now=time.monotonic()-2)
        wrong = replace(wizard_frame(), stream_id='another-stream')
        with self.assertRaises(capture.CaptureError):
            self.col.save_prepared(ticket, wrong)
        with self.assertRaises(capture.CaptureError):
            self.col.save_prepared(ticket, replace(frame, received_mono=time.monotonic()-3))
        changed = wizard_frame()
        changed.camera['requested_width'] = 640
        with self.assertRaises(capture.CaptureError):
            self.col.prepare(changed)
        self.col.save_prepared(ticket, wizard_frame())
        with self.assertRaises(capture.CaptureError):
            self.col.save_prepared(ticket, wizard_frame())
        self.assertEqual(len(self.col.attempts), 1)
        gate = CaptureGate(self.plan['quality'], [.3, .25, .35, .4], frame)
        gate.cancel()
        self.assertIsNone(gate.observe(wizard_frame()))

    def test_partial_manifest_review_failure_and_skip_recovery_preserve_evidence(self):
        ticket = self.col.prepare(wizard_frame(), now=time.monotonic()-2)
        with patch.object(capture, 'append_manifest', side_effect=OSError('manifest failure')):
            with self.assertRaises(capture.CaptureError):
                self.col.save_prepared(ticket, wizard_frame())
        images = list(self.col.folder.rglob('*.png'))
        self.assertEqual(len(images), 1)
        self.assertEqual(self.col.summary()['saved'], 0)
        self.col.close()
        with self.assertRaises(capture.CaptureError):
            Collection.open(self.col.folder)
        self.assertTrue(images[0].exists())
        self.col = Collection.create(Path(self.temp.name), self.profile, self.guide, self.plan, True, 'sample')
        self.col.new_setup(wizard_frame(), [.3, .25, .35, .4], 'screen_left_is_physical_left')
        review = self.reach(lambda a: a['kind'] == 'review')
        with patch.object(self.col.log, 'append', side_effect=OSError('review failure')):
            with self.assertRaises(OSError):
                self.col.accept_batch(review['block']['block_id'], True)
        self.assertEqual(self.col.summary()['pilot_accepted'], 0)
        self.reopen()
        self.assertEqual(self.col.next_action()['kind'], 'review')
        self.col.skip_condition('임시 보류')
        self.col.resume_missing()
        self.assertEqual(self.col.next_action()['kind'], 'review')
        self.assertFalse(self.col.summary()['complete'])

    def test_invalid_roi_plan_and_changed_setup_clear_only_pending_group(self):
        with self.assertRaises(ValueError):
            validate_targets([.8, .2, .2, .4], self.plan['placements'], (128, 96))
        bad = deepcopy(self.plan)
        bad['state_order'][1] = 'NORMAL'
        with self.assertRaises(ValueError):
            validate_plan(bad, self.profile, self.guide)
        self.reach(lambda a: a['kind'] == 'review')
        old_setup = self.col.setup_id
        old_count = len(self.col.attempts)
        self.col.new_setup(wizard_frame(), [.3, .25, .35, .4], 'screen_right_is_physical_left')
        self.assertNotEqual(old_setup, self.col.setup_id)
        self.assertEqual(len(self.col.attempts), old_count)
        self.assertEqual(self.col.next_action()['kind'], 'reference')
        self.assertEqual(self.col.summary()['pilot_accepted'], 0)
        self.assertEqual(self.col.summary()['retained_retake'], 4)

    def test_cross_process_writer_lock_and_new_plan_after_restart_keeps_origin(self):
        code = ('import sys\nfrom training.capture_windows.wizard import Collection\n'
                'try:\n c=Collection.open(sys.argv[1]); c.close()\n'
                'except Exception as exc:\n print(type(exc).__name__); sys.exit(17)\n')
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code, str(self.col.folder)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 17, result.stdout+result.stderr)
        self.assertIn('CaptureError', result.stdout)
        origin = self.col.info['initial_origin_group_id']
        self.col.close()
        lineage = Collection.latest_lineage(Path(self.temp.name))
        self.assertEqual(lineage['continuation_origin'], origin)
        new = Collection.create(Path(self.temp.name), self.profile, self.guide, self.plan, True, 'sample', lineage)
        self.addCleanup(new.close)
        self.assertEqual(new.info['initial_origin_group_id'], origin)
        self.assertEqual(new.summary()['saved'], 0)


if __name__ == '__main__':
    unittest.main()
