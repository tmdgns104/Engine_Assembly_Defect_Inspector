"""Frozen synthetic save/resume/retake/export check; never opens a camera."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np

from .camera import Frame
from .misassembly import SimpleCollection, load_capture_plan
from .misassembly_app import assets_folder
from .session import CollectionSession


def run(destination):
    plan = load_capture_plan(assets_folder() / 'misassembly-plan.json')
    subset = dict(plan, steps=plan['steps'][:2])
    data = destination / 'data'
    data.mkdir(parents=True, exist_ok=False)
    camera = dict(index=7, backend='DSHOW', device_name=None,
                  requested_width=320, requested_height=240, width=320, height=240,
                  fps_reported=None, fourcc_reported=None)

    def frame(number):
        image = np.random.default_rng(number).integers(60, 180, (240, 320, 3), dtype=np.uint8)
        return Frame(image, datetime.now(timezone.utc), time.monotonic(), number, 'test-stream', camera)

    collection = SimpleCollection.create(data / 'collections', subset)
    try:
        first_step = collection.next_step
        first_declared = collection.declare(first_step, 'selftest')
        first = collection.save(first_step, frame(1), 'selftest', 'setup-1', first_declared, source_kind='sample')
        assert len(collection.completed) == 1
        assert first['part_states'] == subset['steps'][0]['part_states']
        assert first['review_status'] == 'NOT_REVIEWED'
        assert first['measured_angle'] is None
        assert first['source_group_id'].startswith(collection.folder.name)
        assert first['declaration_id'] == first_declared['declaration_id']
        try:
            collection.save(subset['steps'][0], frame(2), 'selftest', 'setup-1', first_declared, source_kind='sample')
        except ValueError:
            pass
        else:
            raise AssertionError('duplicate step was accepted')
        collection.supersede_last()
        assert len(collection.completed) == 0
        assert first['capture_id'] in collection.superseded
        retry_step = collection.next_step
        retry_declared = collection.declare(retry_step, 'selftest')
        collection.save(retry_step, frame(3), 'selftest', 'setup-1', retry_declared, source_kind='sample')
        assert len(collection.completed) == 1
        folder = collection.folder
    finally:
        collection.close()
    reopened = SimpleCollection.open(folder)
    try:
        assert len(reopened.completed) == 1
        assert reopened.next_step['step_id'] == subset['steps'][1]['step_id']
        handoff = reopened.export()
        assert (handoff / 'sessions').is_dir()
        assert len((handoff / 'capture-manifest.jsonl').read_text(encoding='utf-8').splitlines()) == 2
    finally:
        reopened.close()
    failed = SimpleCollection.create(data / 'collections', subset)
    failed_folder = failed.folder
    try:
        failed_step = failed.next_step
        failed_declared = failed.declare(failed_step, 'selftest')
        with patch.object(CollectionSession, 'save', side_effect=OSError('simulated disk failure')):
            try:
                failed.save(failed_step, frame(4), 'selftest', 'setup-2', failed_declared, source_kind='sample')
            except OSError:
                pass
            else:
                raise AssertionError('storage failure was accepted')
        assert len(failed.completed) == 0
    finally:
        failed.close()
    recovered = SimpleCollection.open(failed_folder)
    try:
        assert len(recovered.completed) == 0
        recovered_step = recovered.next_step
        recovered_declared = recovered.declare(recovered_step, 'selftest')
        recovered.save(recovered_step, frame(5), 'selftest', 'setup-2', recovered_declared, source_kind='sample')
        assert len(recovered.completed) == 1
    finally:
        recovered.close()
    destination.mkdir(exist_ok=True)
    (destination / 'result.json').write_text(json.dumps({'status': 'PASS', 'checks': [
        'save', 'metadata', 'duplicate', 'supersede', 'resume', 'export',
        'storage_failure_no_progress', 'retry_after_reopen']}), encoding='utf-8')
    return 0
