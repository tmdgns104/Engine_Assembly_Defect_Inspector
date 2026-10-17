"""Basic presence decides PASS/FAIL; assembly classification is reference only.

This consumes the assembly owner's durable record, not model confidence alone.
Uncertain geometry is optional analysis; lost/invalid original evidence is a
system failure and cannot authorize publication, even when basic returned FAIL.
"""
import math
import re

POLICY = 'BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2'
ASSEMBLY_STATES = {'PASS_CANDIDATE': 'PASS', 'FAIL_CANDIDATE': 'FAIL',
                   'REVIEW': 'REVIEW', 'ERROR': 'ERROR'}
PARTS = ('pipe_left', 'pipe_right', 'exhaust', 'symbol')
DEFECTS = {'MISSING', 'UPWARD_ROTATED', 'OUTWARD_SPLAYED', 'REVERSED', 'SIDEWAYS', 'UPSIDE_DOWN'}


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _raw_evidence_valid(assembly):
    frames = assembly.get('frames', [])
    if assembly.get('state') != 'COMPLETE' or len(frames) != 3:
        return False
    identities, previous = set(), None
    for frame in frames:
        validation = frame.get('evidence_validation', {})
        if (validation.get('integrity_source') not in ('WORKER_AND_VERIFIED_RAW_PNG', 'VERIFIED_RAW_PNG_REPLAY')
                or validation.get('integrity', {}).get('valid') is not True
                or not _sha(frame.get('raw_sha256')) or not _sha(frame.get('raw_pixel_sha256'))
                or not frame.get('frame_id') or not frame.get('camera_epoch')
                or frame.get('track_id') is None or type(frame.get('source_pts_ns')) is not int
                or frame['frame_id'] in identities):
            return False
        if previous and (frame['source_pts_ns'] <= previous['source_pts_ns']
                or any(frame[key] != previous[key] for key in ('camera_epoch', 'track_id'))):
            return False
        identities.add(frame['frame_id'])
        previous = frame
    return True


def _confirmed_assembly(assembly):
    """Require all three original frames, verified body pose and saved crops.

    Keep the frozen argmax and three-frame agreement; introduce no new score
    threshold or per-part rotation. A summary FAIL_CANDIDATE is insufficient.
    """
    expected = assembly.get('three_frames', {}).get('state')
    if expected not in ('PASS_CANDIDATE', 'FAIL_CANDIDATE'):
        return False
    previous_states = None
    pixels = set()
    for frame in assembly['frames']:
        pre = frame.get('preprocessing', {})
        pose = pre.get('pose', {})
        matrix = pose.get('matrix')
        if (pre.get('status') != 'VALID' or pose.get('ok') is not True
                or not isinstance(matrix, list) or len(matrix) not in (2, 3)
                or any(not isinstance(row, list) or len(row) != 3 or any(
                    type(x) not in (int, float) or not math.isfinite(x) for x in row) for row in matrix)
                or frame.get('safe_inspection_zone', {}).get('inside') is not True
                or frame.get('quality_review_reasons') or frame.get('shadow_state') != expected
                or frame['raw_pixel_sha256'] in pixels or set(frame.get('parts', {})) != set(PARTS)):
            return False
        pixels.add(frame['raw_pixel_sha256'])
        states = []
        for name in PARTS:
            crop = pre.get('parts', {}).get(name, {})
            part = frame['parts'][name]
            scores = part.get('class_scores')
            prediction = part.get('predicted_state')
            saved = frame.get('images', {}).get(name, {})
            if (crop.get('status') != 'VALID' or crop.get('essential_support', {}).get('ok') is not True
                    or part.get('valid') is not True or not _sha(part.get('pixel_sha256'))
                    or not _sha(saved.get('sha256')) or not saved.get('path')
                    or prediction not in DEFECTS | {'CORRECT'} or not isinstance(scores, dict) or not scores
                    or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores.values())
                    or prediction not in scores or scores[prediction] != max(scores.values())):
                return False
            states.append(prediction)
        actual = 'FAIL_CANDIDATE' if any(state in DEFECTS for state in states) else 'PASS_CANDIDATE'
        if actual != expected or (previous_states is not None and states != previous_states):
            return False
        previous_states = states
    return True


def combine_decisions(existing, assembly):
    if assembly.get('state') != 'COMPLETE':
        part_decision = 'ERROR' if assembly.get('state') == 'ERROR' else 'REVIEW'
    else:
        part_decision = ASSEMBLY_STATES.get(assembly.get('three_frames', {}).get('state'), 'REVIEW')
    if existing not in ('PASS', 'FAIL', 'REVIEW', 'ERROR'):
        existing = 'ERROR'
    raw_valid = _raw_evidence_valid(assembly)
    quality_valid = raw_valid and all(frame['evidence_validation'].get('quality_valid') is True
                                    for frame in assembly['frames'])
    confirmed = quality_valid and _confirmed_assembly(assembly)
    reported = part_decision
    if part_decision in ('PASS', 'FAIL') and not confirmed:
        part_decision = 'REVIEW'
    frame_reasons = [frame.get('preprocessing', {}).get('reason') for frame in assembly.get('frames', [])]
    assembly_reason = (assembly.get('reason') or next((reason for reason in frame_reasons if reason), None)
                       or assembly.get('three_frames', {}).get('reason'))
    if not raw_valid:
        result = 'FAIL' if existing == 'FAIL' else 'ERROR'
        assembly_reason = assembly_reason or 'ASSEMBLY_RAW_EVIDENCE_UNVERIFIED'
    elif existing == 'FAIL':
        result = 'FAIL'
    elif existing == 'PASS' and not quality_valid:
        result, assembly_reason = 'REVIEW', 'RAW_IMAGE_QUALITY_INVALID'
    else:
        result = existing  # Optional analysis cannot erase a valid basic PASS.
    if reported in ('PASS', 'FAIL') and not confirmed:
        assembly_reason = assembly_reason or 'THREE_FRAME_GEOMETRY_CROP_CLASSIFICATION_UNCONFIRMED'
    return {'decision': result, 'existing_inspector': existing, 'assembly_inspector': part_decision,
            'policy': POLICY, 'source': 'INTEGRATED_INSPECTION',
            'assembly_reported': reported, 'assembly_reason': assembly_reason,
            'assembly_frame_reasons': frame_reasons,
            'assembly_confirmed_fail': bool(confirmed and part_decision == 'FAIL'),
            # Preserve the verified reference classification without using it
            # to override presence, uncertainty, or a system error.
            'assembly_affects_final': False,
            'publication_allowed': raw_valid,
            'reason': f'EXISTING_{existing}_ASSEMBLY_{part_decision}'}
