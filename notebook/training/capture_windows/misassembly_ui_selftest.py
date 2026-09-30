"""Actual Tk event-loop regression with an explicitly synthetic camera.

Runs in an isolated folder and never opens physical devices or real collections.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time
import traceback
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
from PIL import ImageGrab

from .camera import CameraClient, Frame
from .misassembly_app import MisassemblyApp, assets_folder
from .session import CollectionSession


class SampleCamera(CameraClient):
    source_kind = 'sample'

    def __init__(self):
        super().__init__()
        self.calls = []
        self.sequence = 0
        self.streaming = True
        # Guidance-only NORMAL, explicitly marked as sample, not new training data.
        self.raw = cv2.imdecode(np.fromfile(assets_folder()/'normal_reference.png', np.uint8), cv2.IMREAD_COLOR)

    def connect(self, settings):
        self.calls.append(settings)
        self.settings = settings
        self.process = object()
        self.state, self.error = 'connected', ''
        self.poll()

    def disconnect(self):
        self.process = self.latest = None
        self.state = 'disconnected'

    def poll(self):
        if self.process is not None and self.streaming:
            self.sequence += 1
            detail = dict(index=self.settings.index, backend=self.settings.backend, device_name=None,
                          width=1280, height=720, requested_width=self.settings.width,
                          requested_height=self.settings.height, fps_reported=None, fourcc_reported=None)
            self.latest = Frame(self.raw.copy(), datetime.now(timezone.utc), time.monotonic(),
                                self.sequence, 'synthetic-ui-stream', detail)


def run(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda kind, value, trace: errors.append(str(value))
    camera = SampleCamera()
    app = MisassemblyApp(root, home=destination, camera=camera, auto_start=False)
    checks, screenshots = [], []

    def pump(seconds=.2, until=None):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            root.update()
            if until and until():
                break
            time.sleep(.02)
        assert not errors, errors

    def screenshot(name):
        root.deiconify()
        pump(.3)
        path = Path(tempfile.gettempdir()) / f'misassembly-{destination.name}-{name}.png'
        # The desktop-region helper can capture an unrelated covering window.
        # Pillow's native window capture reads only this owned Tk surface.
        ImageGrab.grab(window=int(root.frame(),16)).save(path)
        screenshots.append(str(path))

    try:
        pump()
        app.index.set('2')
        app.resolution.set('640x480')
        app.connect()  # Empty operator must not prevent preview.
        pump()
        assert camera.calls[-1].index == 2 and camera.calls[-1].width == 640
        app.connect()  # Reconnect waits for this app's previous worker to stop.
        pump(.3)
        assert len(camera.calls) == 2 and camera.calls[-1].index == 2
        checks.append('preview_connection_without_operator_and_selected_resolution')
        app.operator.set('UI-selftest')
        app.accept_setup()
        pump()
        assert not app.setup_panel_open and app.setup_complete
        # Isolate adjacent angle/state transitions; the stored plan is still complete metadata.
        defect = [s for s in app.plan['steps'] if s['scenario_id'] == 'LEFT_PIPE_UP']
        app.plan = dict(app.plan, steps=[defect[0], defect[1], app.plan['steps'][-1]])
        app.refresh()
        root.geometry('960x650+20+20')
        pump()
        assert app.capture_button.winfo_rooty()+app.capture_button.winfo_height() < root.winfo_rooty()+650
        assert app.video.winfo_height() >= 230
        assert app.recent.winfo_rooty()+65 <= app.capture_button.winfo_rooty()
        screenshot('960x650')
        root.geometry('1240x820+20+20')
        pump()
        assert app.video.winfo_width() > 800
        screenshot('1240x820')
        checks.append('responsive_live_canvas_and_visible_capture')
        event = SimpleNamespace(widget=root)
        app._space_press(event)
        step_id = app.pending_capture['step']['step_id']
        app.operator.set('changed-after-click')
        for _ in range(5):
            app._space_press(event)
            app.capture_button.invoke()
        assert app.collection.next_step['step_id'] == step_id
        pump(15, until=lambda: app.future is None and len(app.collection.completed) == 1)
        assert len(app.collection.completed) == 1
        row = next(iter(app.collection.records.values()))
        assert row['operator'] == 'UI-selftest'
        assert row['target_engine_angle'] == 0 and row['review_status'] == 'NOT_REVIEWED'
        assert row['guide_setup']['body_roi'] == app.body_roi
        assert row['source_kind'] == 'sample'
        saved = cv2.imdecode(np.fromfile(app.collection.folder/row['raw_relative_path'], np.uint8), cv2.IMREAD_COLOR)
        assert np.array_equal(saved, camera.raw), 'overlay contaminated raw'
        app._space_press(event)  # Still holding Space after save must do nothing.
        pump(.5)
        assert len(app.collection.completed) == 1 and app.gate is None
        app._space_release(event)
        checks.append('one_input_fresh_save_auto_next_frozen_metadata_and_no_repeat')
        app.capture_button.invoke()
        pump(15, until=lambda: len(app.collection.completed) == 2 and app.future is None)
        assert len(app.collection.completed) == 2
        assert app.collection.next_step['scenario_id'] == 'SYMBOL_UPSIDE_DOWN'
        checks.append('angle_and_state_transitions_without_confirmation')
        app.retake()
        assert len(app.collection.completed) == 1
        assert app.collection.next_step['target_engine_angle'] == 10
        pump(.5)
        with patch.object(CollectionSession, 'save', side_effect=OSError('UI simulated disk failure')):
            app.capture_button.invoke()
            pump(15, until=lambda: app.gate is None and app.future is None)
        assert len(app.collection.completed) == 1
        pump(.5)
        app.capture_button.invoke()
        pump(15, until=lambda: len(app.collection.completed) == 2 and app.future is None)
        assert len(app.collection.completed) == 2
        checks.append('retake_preserves_original_and_disk_failure_same_button_retry')
        camera.disconnect()
        app.next_click_after = 0
        app.capture_button.invoke()
        assert len(app.collection.completed) == 2
        app.connect()
        pump()
        assert all(s.index == 2 for s in camera.calls)
        camera.streaming = False
        pump(1.2)
        app.capture_button.invoke()
        assert len(app.collection.completed) == 2 and app.gate is None
        camera.streaming = True
        pump()
        checks.append('disconnect_stale_no_progress_and_no_device_fallback')
        with patch('os.startfile'):
            app.finish()
        folder = app.collection.folder
        expected = app.collection.next_step['step_id']
        app.close()
        pump(.3, until=lambda: app.closed)
        root = tk.Tk()
        app = MisassemblyApp(root, home=destination, camera=SampleCamera(), auto_start=False)
        assert app.collection.next_step['step_id'] == expected
        assert len(app.collection.completed) == 2 and len(app.plan['steps']) == 3
        checks.append('resume_original_plan_and_no_duplicate_count')
    except Exception:
        (destination/'failure.txt').write_text(traceback.format_exc()+'\nUI status: '+app.status.get()+
                                               '\nCamera: '+app.camera.state, encoding='utf-8')
        raise
    finally:
        if not app.closed:
            app.close()
            pump(.4, until=lambda: app.closed)
    (destination/'result.json').write_text(json.dumps(dict(status='PASS', checks=checks, screenshots=screenshots), ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


def run_camera(destination, index):
    """Explicit developer check: preview only, no declarations or dataset saves."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    root = tk.Tk()
    app = MisassemblyApp(root, home=destination, auto_start=False)
    app.index.set(str(index))
    started = time.monotonic()
    app.connect()
    sequences, detail = set(), None
    first_frame_seconds = None
    # Covers the bounded worker bootstrap, driver wait and 40 preview updates.
    deadline = started + 60
    try:
        while time.monotonic() < deadline and len(sequences) < 40:
            root.update()
            if app.camera.latest and app.camera.latest.fresh():
                if first_frame_seconds is None:
                    first_frame_seconds = time.monotonic() - started
                sequences.add(app.camera.latest.sequence)
                detail = app.camera.latest.camera
            time.sleep(.04)
        result = dict(status='PASS' if len(sequences) >= 40 else 'NOT_VERIFIED',
                      fresh_sequences=len(sequences), camera=detail, error=app.camera.error,
                      data_saved=False, device_name_verified=False,
                      first_frame_seconds=first_frame_seconds,
                      worker_startup_seconds=(None if app.camera.worker_started is None else app.camera.worker_started-app.camera.started),
                      scope='actual Tk preview and spawned CameraClient; selected index only; no fallback')
        (destination/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        app.close()
        deadline = time.monotonic()+6
        while not app.closed and time.monotonic() < deadline:
            root.update()
            time.sleep(.04)
    return 0 if result['status'] == 'PASS' else 1
