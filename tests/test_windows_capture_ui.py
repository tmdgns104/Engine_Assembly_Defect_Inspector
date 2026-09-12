"""Actual Tk widgets, injected camera, temporary sample files; no hardware."""
import gc
import json
from pathlib import Path
import tempfile
from threading import Event
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from training.capture_windows.app import CaptureApp, DEFAULT_PROFILE
from training.capture_windows.session import CollectionSession
from training.capture_windows.guide import PLAN_NAME, REVIEWS_NAME
from training.scripts.verify_proxy_captures import verify_session
from test_windows_capture import synthetic_frame


class MockCamera:
    source_kind = 'sample'

    def __init__(self):
        self.process = None
        self.state = 'disconnected'
        self.latest = None
        self.error = ''
        self.releases = 0
        self.sequence = 0

    def connect(self, settings=None):
        self.process, self.state = True, 'connected'
        self.poll()

    def poll(self):
        if self.state == 'connected':
            self.sequence += 1
            self.latest = synthetic_frame(self.sequence)

    def snapshot(self):
        self.poll()
        if self.latest is None:
            raise RuntimeError('mock disconnected')
        return self.latest

    def disconnect(self):
        self.releases += 1
        self.process, self.latest, self.state = None, None, 'disconnected'


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='windows_capture_synthetic_')
        self.addCleanup(self.temp.cleanup)
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk display unavailable: {exc}')
        self.root.withdraw()
        self.callback_errors = []
        self.root.report_callback_exception = lambda kind, error, trace: self.callback_errors.append(str(error))
        self.camera = MockCamera()
        self.app = CaptureApp(self.root, output_root=Path(self.temp.name), camera=self.camera)
        self.addCleanup(self.cleanup_window)

    def cleanup_window(self):
        if not self.app.closing:
            self.app.close()
        self.pump(lambda: self.app.closed)
        self.app.executor.shutdown(wait=True)
        # Repeated Tk interpreters must be collected on their owning thread, never a later storage worker.
        self.app = self.root = None
        gc.collect()
        self.assertEqual(self.callback_errors, [])

    def pump(self, predicate, timeout=5):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            try:
                self.root.update()
            except tk.TclError:
                break
            if predicate():
                return
            time.sleep(0.01)
        self.assertTrue(predicate(), 'UI operation did not finish')

    def create_session(self):
        self.app.connect()
        self.app.new_session()
        self.pump(lambda: self.app.pending is None)
        self.assertIsNotNone(self.app.session)

    def test_initial_ui_never_opens_camera(self):
        self.root.update()
        self.assertIsNone(self.camera.process)
        self.assertEqual(self.app.scenario_keys, ['NORMAL', 'MISSING_LEFT', 'MISSING_RIGHT', 'MISSING_BOTH'])
        self.assertIn('disabled', self.app.save_button.state())

    def test_button_save_single_record_original_and_counts(self):
        self.create_session()
        self.app.save()
        self.app.save()  # event duplication while a future is pending
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.session.counts, {'NORMAL': 1})
        self.assertIn('저장 완료', self.app.message.get())
        report = verify_session(self.app.output_root, self.app.session.session_id)
        self.assertEqual(report['source_counts'], {'sample': 1})
        self.assertEqual(len(self.app.counts.get_children()), 4)

    def test_four_states_new_episodes_and_case_preserved(self):
        self.create_session()
        for index in range(4):
            self.app.scenario_combo.current(index)
            self.app.change_scenario()
            self.app.save()
            self.pump(lambda: self.app.pending is None)
        rows = self.app.session.records
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({r['episode_id'] for r in rows}), 4)
        self.assertTrue(all('case' not in r['object_configuration']['objects_removed'] for r in rows))

    def test_storage_error_shows_no_success_and_can_close(self):
        self.create_session()
        with patch('training.scripts.capture_proxy.append_manifest', side_effect=OSError('synthetic disk failure')):
            self.app.save()
            self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.session.counts, {})
        self.assertNotIn('저장 완료', self.app.message.get())
        self.assertIn('원본을 삭제하지', self.app.message.get())

    def test_background_job_keeps_tk_responsive_and_close_waits(self):
        release = Event()
        self.addCleanup(release.set)
        self.camera.connect()
        self.app.job(lambda: release.wait(3), lambda _: None)
        heartbeat = []
        self.root.after(10, lambda: heartbeat.append('alive'))
        self.app.close()
        self.pump(lambda: bool(heartbeat))
        self.assertEqual(self.camera.releases, 1)
        self.assertIsNotNone(self.app.pending)
        release.set()
        self.pump(lambda: self.app.pending is None)

    def test_other_product_populates_controls_and_saves(self):
        profile = {'profile_schema_version': 1, 'product_id': 'fictional_product', 'profile_version': 1,
                   'objects': ['fixture', 'part'], 'scenarios': {
                       'NORMAL': {'objects_removed': [], 'unexpected_object': False},
                       'PART_ABSENT': {'objects_removed': ['part'], 'unexpected_object': False}}}
        path = Path(self.temp.name)/'profile.json'
        path.write_text(json.dumps(profile), encoding='utf-8')
        self.app.load_product(path)
        self.assertEqual(self.app.scenario_keys, ['NORMAL', 'PART_ABSENT'])
        self.create_session()
        self.app.scenario_combo.current(1)
        self.app.change_scenario()
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.session.records[0]['scenario'], 'PART_ABSENT')

    def test_reopen_restores_ui_counts(self):
        self.create_session()
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        opened = CollectionSession.open(self.app.session.folder)
        with patch('training.capture_windows.app.messagebox.askyesno', return_value=True):
            self.app.finish_open(opened)
        self.assertEqual(self.app.session.counts, {'NORMAL': 1})
        self.assertIsNotNone(self.app.session_stream)
        self.assertEqual(self.app.session.episode_id[-5:], 'E0002')

    def create_guided_session(self):
        self.app.connect()
        self.app.conditions.set('synthetic fixed camera / light / pose')
        self.app.start_guide()
        self.pump(lambda: self.app.pending is None)
        self.assertIsNotNone(self.app.guide)

    def test_guide_blocks_without_conditions_or_readiness(self):
        self.app.connect()
        self.app.start_guide()
        self.assertIsNone(self.app.session)
        self.assertIn('조건', self.app.message.get())
        self.app.conditions.set('synthetic conditions')
        self.app.start_guide()
        self.pump(lambda: self.app.pending is None)
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.session.records, [])
        self.assertIn('준비', self.app.message.get())
        self.assertIn('disabled', self.app.save_button.state())

    def test_guided_four_states_review_and_next_condition(self):
        self.create_guided_session()
        sid = self.app.session.session_id
        for i in range(4):
            self.app.prepare_guide()
            self.app.save()
            self.app.save()
            self.pump(lambda: self.app.pending is None)
            self.assertEqual(len(self.app.session.records), i+1)
            self.assertEqual(self.app.guide.index, i)
            self.assertIn('검토 대기', self.app.guide_title.get())
            self.app.review_guide(True)
            self.app.review_guide(True)
            self.pump(lambda: self.app.pending is None)
            self.assertEqual(self.app.guide.index, i+1)
            self.assertFalse(self.app.guide.prepared)
        self.assertTrue(self.app.guide.complete)
        self.assertIn('학습', self.app.guide_text.get())
        self.app.guide_condition.current(2)
        self.app.conditions.set('synthetic changed lighting')
        self.app.start_guide()
        self.pump(lambda: self.app.pending is None)
        self.assertNotEqual(self.app.session.session_id, sid)
        self.assertEqual(self.app.guide.condition['id'], 'LIGHTING')
        self.assertEqual(self.app.session.records, [])

    def test_guided_retake_preserves_original_and_episode(self):
        self.create_guided_session()
        self.app.prepare_guide()
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        original = self.app.session.last_path
        original_bytes = original.read_bytes()
        episode = self.app.session.episode_id
        self.app.review_guide(False)
        self.pump(lambda: self.app.pending is None)
        self.assertIn('이유', self.app.message.get())
        self.assertIsNotNone(self.app.guide.pending_record)
        self.app.guide_note.set('synthetic reflection')
        self.app.review_guide(False)
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(original.read_bytes(), original_bytes)
        self.assertEqual(self.app.session.episode_id, episode)
        self.assertEqual(self.app.guide.index, 0)
        self.app.prepare_guide()
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(len(self.app.session.records), 2)

    def test_guided_reopen_pending_restores_saved_plan_not_new_config(self):
        self.create_guided_session()
        self.app.prepare_guide()
        self.app.save()
        self.pump(lambda: self.app.pending is None)
        self.app.guide_config['setup'] = 'changed local UI config'
        opened = CollectionSession.open(self.app.session.folder)
        with patch('training.capture_windows.app.messagebox.askyesno', return_value=True):
            self.app.finish_open(opened)
        self.assertNotEqual(self.app.guide.config['setup'], 'changed local UI config')
        self.assertIsNotNone(self.app.guide.pending_record)
        self.assertFalse(self.app.guide.prepared)
        self.assertEqual(len(self.app.session.records), 1)
        self.app.review_guide(True)
        self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.selected_scenario(), 'MISSING_LEFT')

    def test_guided_disconnect_rearrange_and_conditions_change_require_readiness(self):
        self.create_guided_session()
        self.app.prepare_guide()
        self.app.new_episode()
        self.assertFalse(self.app.guide.prepared)
        self.app.prepare_guide()
        self.app.conditions.set('changed condition')
        self.app.save()
        self.assertEqual(self.app.session.records, [])
        self.assertIn('바뀌', self.app.message.get())
        self.app.disconnect()
        self.assertFalse(self.app.guide.prepared)
        self.app.save()
        self.assertEqual(self.app.session.records, [])

    def test_corrupt_guide_resume_blocks_manual_save(self):
        self.create_guided_session()
        path = self.app.session.folder/PLAN_NAME
        path.write_text('{broken', encoding='utf-8')
        opened = CollectionSession.open(self.app.session.folder)
        self.app.finish_open(opened)
        self.assertTrue(self.app.session.failed)
        self.assertIn('복원 실패', self.app.message.get())
        self.app.save()
        self.assertEqual(self.app.session.records, [])
        self.assertEqual(path.read_text(encoding='utf-8'), '{broken')

    def test_guided_storage_failure_no_progress_or_success(self):
        self.create_guided_session()
        self.app.prepare_guide()
        with patch('training.scripts.capture_proxy.append_manifest', side_effect=OSError('synthetic disk failure')):
            self.app.save()
            self.pump(lambda: self.app.pending is None)
        self.assertEqual(self.app.guide.index, 0)
        self.assertEqual(self.app.session.counts, {})
        self.assertNotIn('저장 완료', self.app.message.get())
        self.assertFalse(self.app.guide.prepared)
        self.assertFalse((self.app.session.folder/REVIEWS_NAME).exists())

    def test_generic_guide_ui_uses_product_without_earbud_rules(self):
        profile = {'profile_schema_version': 1, 'product_id': 'fictional_product', 'profile_version': 1,
                   'objects': ['fixture', 'part'], 'scenarios': {
                       'NORMAL': {'objects_removed': [], 'unexpected_object': False},
                       'PART_ABSENT': {'objects_removed': ['part'], 'unexpected_object': False}}}
        path = Path(self.temp.name)/'profile.json'
        path.write_text(json.dumps(profile), encoding='utf-8')
        self.app.load_product(path)
        self.create_guided_session()
        for _ in range(2):
            self.assertNotIn('이어폰', self.app.guide_text.get())
            self.app.prepare_guide()
            self.app.save()
            self.pump(lambda: self.app.pending is None)
            self.app.review_guide(True)
            self.pump(lambda: self.app.pending is None)
        self.assertTrue(self.app.guide.complete)


if __name__ == '__main__':
    unittest.main()
