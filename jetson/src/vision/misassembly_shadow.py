"""Read committed request evidence in a bounded diagnostic worker.

No camera, PLC gateway, production result mutation or model training lives here.
Inference happens after the existing inspection commits; its delay is reported
separately and never represented as the production inspection latency.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import queue
import re
import sys
import threading
import time


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_assets(root):
    manifest = json.loads((root/'FROZEN_MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = (root/item['relative_path']).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path.read_bytes()) != item['sha256']:
            raise ValueError('FROZEN_SHADOW_ASSET_MISMATCH')
    return manifest


def load_frozen_models(root):
    verify_assets(root)
    sys.path.insert(0, str(root/'jetson/shadow_misassembly'))
    from static_models import StaticShadowModels
    from pose_stability import FrameContext
    from live_observation import ThreeFrameObservation
    return StaticShadowModels(), FrameContext, ThreeFrameObservation


class ShadowObserver:
    def __init__(self, data_root, output_root, *, assets_root=None, loader=None, start=True):
        self.data_root, self.output_root = Path(data_root).resolve(), Path(output_root).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.loader = loader or (lambda: load_frozen_models(Path(assets_root)))
        self.loaded = None
        self.jobs = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.latest = {'state': 'WAITING_FOR_DURABLE_INSPECTION', 'source': 'MISASSEMBLY_SHADOW', 'plc_output': False}
        self.thread = None
        if start:
            self.thread = threading.Thread(target=self._run, name='request-shadow', daemon=True)
            self.thread.start()

    @staticmethod
    def checked_id(value):
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{32}', value):
            raise ValueError('INVALID_INSPECTION_ID')
        return value

    def _save(self, identifier, value):
        path = self.output_root/self.checked_id(identifier)
        path.mkdir(exist_ok=True)
        target = path/'result.json'
        temporary = path/'result.pending'
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(target)
        self.latest = dict(state=value['state'], inspection_id=identifier, source='MISASSEMBLY_SHADOW', plc_output=False)

    def evidence_path(self, identifier, name='result.json'):
        if name != 'result.json' and not re.fullmatch(r'f[0-2]_(raw|canonical|pipe_left|pipe_right|exhaust|symbol)\.png', name):
            raise ValueError('INVALID_SHADOW_ASSET')
        path = (self.output_root/self.checked_id(identifier)/name).resolve()
        if not path.is_relative_to(self.output_root):
            raise ValueError('SHADOW_PATH_OUTSIDE_ROOT')
        return path

    def submit(self, row):
        identifier = self.checked_id(row['inspection_id'])
        if (self.output_root/identifier).exists():
            return
        if self.stop.is_set():
            return
        try:
            self.jobs.put_nowait(deepcopy(row))
        except queue.Full:
            self._save(identifier, dict(state='NOT_RUN', reason='SHADOW_QUEUE_FULL', inspection_id=identifier,
                source='MISASSEMBLY_SHADOW', production_decision=row['decision'], plc_output=False))

    def _run(self):
        while not self.stop.is_set():
            try:
                row = self.jobs.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                self.process_one(row)
            except Exception as error:
                self._save(row['inspection_id'], dict(state='ERROR', reason=f'{type(error).__name__}:{error}',
                    inspection_id=row['inspection_id'], source='MISASSEMBLY_SHADOW',
                    production_decision=row['decision'], plc_output=False))

    def process_one(self, row):
        import cv2
        import numpy as np
        identifier = self.checked_id(row['inspection_id'])
        folder = self.output_root/identifier
        folder.mkdir(exist_ok=False)
        started = time.monotonic()
        observations = {o.get('freshness', {}).get('frame_id'): o for o in row['result'].get('observations', [])}
        prepared = []
        for asset in row['result'].get('assets', []):
            if asset['kind'] != 'raw':
                continue
            path = (self.data_root/asset['relative_path']).resolve()
            if not path.is_relative_to(self.data_root):
                raise ValueError('RAW_PATH_OUTSIDE_JOURNAL')
            data = path.read_bytes()
            if sha(data) != asset['sha256']:
                raise ValueError('RAW_FILE_HASH_MISMATCH')
            image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            observation = observations.get(asset.get('frame_id'))
            if observation is None or image is None or sha(image.tobytes()) != observation['input_pixel_sha256']:
                raise ValueError('RAW_FRAME_BINDING_OR_PIXELS_INVALID')
            prepared.append((asset, data, image, observation))
        binding = row['request'].get('runtime_binding') or {}
        if not prepared or binding.get('track_id') is None:
            result = dict(state='NOT_RUN', reason='NO_VALID_BOUND_RAW_FRAMES', frames=[])
        else:
            if self.loaded is None:
                self.loaded = self.loader()
            models, context_type, history_type = self.loaded
            models.processor.guard.reset()  # No pose/prediction leaks across products.
            history, frames = history_type(), []
            for index, (asset, data, image, observation) in enumerate(prepared):
                fresh = observation['freshness']
                context = context_type(frame_id=asset['frame_id'], source_pts_ns=fresh['source_pts_ns'],
                    track_id=binding['track_id'], camera_epoch=fresh['camera_epoch'],
                    quality_valid=bool(observation['quality']['valid'] and fresh['integrity']['valid']),
                    tracking_continuity_verified=False)
                record, canonical, crops = models.process(image, context)
                record = dict(record, frame_id=asset['frame_id'], camera_epoch=context.camera_epoch,
                    source_pts_ns=context.source_pts_ns, track_id=context.track_id,
                    raw_pixel_sha256=sha(image.tobytes()), raw_sha256=asset['sha256'],
                    raw_path=f'f{index}_raw.png', images={})
                (folder/record['raw_path']).write_bytes(data)
                for key, array in dict(crops, canonical=canonical).items():
                    if array is None:
                        continue
                    if key not in ('canonical', 'pipe_left', 'pipe_right', 'exhaust', 'symbol'):
                        raise ValueError('UNKNOWN_SHADOW_IMAGE_KIND')
                    ok, encoded = cv2.imencode('.png', array)
                    if not ok:
                        raise ValueError('SHADOW_EVIDENCE_ENCODING_FAILED')
                    name = f'f{index}_{key}.png'
                    (folder/name).write_bytes(encoded.tobytes())
                    record['images'][key] = {'path': name, 'sha256': sha(encoded.tobytes())}
                compact = dict(record, parts={k: {'predicted_state': v['predicted_state']} for k,v in record['parts'].items()})
                record['three_frames'] = history.add(compact)
                frames.append(record)
            result = dict(state='COMPLETE', frames=frames, three_frames=frames[-1]['three_frames'])
        result.update(inspection_id=identifier, source='MISASSEMBLY_SHADOW',
            production_decision=row['decision'], plc_output=False,
            timing_scope='POST_COMMIT_SHADOW_NOT_PLC_RESPONSE_LATENCY', elapsed_ms=(time.monotonic()-started)*1000)
        self._save(identifier, result)
        return result

    def status(self):
        return dict(self.latest, pending=self.jobs.qsize(), mode='POST_COMMIT_SHADOW_ONLY')

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
        return {'worker_stopped': self.thread is None or not self.thread.is_alive()}
