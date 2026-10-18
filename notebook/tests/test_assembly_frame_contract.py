"""Worker -> durable Journal -> assembly evidence contract, without device I/O.

Camera metadata deliberately matches GStreamer: it does NOT supply integrity.
Private field PNGs are replayed separately; no factory images/DB ship in Git.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from src.journal.sqlite import Journal
from src.vision.assembly_inspection import AssemblyInspector
from src.vision.inspection_worker import worker_main
from src.vision.integrated_decision import combine_decisions
from test_field_worker import FakeCamera
from notebook.tests.assembly_result_fixture import assembly_result, PARTS


class CameraWithoutIntegrity(FakeCamera):
    def capture(self):
        # GStreamer owns a distinct pixel array per capture, not a reused buffer.
        self.image = np.full((720, 1280, 3), 80 + self.sequence % 80, np.uint8)
        frame = super().capture()
        return frame


class AssemblyBoundary:
    """Only the expensive frozen models are doubled; persistence/loader are real."""
    def __init__(self, state='FAIL_CANDIDATE'):
        self.state, self.contexts = state, []
        self.processor = SimpleNamespace(guard=SimpleNamespace(reset=lambda: None))

    def process(self, image, context):
        self.contexts.append(context)
        state = self.state if context.quality_valid else 'REVIEW'
        record = assembly_result(state)['frames'][0]
        record.update(shadow_state=state, reason='MODEL_OR_QUALITY_EVIDENCE')
        return record, image, {name:image for name in PARTS}


def inspector(root, model, *, start=False):
    (root/'assembly').mkdir(exist_ok=True)
    history = lambda: SimpleNamespace(add=lambda record: dict(
        state=record['shadow_state'], reason='MODEL_BOUNDARY_FIXTURE'))
    return AssemblyInspector(root, root/'assembly',
        loader=lambda: (model, SimpleNamespace, history), start=start)


def stored_row(root, *, integrity=None):
    """Real Journal JSON/PNG boundary with the actual observation field layout."""
    journal = Journal(root)
    request = dict(cell_id='offline', plc_session_id=1, request_id=1, cycle_id=1,
        attempt=1, control_mode='production', runtime_binding=dict(
            track_id=1, camera_epoch='camera', worker_generation='worker'))
    identifier, _ = journal.admit(request, {})
    observations, images = [], []
    for index in range(3):
        image = np.full((24, 32, 3), 80+index, np.uint8)
        frame_id = f'camera:{8833+index}'
        fresh = dict(frame_id=frame_id, sequence=8833+index, camera_epoch='camera',
            source_pts_ns=663941479372+index*168000000,
            estimated_source_monotonic=71433.745+index*.168,
            received_monotonic=71433.753+index*.168, age_seconds=.008)
        if integrity is not None:
            fresh['integrity'] = deepcopy(integrity)
        observation = dict(frame_id=frame_id, width=32, height=24, freshness=fresh,
            quality=dict(valid=True, mean_brightness=float(80+index), blur_variance=0.),
            input_pixel_sha256=hashlib.sha256(image.tobytes()).hexdigest(),
            engine_dynamic={key: fresh[key] for key in ('frame_id', 'camera_epoch', 'source_pts_ns')})
        observations.append(observation)
        images.append(dict(kind='raw', frame_id=frame_id, width=32, height=24,
            data=cv2.imencode('.png', image)[1].tobytes()))
    journal.finish(identifier, dict(decision='FAIL', observations=observations), images)
    row = journal.detail(identifier)
    journal.db.close()
    return row


class AssemblyContractTests(unittest.TestCase):
    def setUp(self):
        # Windows cannot fsync a read-only fd. Durability is tested unmocked on
        # the required Jetson/POSIX run; this shim changes no evidence validation.
        if os.name == 'nt':
            self.fsync = patch('src.vision.assembly_inspection.os.fsync')
            self.fsync.start()
            self.addCleanup(self.fsync.stop)

    def test_worker_without_camera_integrity_survives_journal_and_assembly(self):
        recipe = dict(observation_count=3, rule='presence_count', reference_class=None,
            slots=[dict(id='part', expected_count=1, allowed_classes=['part'])])
        package = SimpleNamespace(manifest={'files': {}, 'model_version': 'offline'},
            manifest_hash='offline', recipe=recipe, capture={'width':1280,'height':720})
        detector = SimpleNamespace(close=lambda: None, runtime_metadata=lambda: {},
            detect=lambda frame: SimpleNamespace(to_dict=lambda: dict(
                frame_id=frame.frame_id, detections=[], inference_ms=0.)))
        station = dict(camera_device='/dev/OFFLINE', frame_spacing_seconds=.01,
            max_frame_age_seconds=1., quality=dict(min_blur_variance=0,
                min_mean_brightness=0, max_mean_brightness=255))
        commands, results, previews = queue.Queue(), queue.Queue(), queue.Queue(maxsize=1)
        stopping, cancel = threading.Event(), threading.Event()
        request = dict(cell_id='offline', plc_session_id=1, request_id=1, cycle_id=1,
            attempt=1, kind='inspect', view_assessment={}, control_mode='production',
            runtime_binding=dict(track_id=1, camera_epoch='fixture', worker_generation='worker'))
        with tempfile.TemporaryDirectory() as directory, \
             patch('src.vision.inspection_worker.load_package', return_value=package), \
             patch('src.camera.gstreamer_camera.GStreamerCamera', CameraWithoutIntegrity), \
             patch('src.vision.detector_factory.create_detector', return_value=detector):
            root = Path(directory)
            journal = Journal(root)
            identifier, _ = journal.admit(request, {})
            now = time.monotonic()
            commands.put(dict(inspection_id=identifier, request=request,
                accepted_monotonic=now, deadline=now+6))
            thread = threading.Thread(target=worker_main, args=('offline', station, 'worker',
                commands, results, previews, stopping, cancel, SimpleNamespace(value=0)), daemon=True)
            thread.start()
            try:
                message = results.get(timeout=6)
                self.assertEqual(message['type'], 'ready', message)
                message = results.get(timeout=6)
                self.assertEqual(message['type'], 'result', message)
                self.assertEqual(len(message['result']['observations']), 3, message)
            finally:
                stopping.set()
                thread.join(4)
            self.assertFalse(thread.is_alive())
            journal.finish(identifier, message['result'], message['images'])
            row = journal.detail(identifier)
            journal.db.close()
            for observation in row['result']['observations']:
                self.assertEqual(observation['frame_evidence_contract'], 'RAW_FRAME_INTEGRITY_V1')
                self.assertEqual(observation['worker_generation'], 'worker')
                self.assertTrue(observation['freshness']['integrity']['valid'])
                self.assertEqual(observation['freshness']['integrity']['detector'], 'KNOWN_STRIPE_PATTERN_V1')
            model = AssemblyBoundary()
            assembled = inspector(root, model).process_one(row)
            self.assertEqual(assembled['state'], 'COMPLETE')
            self.assertEqual(assembled['source'], 'ASSEMBLY_INSPECTOR')
            self.assertFalse(assembled['used_by_final_policy'])
            self.assertTrue(assembled['evidence_required_before_publication'])
            for observation, context in zip(row['result']['observations'], model.contexts):
                fresh = observation['freshness']
                self.assertEqual((context.frame_id, context.source_pts_ns, context.camera_epoch),
                    (fresh['frame_id'], fresh['source_pts_ns'], fresh['camera_epoch']))

    def test_legacy_missing_integrity_remeasured_only_from_hash_verified_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = stored_row(root)
            original = deepcopy(row)
            value = inspector(root, AssemblyBoundary()).process_one(row)
            self.assertEqual(value['state'], 'COMPLETE')
            self.assertEqual(row, original)  # Never patch the historical Journal.
            self.assertTrue(all(f['evidence_validation']['integrity_source'] ==
                'VERIFIED_RAW_PNG_REPLAY' for f in value['frames']))
            final = combine_decisions('PASS', value)
            self.assertEqual(final['decision'], 'PASS')
            self.assertEqual(final['assembly_inspector'], 'FAIL')
            self.assertFalse(final['assembly_affects_final'])

    def test_corrupted_png_or_pixel_hash_never_reaches_models(self):
        for corruption in ('file', 'pixels'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = stored_row(root)
                if corruption == 'file':
                    path = root/row['result']['assets'][0]['relative_path']
                    path.write_bytes(path.read_bytes()+b'changed')
                else:
                    row['result']['observations'][0]['input_pixel_sha256'] = '0'*64
                model = AssemblyBoundary()
                with self.assertRaises(ValueError):
                    inspector(root, model).process_one(row)
                self.assertEqual(model.contexts, [])

    def test_missing_new_integrity_or_identity_mismatch_rejected(self):
        for fault in ('new_missing', 'unknown_version', 'frame', 'epoch', 'source',
                      'duplicate', 'generation', 'missing_quality'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = stored_row(root)
                obs = row['result']['observations'][1]
                if fault == 'new_missing': obs['frame_evidence_contract'] = 'RAW_FRAME_INTEGRITY_V1'
                if fault == 'unknown_version': obs['frame_evidence_contract'] = 'unknown'
                if fault == 'frame': obs['frame_id'] = 'other'
                if fault == 'epoch': obs['freshness']['camera_epoch'] = 'other'
                if fault == 'source': obs['freshness']['source_pts_ns'] += 1
                if fault == 'duplicate': row['result']['observations'].append(deepcopy(obs))
                if fault == 'generation': obs['worker_generation'] = 'other'
                if fault == 'missing_quality': del obs['quality']
                model = AssemblyBoundary()
                with self.assertRaisesRegex(ValueError, 'EVIDENCE_'):
                    inspector(root, model).process_one(row)
                self.assertEqual(model.contexts, [])

    def test_invalid_quality_and_integrity_stay_review(self):
        for invalid in ('quality', 'integrity', 'raw_stripes'):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                row = stored_row(root, integrity={'valid': True})
                for obs, asset in zip(row['result']['observations'], row['result']['assets']):
                    if invalid == 'quality': obs['quality']['valid'] = False
                    if invalid == 'integrity': obs['freshness']['integrity'] = dict(valid=False, reason='CAPTURE_REJECTED')
                    if invalid == 'raw_stripes':
                        image = np.zeros((24, 32, 3), np.uint8)
                        image[::2] = 255
                        data = cv2.imencode('.png', image)[1].tobytes()
                        (root/asset['relative_path']).write_bytes(data)
                        asset['sha256'] = hashlib.sha256(data).hexdigest()
                        obs['input_pixel_sha256'] = hashlib.sha256(image.tobytes()).hexdigest()
                value = inspector(root, AssemblyBoundary('PASS_CANDIDATE')).process_one(row)
                self.assertEqual(combine_decisions('PASS', value)['decision'], 'REVIEW' if invalid=='quality' else 'ERROR')
                self.assertTrue(all(not frame['evidence_validation']['quality_valid'] for frame in value['frames']))

    def test_missing_legacy_evidence_is_durable_error_not_keyerror(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = stored_row(root)
            del row['result']['observations'][0]['quality']
            observer = inspector(root, AssemblyBoundary(), start=True)
            try:
                observer.submit(row)
                deadline = time.monotonic()+4
                value = None
                while time.monotonic() < deadline:
                    # Wait for the atomically created result before resolving it
                    # (Windows can expand a missing ancestor to an 8.3 path).
                    if (root/'assembly'/row['inspection_id']/'result.json').is_file():
                        value = observer.result(row['inspection_id'])
                    if value: break
                    time.sleep(.02)
                self.assertIsNotNone(value)
                self.assertEqual(value['state'], 'ERROR')
                self.assertIn('EVIDENCE_QUALITY_MISSING_OR_INVALID', value['reason'])
                self.assertNotIn('KeyError', value['reason'])
                self.assertEqual(combine_decisions('PASS', value)['decision'], 'ERROR')
            finally:
                observer.close()

    def test_repeated_assembly_completion_queues_only_one_plc_result(self):
        from unittest.mock import Mock
        from notebook.tests.test_opener_guards import DurableIdentityGuards
        for model_state, decision, plc_value in (
                ('PASS_CANDIDATE', 'PASS', 0), ('FAIL_CANDIDATE', 'PASS', 0),
                ('REVIEW', 'PASS', 0), ('ERROR', 'PASS', 0)):
            with self.subTest(model_state=model_state):
                fixture = DurableIdentityGuards()
                fixture.setUp()
                try:
                    identifier = fixture.candidate()
                    runtime = fixture.r
                    runtime.bridge = SimpleNamespace(inspection_id=identifier,
                        poll=lambda: None, error=None, phase='INSPECTION_DURABLE')
                    runtime.assembly = SimpleNamespace(submit=Mock(), result=lambda _: assembly_result(model_state),
                        evidence_path=lambda _: 'offline-assembly/result.json')
                    runtime.line_profile, runtime.error = {'assembly_deadline_s':30}, None
                    for now in range(5, 10):
                        runtime._poll_result(now)
                    fixture.h.publish.assert_called_once()
                    self.assertEqual(fixture.h.publish.call_args.args[1], decision)
                    self.assertEqual(runtime.history[0]['plc_result_value'], plc_value)
                    self.assertTrue(runtime.history[0]['plc_done_requested'])
                    count = fixture.journal.db.execute("SELECT count(*) FROM service_state WHERE key LIKE 'integrated_decision:%'").fetchone()[0]
                    self.assertEqual(count, 1)
                finally:
                    fixture.tearDown()


if __name__ == '__main__':
    unittest.main()
