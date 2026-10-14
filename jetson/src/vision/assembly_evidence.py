"""Validate committed raw evidence before any assembly model sees its pixels.

Legacy observations may omit capture integrity. Only a hash-verified original
PNG can supply a new measurement of the existing stripe detector. This does not
reconstruct missing quality, timestamps or camera identity, or edit the Journal.
"""
import hashlib
import math

from src.camera.frame_integrity import FRAME_EVIDENCE_CONTRACT, measured_integrity


def _frame_metadata(observation, binding):
    fresh = observation.get('freshness')
    if not isinstance(fresh, dict):
        raise ValueError('EVIDENCE_FRESHNESS_MISSING')
    frame_id, epoch, pts = (fresh.get(key) for key in ('frame_id', 'camera_epoch', 'source_pts_ns'))
    if (not isinstance(frame_id, str) or not frame_id or not isinstance(epoch, str) or not epoch
            or type(pts) is not int or pts < 0):
        raise ValueError('EVIDENCE_FRAME_IDENTITY_MISSING')
    for source in (observation, observation.get('engine_dynamic') or {}):
        for key in ('frame_id', 'camera_epoch', 'source_pts_ns'):
            if key in source and source[key] != fresh[key]:
                raise ValueError('EVIDENCE_FRAME_IDENTITY_MISMATCH:' + key)
    if binding.get('camera_epoch') is not None and binding['camera_epoch'] != epoch:
        raise ValueError('EVIDENCE_CAMERA_EPOCH_MISMATCH')
    generation = observation.get('worker_generation')
    if generation is not None and binding.get('worker_generation') not in (None, generation):
        raise ValueError('EVIDENCE_WORKER_GENERATION_MISMATCH')
    quality = observation.get('quality')
    if not isinstance(quality, dict) or type(quality.get('valid')) is not bool:
        raise ValueError('EVIDENCE_QUALITY_MISSING_OR_INVALID')
    contract = observation.get('frame_evidence_contract')
    if contract not in (None, FRAME_EVIDENCE_CONTRACT):
        raise ValueError('EVIDENCE_CONTRACT_UNSUPPORTED')
    if contract == FRAME_EVIDENCE_CONTRACT:
        if not isinstance(fresh.get('integrity'), dict):
            raise ValueError('EVIDENCE_INTEGRITY_MISSING')
        if not generation or observation.get('frame_id') != frame_id:
            raise ValueError('EVIDENCE_WORKER_IDENTITY_MISSING')
        if type(fresh.get('sequence')) is not int:
            raise ValueError('EVIDENCE_SEQUENCE_MISSING')
        for key in ('estimated_source_monotonic', 'received_monotonic'):
            value = fresh.get(key)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError('EVIDENCE_SOURCE_TIME_MISSING:' + key)
    return fresh


def load_assembly_frames(data_root, row):
    import cv2
    import numpy as np
    binding = row['request'].get('runtime_binding') or {}
    observations = {}
    for observation in row['result'].get('observations', []):
        fresh = _frame_metadata(observation, binding)
        if fresh['frame_id'] in observations:
            raise ValueError('EVIDENCE_DUPLICATE_OBSERVATION')
        observations[fresh['frame_id']] = observation
    prepared, seen = [], set()
    previous = None
    for asset in row['result'].get('assets', []):
        if asset['kind'] != 'raw':
            continue
        path = (data_root/asset['relative_path']).resolve()
        if not path.is_relative_to(data_root):
            raise ValueError('RAW_PATH_OUTSIDE_JOURNAL')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != asset.get('sha256'):
            raise ValueError('RAW_FILE_HASH_MISMATCH')
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        observation = observations.get(asset.get('frame_id'))
        if (observation is None or image is None or hashlib.sha256(image.tobytes()).hexdigest()
                != observation.get('input_pixel_sha256')):
            raise ValueError('RAW_FRAME_BINDING_OR_PIXELS_INVALID')
        fresh = observation['freshness']
        if fresh['frame_id'] in seen:
            raise ValueError('EVIDENCE_DUPLICATE_RAW_FRAME')
        seen.add(fresh['frame_id'])
        if previous:
            if fresh['camera_epoch'] != previous['camera_epoch']:
                raise ValueError('EVIDENCE_CAMERA_EPOCH_CHANGED')
            for key in ('source_pts_ns', 'sequence', 'estimated_source_monotonic'):
                if key in fresh and key in previous and fresh[key] <= previous[key]:
                    raise ValueError('EVIDENCE_FRAME_ORDER_INVALID:' + key)
        previous = fresh
        for source in (asset, observation, fresh):
            for key, size in (('width', image.shape[1]), ('height', image.shape[0])):
                if key in source and source[key] != size:
                    raise ValueError('EVIDENCE_DIMENSIONS_MISMATCH')
        integrity = measured_integrity(image, fresh.get('integrity'))
        validation = dict(integrity_source=('WORKER_AND_VERIFIED_RAW_PNG'
            if 'integrity' in fresh else 'VERIFIED_RAW_PNG_REPLAY'),
            integrity=integrity, image_quality=observation['quality'],
            quality_valid=observation['quality']['valid'] and integrity['valid'],
            frame_evidence_contract=observation.get('frame_evidence_contract', 'LEGACY_RAW_RECHECK'),
            worker_generation=observation.get('worker_generation'),
            sequence=fresh.get('sequence'), estimated_source_monotonic=fresh.get('estimated_source_monotonic'))
        prepared.append((asset, data, image, observation, validation))
    if seen != set(observations):
        raise ValueError('EVIDENCE_RAW_OBSERVATION_SET_MISMATCH')
    return prepared
