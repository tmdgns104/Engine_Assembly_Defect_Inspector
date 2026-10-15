"""Public, synthetic assembly evidence; no field images or trained predictions."""
from copy import deepcopy

PARTS = ('pipe_left', 'pipe_right', 'exhaust', 'symbol')


def assembly_result(state='PASS_CANDIDATE'):
    frames = []
    for index in range(3):
        parts = {}
        for name in PARTS:
            predicted = 'MISSING' if state == 'FAIL_CANDIDATE' and name == 'exhaust' else 'CORRECT'
            parts[name] = dict(valid=True, predicted_state=predicted,
                class_scores={predicted: .9, 'OTHER_FIXTURE': .1}, pixel_sha256='a'*64)
        frames.append(dict(frame_id=f'camera:{index}', camera_epoch='camera', track_id=1,
            source_pts_ns=100+index, raw_sha256=f'{index+1:064x}', raw_pixel_sha256=f'{index+4:064x}',
            evidence_validation=dict(integrity_source='WORKER_AND_VERIFIED_RAW_PNG',
                integrity={'valid': True}, image_quality={'valid': True}, quality_valid=True),
            preprocessing=dict(status='VALID', pose=dict(ok=True, matrix=[[1,0,0],[0,1,0],[0,0,1]]),
                parts={name:dict(status='VALID', essential_support={'ok':True}) for name in PARTS}),
            safe_inspection_zone={'inside':True}, shadow_state=state, parts=parts,
            images={name:dict(path=f'f{index}_{name}.png', sha256='b'*64) for name in PARTS}))
    if state in ('REVIEW', 'ERROR'):
        for frame in frames:
            frame['preprocessing'].update(status='FAILED', reason='BODY_ALIGNMENT_UNCERTAIN')
            for part in frame['parts'].values(): part['valid'] = False
    return deepcopy(dict(state='COMPLETE', frames=frames, three_frames=dict(state=state)))
