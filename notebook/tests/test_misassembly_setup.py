"""First-run alignment through Tk events, plus missing-part writer metadata."""
import json
from pathlib import Path
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from training.capture_windows.misassembly_app import MisassemblyApp
from training.capture_windows.misassembly_ui_selftest import SampleCamera
from training.capture_windows.misassembly import SimpleCollection, load_capture_plan
from training.capture_windows.camera import CameraSettings
from training.capture_windows.session import CollectionSession
from training.capture_windows.misassembly_entry import run_diagnostic


class SetupTests(unittest.TestCase):
    def test_diagnostic_failure_returns_code_and_log_without_popup(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('training.capture_windows.misassembly_selftest.run', side_effect=RuntimeError('diagnostic failure')):
                with patch('training.capture_windows.misassembly_entry.show_startup_error') as popup:
                    self.assertEqual(run_diagnostic('--self-test', Path(folder)), 1)
            popup.assert_not_called()
            self.assertIn('diagnostic failure', (Path(folder)/'entry-error.txt').read_text(encoding='utf-8'))

    def test_pause_during_preparation_does_not_save_and_same_button_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            app = MisassemblyApp(root, home=folder, camera=SampleCamera(), auto_start=False)
            app.operator.set('pause-setup-test')
            app.connect()
            app.accept_setup()
            create = CollectionSession.create
            entered, release = threading.Event(), threading.Event()

            def delayed_create(*args, **kwargs):
                session = create(*args, **kwargs)
                entered.set()
                release.wait(5)
                return session

            def pump_until(done):
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and not done():
                    root.update()
                    time.sleep(.02)
                self.assertTrue(done(), app.status.get())

            try:
                with patch.object(CollectionSession, 'create', side_effect=delayed_create):
                    app.capture()
                    pump_until(entered.is_set)
                    app.pause()
                    release.set()
                    pump_until(lambda: app.future is None and app.gate is None)
                self.assertEqual(len(app.collection.completed), 0)
                app.capture()
                pump_until(lambda: app.future is None and app.gate is None)
                self.assertEqual(len(app.collection.completed), 1, app.status.get())
            finally:
                release.set()
                app.close()
                pump_until(lambda: app.closed)

    def test_slow_session_creation_precedes_selected_fresh_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            app = MisassemblyApp(root, home=folder, camera=SampleCamera(), auto_start=False)
            app.operator.set('slow-setup-test')
            app.connect()
            app.accept_setup()
            create = CollectionSession.create

            def slow_create(*args, **kwargs):
                session = create(*args, **kwargs)
                time.sleep(1.2)  # Longer than the live-frame freshness limit.
                return session

            try:
                with patch.object(CollectionSession, 'create', side_effect=slow_create):
                    app.capture()
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline and (app.future or app.gate):
                        root.update()
                        time.sleep(.02)
                self.assertEqual(len(app.collection.completed), 1, app.status.get())
            finally:
                app.close()
                deadline = time.monotonic() + 3
                while not app.closed and time.monotonic() < deadline:
                    root.update()
                    time.sleep(.02)

    def test_first_setup_drag_and_invalid_box_keep_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = tk.Tk()
            camera = SampleCamera()
            app = MisassemblyApp(root, home=folder, camera=camera, auto_start=False)
            try:
                root.geometry('960x650+20+20')
                app.index.set('1')
                app.connect()
                root.update()
                self.assertGreater(app.video.winfo_height(), 100)
                self.assertLess(app.capture_button.winfo_rooty()+app.capture_button.winfo_height(), root.winfo_rooty()+650)
                app.begin_alignment()
                root.update()
                camera.poll()
                app._render_video()
                x, y, width, height = app.preview_box
                expected = [.38, .28, .2, .44]
                for name, xx, yy in [('<ButtonPress-1>', .38, .28), ('<B1-Motion>', .58, .72), ('<ButtonRelease-1>', .58, .72)]:
                    app.video.event_generate(name, x=round(x+xx*width), y=round(y+yy*height))
                for actual, target in zip(app.body_roi, expected):
                    self.assertAlmostEqual(actual, target, delta=.008)
                self.assertFalse(app.setting_roi)
                self.assertTrue(app.setup_panel_open)
                app.operator.set('setup-test')
                app.accept_setup()
                self.assertTrue(app.setup_complete)
                self.assertFalse(app.setup_panel_open)
                saved = json.loads((Path(folder)/'misassembly-settings.json').read_text(encoding='utf-8'))
                self.assertEqual(saved['body_roi'], app.body_roi)
                previous = list(app.body_roi)
                app.begin_alignment()
                root.update()
                app._render_video()
                x,y,width,height=app.preview_box
                app.video.event_generate('<ButtonPress-1>', x=round(x), y=round(y))
                app.video.event_generate('<ButtonRelease-1>', x=round(x+width), y=round(y+height))
                self.assertEqual(app.body_roi, previous)
                self.assertTrue(app.setting_roi)
            finally:
                app.close()
                for _ in range(10):
                    if app.closed:
                        break
                    root.update()
                    time.sleep(.05)

    def test_missing_original_manifest_counts_and_unreviewed_state(self):
        path=Path(__file__).parents[1]/'training/capture_windows/assets/misassembly-plan.json'
        plan=load_capture_plan(path)
        step=next(s for s in plan['steps'] if s['scenario_id']=='MISSING_ALL_TARGETS')
        subset=dict(plan,steps=[step])
        camera=SampleCamera()
        camera.connect(CameraSettings(1,'DSHOW',1280,720))
        with tempfile.TemporaryDirectory() as folder:
            collection=SimpleCollection.create(Path(folder),subset)
            try:
                declaration=collection.declare(step,'missing-test')
                row=collection.save(step,camera.snapshot(),'missing-test','setup',declaration,source_kind='sample')
                raw=collection.session.records[-1]
                self.assertEqual(raw['object_configuration']['expected_counts'], {'gray_pipe':0,'exhaust_top':0,'symbol_module':0})
                self.assertEqual(set(row['part_states'].values()), {'MISSING'})
                self.assertEqual(row['review_status'],'NOT_REVIEWED')
                self.assertEqual(len(collection.completed),1)
            finally:
                collection.close()


if __name__ == '__main__':
    unittest.main()
