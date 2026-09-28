"""Explicit --self-test only: frozen GUI/process/storage checks without a camera."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from queue import Full
import shutil
import sys
import tempfile
import time
import traceback


def synthetic_preview(settings, stream_id, stop, frames, events):
    """Exercise the real CameraClient spawn/queue contract using generated pixels."""
    import numpy as np
    from .camera import Frame
    frames.cancel_join_thread()
    sequence = 0
    metadata = dict(index=settings.index, backend=settings.backend,
                    device_name='SYNTHETIC SELF TEST', requested_width=settings.width,
                    requested_height=settings.height, width=settings.width,
                    height=settings.height, fps_reported=None, fourcc_reported=None)
    while not stop.is_set():
        sequence += 1
        pixels = np.random.default_rng(sequence).integers(
            45, 210, (settings.height, settings.width, 3), dtype=np.uint8)
        frame = Frame(pixels, datetime.now(timezone.utc), time.monotonic(),
                      sequence, stream_id, metadata)
        try:
            frames.put(frame, timeout=.1)
        except Full:
            pass
        stop.wait(.03)


def pump(root, predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while not predicate():
        if time.monotonic() >= deadline:
            raise TimeoutError('Portable GUI/process check timed out')
        root.update()
        time.sleep(.01)


def run_check(profile_path, default_output, report_path):
    """Write a bounded diagnostic receipt; never visit the user's dataset folder."""
    result = dict(pass_check=False, frozen=bool(getattr(sys, 'frozen', False)),
                  executable=sys.executable, resources=str(profile_path),
                  default_output=str(default_output), physical_camera_opened=False,
                  actual_dataset_captures=0, sample_captures=0)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    app = root = collection = scratch_folder = None
    try:
        import cv2
        import numpy as np
        import tkinter as tk
        from PIL import Image, ImageTk
        from .camera import CameraClient, CameraSettings
        from .wizard import Collection
        from .wizard_app import WizardApp
        from .wizard_plan import target_counts
        from .engine_dataset import engine_v1, CRANK_CHECKS
        from training.scripts import capture_proxy as capture
        # Preserve failed diagnostics; release writer/camera handles before successful cleanup.
        with tempfile.TemporaryDirectory(prefix='portable_sample_', dir=report_path.parent, delete=False) as scratch:
            scratch = Path(scratch)
            scratch_folder = scratch.resolve()
            root = tk.Tk()
            root.withdraw()
            errors = []
            root.report_callback_exception = lambda kind, error, trace: errors.append(str(error))
            camera = CameraClient(target=synthetic_preview)
            app = WizardApp(root, profile_path, scratch / 'raw', camera=camera)
            assert camera.process is None and camera.state == 'disconnected'
            assert not (scratch / 'raw').exists(), 'Startup must not create a collection'
            expected = {'train_candidate': 144, 'validation_candidate': 72, 'test_reserved': 72}
            assert target_counts(app.plan) == expected
            assert app.profile['objects'] == ['gray_pipe', 'exhaust_top', 'symbol_module']
            # Real Tk/Tcl and Pillow's Tcl bridge must work from bundled resources.
            photo = ImageTk.PhotoImage(Image.new('RGB', (8, 8)), master=root)
            assert photo.width() == 8
            root.update()
            result.update(product=app.product_name, counts=expected,
                          tk_version=root.tk.call('info', 'patchlevel'),
                          opencv_version=cv2.__version__, numpy_version=np.__version__,
                          startup_no_camera=True, startup_no_collection=True)
            camera.connect(CameraSettings(0, 'DSHOW', 128, 96))
            pump(root, lambda: camera.state == 'connected' and camera.latest is not None)
            first = camera.snapshot()
            pump(root, lambda: camera.latest is not None and camera.latest.sequence > first.sequence)
            frame = camera.snapshot()
            assert frame.fresh() and frame.camera['device_name'] == 'SYNTHETIC SELF TEST'
            result['frozen_camera_worker_pid'] = camera.process.pid
            result['preview_sequences'] = [first.sequence, frame.sequence]
            collection = Collection.create(scratch / 'raw', app.profile, app.guide,
                                           app.plan, True, 'sample')
            alignment = [.42, .42, .16, .16]
            collection.new_setup(frame, [.1, .1, .8, .8], 'engine_zero_reference_clockwise', alignment)
            for index in range(2):
                pump(root, lambda: camera.latest.sequence > frame.sequence)
                frame = camera.snapshot()
                if engine_v1(collection.template):
                    collection.confirm_crank(dict.fromkeys(CRANK_CHECKS, True))
                assert collection.next_action()['kind'] == 'reference'
                ticket = collection.prepare(frame, now=time.monotonic() - 2, engine_angle_confirmed=True)
                attempt = collection.save_prepared(ticket, frame)
                record = attempt['record']
                assert record['source_kind'] == 'sample'
                saved = collection.folder / 'sessions' / record['image_path']
                assert hashlib.sha256(saved.read_bytes()).hexdigest() == record['image_sha256']
                decoded = cv2.imdecode(np.fromfile(saved, dtype=np.uint8), cv2.IMREAD_COLOR)
                assert np.array_equal(decoded, frame.image)
                if collection.next_action()['kind'] == 'quality':
                    collection.acknowledge_quality(attempt['attempt_id'], True)
            assert collection.next_action()['kind'] == 'setup_review'
            folder = collection.folder
            before = list(collection.attempts)
            collection.close()
            collection = Collection.open(folder)
            assert list(collection.attempts) == before
            assert collection.next_action()['kind'] == 'setup_review'
            assert capture.profile_digest(collection.profile) == capture.profile_digest(app.profile)
            assert collection.setups[collection.setup_id]['alignment_roi'] == alignment
            export = collection.export(contact_sheets=True)
            contract = json.loads((export/'LABELING_CONTRACT.json').read_text(encoding='utf-8'))
            assert contract['class_ids'] == {'gray_pipe': 0, 'exhaust_top': 1, 'symbol_module': 2}
            assert contract['test_reserved_policy']['locked'] is True
            assert len(contract['crank_phases']) == 8
            for name in ('annotation_queue_yolo.jsonl', 'annotation_queue_mask.jsonl'):
                assert not (export/name).read_text(encoding='utf-8').strip()
            for name in ('HUMAN_CODEX_DATASET_CONTRACT_KO.md', 'DATASET_SUMMARY_KO.md',
                         'LABELING_RULES_KO.md', 'dataset_manifest.jsonl', 'normal_defect_pairs.jsonl', 'labels.csv'):
                assert (export/name).is_file(), name
            result.update(v1_contract_export=True, e04_locked=True, unapproved_samples_not_queued=True,
                          crank_phases=8, alignment_resume=True)
            result.update(sample_captures=2, png_hash_roundtrip=True,
                          resume_no_duplicate=True, pending_human_review=True)
            collection.close()
            collection = None
            app.close()
            pump(root, lambda: app.closed)
            app.executor.shutdown(wait=True)
            assert camera.process is None
            assert not errors, errors
            result.update(gui_callbacks_ok=True, camera_worker_stopped=True, pass_check=True)
    except Exception:
        result['error'] = traceback.format_exc()
    finally:
        if collection is not None:
            collection.close()
        if app is not None and not app.closed:
            app.close()
            try:
                pump(root, lambda: app.closed, seconds=8)
            except Exception:
                result['cleanup_error'] = traceback.format_exc()
                result['pass_check'] = False
            app.executor.shutdown(wait=True)
        if scratch_folder is not None:
            if result['pass_check']:
                try:
                    from .storage_paths import storage_path
                    assert scratch_folder.parent == report_path.parent.resolve()
                    assert scratch_folder.name.startswith('portable_sample_')
                    shutil.rmtree(storage_path(scratch_folder))
                except Exception:
                    result['cleanup_error'] = traceback.format_exc()
                    result['pass_check'] = False
            else:
                result['preserved_sample_workspace'] = str(scratch_folder)
        with report_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return 0 if result['pass_check'] else 1
