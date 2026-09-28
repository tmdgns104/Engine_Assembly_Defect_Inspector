"""Camera-free regression tests. All PNGs are synthetic and temporary."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import multiprocessing as mp
from pathlib import Path
from queue import Queue
import socket
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from training.capture_windows.camera import (
    BACKENDS, CameraClient, CameraSettings, Frame, camera_details, capture_loop)
from training.capture_windows.session import CollectionSession, load_display, validate_info
from training.scripts import capture_proxy as capture
from training.scripts.verify_proxy_captures import verify_session

PROFILE_PATH = Path('training/datasets/proxy/earbud_case_v0/profile.json')


def synthetic_frame(sequence=1, age=0, settings=None):
    settings = settings or CameraSettings(2, 'DSHOW', 12, 8)
    image = np.zeros((8, 12, 3), np.uint8)
    image[:, :5] = (17, 34, 230)
    image[2:4, 8:11] = (241, 120, 9)
    return Frame(image, datetime.now(timezone.utc), time.monotonic()-age, sequence,
        'SYNTHETIC_STREAM', {'index': settings.index, 'backend': settings.backend,
            'device_name': None, 'requested_width': settings.width, 'requested_height': settings.height,
            'width': 12, 'height': 8, 'fps_reported': None, 'fourcc_reported': None})


class DummyCapture:
    def __init__(self, opened=True, backend='DSHOW', frames=1, error=None):
        self.opened, self.backend, self.remaining, self.error = opened, backend, frames, error
        self.released = False
        self.open_calls = []
        self.set_calls = []

    def open(self, index, backend):
        self.open_calls.append((index, backend))
        return self.opened

    def set(self, prop, value):
        self.set_calls.append((prop, value))
        return True

    def get(self, prop):
        return float('nan')

    def getBackendName(self):
        return self.backend

    def read(self):
        if self.error:
            raise RuntimeError(self.error)
        if self.remaining:
            self.remaining -= 1
            return True, synthetic_frame().image
        return False, None

    def release(self):
        self.released = True


def fake_process(settings, stream, stop, frames, events):
    """Spawn-safe mock; never imports a camera input factory."""
    frame = synthetic_frame()
    frame.stream_id = stream
    frames.put(frame)
    stop.wait(10)


def hung_process(settings, stream, stop, frames, events):
    time.sleep(20)


class CameraTests(unittest.TestCase):
    def run_loop(self, cap, settings=None):
        frames, events = Queue(maxsize=1), Queue()
        capture_loop(settings or CameraSettings(2, 'DSHOW', 12, 8), 'TEST', Event(), frames, events, lambda: cap)
        return frames, events

    def test_windows_backend_index_is_explicit_without_fallback(self):
        for backend in BACKENDS:
            cap = DummyCapture(backend=backend)
            frames, events = self.run_loop(cap, CameraSettings(3, backend, 1280, 720))
            self.assertEqual(cap.open_calls, [(3, BACKENDS[backend])])
            self.assertEqual(frames.get_nowait().camera['width'], 12)
            self.assertTrue(cap.released)

    def test_failed_connect_releases_and_has_no_frame(self):
        cap = DummyCapture(opened=False)
        frames, events = self.run_loop(cap)
        self.assertTrue(frames.empty())
        self.assertIn('연결 실패', events.get_nowait()[1])
        self.assertEqual(len(cap.open_calls), 1)
        self.assertTrue(cap.released)

    def test_read_failure_and_exception_release(self):
        for cap in [DummyCapture(frames=0), DummyCapture(error='native read error')]:
            frames, events = self.run_loop(cap)
            self.assertTrue(frames.empty())
            self.assertEqual(events.get_nowait()[0], 'error')
            self.assertTrue(cap.released)

    def test_backend_mismatch_is_error(self):
        frames, events = self.run_loop(DummyCapture(backend='MSMF'))
        self.assertTrue(frames.empty())
        self.assertIn('요청 backend', events.get_nowait()[1])

    def test_reported_unknown_and_actual_resolution(self):
        info = camera_details(DummyCapture(), CameraSettings(0, 'DSHOW', 1280, 720), synthetic_frame().image)
        self.assertEqual((info['width'], info['height']), (12, 8))
        self.assertEqual(info['requested_width'], 1280)
        self.assertIsNone(info['fps_reported'])
        self.assertIsNone(info['fourcc_reported'])
        self.assertIsNone(info['device_name'])

    def test_frame_order_receive_timestamp_and_original_pixels(self):
        frames, _ = self.run_loop(DummyCapture(frames=4))
        f = frames.get_nowait()
        self.assertEqual(f.sequence, 4)
        self.assertEqual(f.captured_at.utcoffset().total_seconds(), 0)
        self.assertTrue(f.fresh())
        np.testing.assert_array_equal(f.image, synthetic_frame().image)

    def test_invalid_settings_rejected(self):
        for args in [(-1, 'DSHOW', 12, 8), (True, 'DSHOW', 12, 8), (0, 'V4L2', 12, 8), (0, 'MSMF', 0, 8)]:
            with self.assertRaises(ValueError):
                CameraSettings(*args)

    def test_snapshot_rejects_disconnected_stale_and_future(self):
        client = CameraClient()
        for state, frame in [('error', synthetic_frame()), ('disconnected', synthetic_frame()),
                              ('connected', synthetic_frame(age=2)), ('connected', synthetic_frame(age=-5))]:
            client.state, client.latest = state, frame
            with self.assertRaises(RuntimeError):
                client.snapshot()

    def wait_client(self, client, predicate, timeout=6):
        end = time.monotonic()+timeout
        while time.monotonic() < end:
            client.poll()
            if predicate():
                return
            time.sleep(0.02)
        self.fail('mock camera worker timeout')

    def test_process_disconnect_before_backend_switch(self):
        client = CameraClient(target=fake_process)
        try:
            client.connect(CameraSettings(2, 'DSHOW', 12, 8))
            self.wait_client(client, lambda: client.state == 'connected')
            self.assertEqual(client.snapshot().camera['index'], 2)
            with self.assertRaises(RuntimeError):
                client.connect(CameraSettings(3, 'MSMF', 12, 8))
            client.disconnect()
            self.assertIsNone(client.latest)
            self.wait_client(client, lambda: client.process is None)
            client.connect(CameraSettings(3, 'MSMF', 12, 8))
            self.assertEqual(client.settings.backend, 'MSMF')
        finally:
            client.disconnect()
            self.wait_client(client, lambda: client.process is None)

    def test_blocked_driver_owned_process_can_stop(self):
        client = CameraClient(target=hung_process)
        client.connect(CameraSettings(2, 'DSHOW', 12, 8))
        start = time.monotonic()
        client.disconnect()
        self.assertLess(time.monotonic()-start, 0.1)
        self.wait_client(client, lambda: client.process is None)
        self.assertIsNone(client.latest)
        self.assertIn('이 앱의 카메라', client.error)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = capture.load_profile(PROFILE_PATH)
        self.session = CollectionSession.create(self.root, self.profile, synthetic_frame(), source_kind='sample')
        self.session.set_scenario('NORMAL')

    def test_four_scenarios_original_pixels_and_existing_verifier(self):
        removals = [[], ['earbud_left'], ['earbud_right'], ['earbud_left', 'earbud_right']]
        for seq, (scenario, removed) in enumerate(zip(self.profile['scenarios'], removals), start=1):
            self.session.set_scenario(scenario)
            frame = synthetic_frame(seq)
            path = self.session.save(frame)
            row = self.session.records[-1]
            self.assertEqual(row['object_configuration']['objects_removed'], removed)
            self.assertIn('case', row['object_configuration']['objects_expected'])
            self.assertNotIn('case', removed)
            self.assertEqual(row['camera_source'], 'windows:DSHOW:index=2')
            self.assertEqual(row['captured_at'], frame.captured_at.isoformat())
            self.assertEqual(row['profile_sha256'], capture.profile_digest(self.profile))
            np.testing.assert_array_equal(cv2.imread(str(path)), frame.image)
        result = verify_session(self.root, self.session.session_id)
        self.assertEqual(result['captures'], 4)
        self.assertEqual(result['source_counts'], {'sample': 4})

    def test_same_episode_repeats_and_scenario_creates_new_episode(self):
        first = self.session.episode_id
        self.session.save(synthetic_frame(1))
        self.session.set_scenario('NORMAL')
        self.session.save(synthetic_frame(2))
        self.assertEqual(self.session.records[-1]['episode_id'], first)
        self.session.set_scenario('MISSING_LEFT')
        self.assertNotEqual(self.session.episode_id, first)
        current = self.session.episode_id
        self.session.new_episode()
        self.assertNotEqual(current, self.session.episode_id)

    def test_state_change_rejects_previous_frame(self):
        frame = synthetic_frame()
        self.session.set_scenario('MISSING_LEFT')
        with self.assertRaises(capture.CaptureError):
            self.session.save(frame)
        self.assertFalse(self.session.counts)

    def test_stale_frame_does_not_write(self):
        with self.assertRaises(capture.CaptureError):
            self.session.save(synthetic_frame(age=2))
        self.assertFalse(list(self.root.rglob('*.png')))

    def test_same_frame_and_concurrent_save_are_blocked(self):
        frame = synthetic_frame()
        self.session.save(frame)
        with self.assertRaises(capture.CaptureError):
            self.session.save(frame)
        self.session.save_lock.acquire()
        try:
            with self.assertRaises(capture.CaptureError):
                self.session.save(synthetic_frame(2))
        finally:
            self.session.save_lock.release()
        self.assertEqual(sum(self.session.counts.values()), 1)

    def test_new_session_ids_do_not_collide(self):
        other = CollectionSession.create(self.root, self.profile, synthetic_frame(), source_kind='sample')
        self.assertNotEqual(other.session_id, self.session.session_id)
        self.assertTrue(other.folder.is_dir())

    def test_session_info_version_and_unknown_device_properties(self):
        info = json.loads((self.session.folder/'session-info.json').read_text(encoding='utf-8'))
        validate_info(info)
        self.assertEqual(info['session_info_schema_version'], 1)
        self.assertIsNone(info['camera']['device_name'])
        self.assertIsNone(info['camera']['fps_reported'])
        self.assertIn('not sensor exposure', info['timestamp_semantics'])

    def test_reopen_restores_counts_snapshot_and_new_episode(self):
        self.session.save(synthetic_frame())
        opened = CollectionSession.open(self.session.folder)
        self.assertEqual(opened.counts, {'NORMAL': 1})
        self.assertEqual(opened.profile, self.profile)
        self.assertEqual(opened.last_path, self.session.last_path)
        opened.set_scenario('NORMAL')
        self.assertNotEqual(opened.episode_id, self.session.episode_id)
        opened.save(synthetic_frame(2))
        self.assertEqual(sum(opened.counts.values()), 2)

    def test_empty_gui_session_reopens(self):
        opened = CollectionSession.open(self.session.folder)
        self.assertEqual(opened.counts, {})

    def test_legacy_v1_and_v2_without_info_verify_readonly(self):
        for i, profile in enumerate([None, self.profile]):
            sid = f'LEGACY{i}'
            ok, png = cv2.imencode('.png', synthetic_frame().image)
            record = capture.make_record(session_id=sid, episode_id=sid+'_E1', scenario='NORMAL',
                captured_at=datetime.now(timezone.utc), width=12, height=8, device='mock',
                camera_source='mock.png', source_kind='sample', image_png=png.tobytes(), profile=profile)
            capture.save_capture(self.root, record, png.tobytes())
            opened = CollectionSession.open(self.root/sid)
            self.assertTrue(opened.read_only)
            self.assertEqual(opened.counts, {'NORMAL': 1})

    def test_changed_camera_profile_resolution_conditions_block_resume(self):
        frame = synthetic_frame()
        self.session.can_continue(self.profile, frame, '', source_kind='sample')
        changes = [('backend', 'MSMF'), ('index', 3), ('width', 640), ('requested_height', 720)]
        for key, value in changes:
            modified = synthetic_frame()
            modified.camera[key] = value
            with self.assertRaises(capture.CaptureError):
                self.session.can_continue(self.profile, modified, '', source_kind='sample')
        with self.assertRaises(capture.CaptureError):
            self.session.can_continue(self.profile, frame, 'new lighting', source_kind='sample')
        other = dict(self.profile, product_id='different')
        with self.assertRaises(capture.CaptureError):
            self.session.can_continue(other, frame, '', source_kind='sample')

    def test_real_camera_cannot_append_to_synthetic_session(self):
        with self.assertRaises(capture.CaptureError):
            self.session.can_continue(self.profile, synthetic_frame(), '', source_kind='camera')

    def test_actual_dimension_change_blocks_save(self):
        frame = synthetic_frame()
        frame.image = np.zeros((16, 24, 3), np.uint8)
        with self.assertRaises(capture.CaptureError):
            self.session.save(frame)
        self.assertFalse(list(self.root.rglob('*.png')))

    def test_manifest_partial_failure_preserves_orphan_and_blocks(self):
        with patch.object(capture, 'append_manifest', side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(capture.CaptureError, '원본을 삭제하지'):
                self.session.save(synthetic_frame())
        self.assertEqual(len(list(self.root.rglob('*.png'))), 1)
        self.assertFalse(self.session.counts)
        self.assertTrue(self.session.failed)
        with self.assertRaises(capture.CaptureError):
            self.session.save(synthetic_frame(2))
        with self.assertRaises(capture.CaptureError):
            CollectionSession.open(self.session.folder)

    def test_verify_failure_has_no_success_count(self):
        with patch('training.capture_windows.session.verify_session', side_effect=capture.CaptureError('reload failure')):
            with self.assertRaises(capture.CaptureError):
                self.session.save(synthetic_frame())
        self.assertFalse(self.session.counts)
        self.assertIsNone(self.session.last_path)
        self.assertTrue(self.session.failed)
        self.assertEqual(len(list(self.root.rglob('*.png'))), 1)

    def test_existing_corruption_rejected_on_open(self):
        self.session.save(synthetic_frame())
        self.session.last_path.write_bytes(b'corrupt synthetic file')
        with self.assertRaises(capture.CaptureError):
            CollectionSession.open(self.session.folder)

    def test_invalid_info_and_profile_hash_rejected(self):
        path = self.session.folder/'session-info.json'
        info = json.loads(path.read_text(encoding='utf-8'))
        info['profile_sha256'] = '0'*64
        path.write_text(json.dumps(info), encoding='utf-8')
        with self.assertRaises(ValueError):
            CollectionSession.open(self.session.folder)

    def test_other_product_works_without_common_code_changes(self):
        profile = {'profile_schema_version': 1, 'product_id': 'fictional_kit', 'profile_version': 1,
                   'objects': ['tray', 'red_part', 'blue_part', 'cap'],
                   'scenarios': {'NORMAL': {'objects_removed': [], 'unexpected_object': False},
                                 'CAP_ABSENT': {'objects_removed': ['cap'], 'unexpected_object': False}}}
        path = self.root/'profile.json'
        path.write_text(json.dumps(profile), encoding='utf-8')
        loaded = capture.load_profile(path)
        name, labels = load_display(path, loaded)
        self.assertEqual(labels['CAP_ABSENT'], 'CAP_ABSENT')
        session = CollectionSession.create(self.root, loaded, synthetic_frame(), source_kind='sample')
        session.set_scenario('CAP_ABSENT')
        session.save(synthetic_frame())
        self.assertEqual(verify_session(self.root, session.session_id)['product_id'], 'fictional_kit')

    def test_display_labels_are_separate_from_profile_hash(self):
        before = capture.profile_digest(self.profile)
        name, labels = load_display(PROFILE_PATH, self.profile)
        self.assertEqual(labels['MISSING_BOTH'], '양쪽 누락')
        self.assertEqual(before, capture.profile_digest(self.profile))


if __name__ == '__main__':
    unittest.main()
