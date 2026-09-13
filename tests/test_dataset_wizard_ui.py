"""Tk interaction with a single injected synthetic camera, never physical devices."""
from dataclasses import replace
import gc
from pathlib import Path
import tempfile
from threading import Event
import time
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from training.capture_windows.wizard import Collection
from training.capture_windows.wizard_app import WizardApp
from training.capture_windows.wizard_views import progress_window
from test_dataset_wizard import wizard_frame


class WizardCamera:
    source_kind = 'sample'

    def __init__(self):
        self.process, self.latest, self.settings = None, None, None
        self.state, self.error = 'disconnected', ''
        self.sequence, self.seed, self.releases = 0, 1, 0

    def connect(self, settings=None):
        self.settings = settings
        self.state, self.process = 'connected', True
        self.poll()

    def poll(self):
        if self.state == 'connected':
            self.sequence += 1
            self.latest = replace(wizard_frame(self.seed), sequence=self.sequence)

    def snapshot(self):
        self.poll()
        if self.state != 'connected' or self.latest is None or not self.latest.fresh():
            raise ValueError('mock disconnected/stale')
        return self.latest

    def disconnect(self):
        self.releases += 1
        self.state, self.process, self.latest = 'disconnected', None, None


class WizardWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='wizard_ui_sample_')
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.errors = []
        self.root.report_callback_exception = lambda kind, error, trace: self.errors.append(str(error))
        self.camera = WizardCamera()
        self.app = WizardApp(self.root, output_root=self.temp.name, camera=self.camera)
        self.addCleanup(self.cleanup_window)

    def pump(self, predicate, seconds=5):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            try:
                self.root.update()
            except tk.TclError:
                break
            if predicate():
                return
            time.sleep(.01)
        self.assertTrue(predicate(), self.app.message.get())

    def cleanup_window(self):
        self.app.close()
        self.pump(lambda: self.app.closed)
        self.app.executor.shutdown(wait=True)
        self.assertEqual(self.errors, [])
        self.app = self.root = None
        gc.collect()

    def configure(self, lamp=False):
        self.camera.connect()
        col = Collection.create(self.app.output_root, self.app.profile, self.app.guide, self.app.plan, lamp, 'sample')
        col.new_setup(self.camera.snapshot(), [.3, .25, .35, .4], 'screen_left_is_physical_left')
        self.app.collection = col
        self.app.roi = [.3, .25, .35, .4]
        self.app.paused = False
        self.app.resume_verified = True
        self.app.refresh()
        return col

    def photograph(self):
        if self.app.lighting_window:
            self.app.lighting_window.confirmed.set(True)  # Synthetic physical-preparation input.
            self.app.lighting_window.confirm()
        self.camera.seed += 1
        count = len(self.app.collection.attempts)
        self.app.ready()
        self.app.ready()  # duplicate readiness cannot arm another image
        self.pump(lambda: not self.app.future and not self.app.gate and len(self.app.collection.attempts) == count+1)

    def advance_synthetic(self, predicate):
        """Build bounded sample-only fixtures without touching physical devices."""
        col = self.app.collection
        for sequence in range(1, 50):
            action = col.next_action()
            if predicate(action):
                return action
            kind = action['kind']
            if kind in ('reference', 'capture'):
                frame = wizard_frame(sequence)
                col.save_prepared(col.prepare(frame, now=time.monotonic()-2), frame)
            elif kind == 'setup_review':
                col.confirm_setup(True)
            elif kind == 'review':
                col.accept_batch(action['block']['block_id'], True)
            elif kind == 'round':
                col.begin_round(False)
            elif kind == 'quality':
                col.acknowledge_quality(action['attempt']['attempt_id'], True)
            else:
                self.fail(f'Unexpected fixture action: {kind}')
        self.fail('Synthetic fixture exceeded bound')

    def test_confirmed_block_reopens_without_acceptance_and_retake_preserves_history(self):
        col = self.configure()
        self.advance_synthetic(lambda a: a['kind'] == 'capture' and a['block']['phase'] == 'main'
                               and a['block']['placement_id'] == 'LEFT')
        block_id = 'main_B01_BASE_CENTER'
        ids = list(col.accepted[block_id].values())
        paths = [col.folder/'sessions'/col.attempts[aid]['record']['image_path'] for aid in ids]
        originals = [p.read_bytes() for p in paths]
        self.app.paused = True
        count = len(col.log.events)
        progress = progress_window(self.app)
        tree = next(w for w in progress.winfo_children() if isinstance(w, ttk.Treeview))
        row = next(i for i in tree.get_children() if tree.item(i, 'values')[:4] == ('main', 'B01', 'BASE', 'CENTER'))
        tree.selection_set(row)
        controls = next(w for w in progress.winfo_children() if isinstance(w, ttk.Frame))
        next(w for w in controls.winfo_children() if isinstance(w, ttk.Button)).invoke()
        review = self.app.review_window
        self.assertEqual(review.ids, ids)
        self.assertEqual(len(col.log.events), count)
        self.assertIn('disabled', review.accept_button.state())
        review.confirmed.set(True)
        review.accept()
        self.assertEqual(len(col.log.events), count)
        review.selected[0].set(True)
        review.reason.set('조명 조건 불일치')
        review.retake()
        self.pump(lambda: not self.app.future)
        self.assertNotIn(block_id, col.accepted)
        self.assertEqual(col.next_action()['scenario'], 'NORMAL')
        self.assertEqual(col.summary()['main_accepted'], 0)
        self.assertEqual(col.summary()['pending'], 3)
        self.assertEqual([p.read_bytes() for p in paths], originals)
        self.assertEqual(col.log.events[-1]['type'], 'attempt_rejected')
        folder = col.folder
        col.close()
        self.app.collection = Collection.open(folder)
        self.assertNotIn(block_id, self.app.collection.accepted)
        self.assertEqual(self.app.collection.attempts[ids[0]]['rejection_reason'], '조명 조건 불일치')

    def test_lighting_confirmation_never_captures_and_repeats_on_change_or_resume(self):
        col = self.configure(lamp=True)
        self.advance_synthetic(lambda a: a['kind'] == 'capture')
        self.app.refresh()
        lighting = self.app.lighting_window
        self.assertIsNotNone(lighting)
        count = len(col.attempts)
        self.app.ready()
        lighting.confirm()
        self.assertIs(self.app.lighting_window, lighting)
        self.assertIsNone(self.app.gate)
        lighting.confirmed.set(True)
        lighting.confirm()
        self.assertIsNone(self.app.lighting_window)
        self.assertEqual(len(col.attempts), count)
        self.assertIsNone(self.app.gate)
        action = col.next_action()
        self.assertFalse(self.app.needs_lighting(action))
        self.advance_synthetic(lambda a: a['kind'] == 'capture' and a['block']['condition_id'] == 'DIM')
        self.app.refresh()
        self.assertIsNotNone(self.app.lighting_window)
        self.assertIn('밝기를 조금 낮추거나', '\n'.join(
            w.cget('text') for w in self.app.lighting_window.window.winfo_children() if isinstance(w, ttk.Label)))
        count = len(col.attempts)
        self.app.ready()
        self.assertIsNone(self.app.gate)
        self.app.lighting_window.confirmed.set(True)
        self.app.lighting_window.confirm()
        self.assertEqual(len(col.attempts), count)
        self.app.pause()
        self.app.paused = False
        self.app.refresh()
        self.assertIsNotNone(self.app.lighting_window)
        self.app.lighting_window.cancel()
        self.assertTrue(self.app.paused)
        self.assertEqual(len(col.attempts), count)
        self.assertIsNone(self.app.gate)

    def test_initial_start_has_no_camera_access_and_advanced_is_closed(self):
        self.root.update()
        self.assertIsNone(self.camera.process)
        self.assertFalse(hasattr(self.app, 'settings_window'))
        self.assertIn('disabled', self.app.ready_button.state())
        self.assertIn('시작', self.app.title.get())

    def test_ready_then_auto_capture_review_retake_and_next_condition(self):
        col = self.configure()
        self.photograph()
        self.photograph()
        self.assertIsNotNone(self.app.review_window)
        review = self.app.review_window
        review.accept()
        self.assertFalse(col.setups[col.setup_id]['confirmed'])
        review.confirmed.set(True)
        review.accept()
        self.pump(lambda: not self.app.future)
        for _ in range(4):
            self.photograph()
        self.assertEqual(col.summary()['pilot_accepted'], 0)
        review = self.app.review_window
        self.assertEqual(len(review.ids), 4)
        self.root.deiconify()
        review.window.deiconify()
        self.pump(lambda: review.canvas.winfo_height() > 100)
        self.root.update()
        bottom = review.canvas.winfo_rooty()+review.canvas.winfo_height()
        self.assertLessEqual(max(b.winfo_rooty()+b.winfo_height() for b in review.select_buttons), bottom)
        old = col.attempts[review.ids[2]]
        path = col.folder/'sessions'/old['record']['image_path']
        original = path.read_bytes()
        review.selected[2].set(True)
        review.reason.set('잘못된 배치')
        review.retake()
        self.pump(lambda: not self.app.future)
        self.photograph()
        self.assertEqual(path.read_bytes(), original)
        self.app.review_window.confirmed.set(True)
        self.app.review_window.accept()
        self.pump(lambda: not self.app.future)
        self.assertEqual(col.summary()['pilot_accepted'], 4)
        self.assertEqual(col.next_action()['kind'], 'round')
        self.assertEqual(col.summary()['main_accepted'], 0)

    def test_space_hold_pause_and_disconnect_never_save(self):
        col = self.configure()
        event = SimpleNamespace(widget=self.app.preview)
        self.app.key_ready(event)
        first = self.app.ticket
        self.app.key_ready(event)
        self.assertIs(self.app.ticket, first)
        self.app.pause()
        self.app.key_ready(event)
        self.assertIsNone(self.app.gate)
        self.assertEqual(len(col.attempts), 0)
        self.app.key_release(event)
        self.app.start()
        self.app.ready()
        self.camera.disconnect()
        self.pump(lambda: self.app.gate is None)
        self.assertFalse(col.attempts)
        self.assertIn('촬영하지 않았', self.app.message.get())

    def test_storage_failure_freezes_without_success_and_close_is_responsive(self):
        col = self.configure()
        with patch('training.scripts.capture_proxy.append_manifest', side_effect=OSError('synthetic disk failure')):
            self.app.ready()
            self.pump(lambda: col.failed and self.app.future is None)
        self.assertEqual(col.summary()['saved'], 0)
        self.assertTrue(self.app.paused)
        self.assertIn('진행 중단', self.app.message.get())
        release = Event()
        self.addCleanup(release.set)
        self.app.submit(lambda: release.wait(4))
        heartbeat = []
        self.root.after(10, lambda: heartbeat.append(True))
        self.app.close()
        self.pump(lambda: bool(heartbeat))
        self.assertIsNotNone(self.app.future)
        release.set()
        self.pump(lambda: self.app.closed)

    def test_reopen_starts_paused_and_original_png_has_no_overlay(self):
        col = self.configure()
        self.photograph()
        a = next(iter(col.attempts.values()))
        png = col.folder/'sessions'/a['record']['image_path']
        image = cv2.imread(str(png))
        np.testing.assert_array_equal(image, wizard_frame(self.camera.seed).image)
        folder = col.folder
        col.close()
        self.app.collection = None
        with patch.object(self.app, 'settings'):
            self.app.open_collection(folder)
            self.pump(lambda: not self.app.future)
        self.assertTrue(self.app.paused)
        self.assertFalse(self.app.resume_verified)
        self.assertIsNone(self.app.gate)
        self.assertEqual(self.app.collection.summary()['saved'], 1)
        with patch('training.capture_windows.wizard_app.messagebox.askyesno', return_value=True):
            self.app.start()
        self.assertFalse(self.app.paused)
        self.assertIsNone(self.app.gate)

    def test_ttk_space_release_does_not_invoke_a_second_shutter(self):
        col = self.configure()
        self.root.deiconify()
        self.root.update()
        self.app.ready_button.focus_force()
        self.app.ready_button.event_generate('<KeyPress-space>')
        self.pump(lambda: not self.app.future and not self.app.gate and len(col.attempts) == 1)
        for _ in range(5):
            self.app.ready_button.event_generate('<KeyPress-space>')
        self.app.ready_button.event_generate('<KeyRelease-space>')
        self.root.update()
        self.assertFalse(self.app.space_down)
        self.assertIsNone(self.app.gate)
        self.assertEqual(len(col.attempts), 1)


if __name__ == '__main__':
    unittest.main()
