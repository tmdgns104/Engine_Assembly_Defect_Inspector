"""Combine two independent inspection results without inventing evidence."""
ASSEMBLY_STATES = {'PASS_CANDIDATE': 'PASS', 'FAIL_CANDIDATE': 'FAIL',
                   'REVIEW': 'REVIEW', 'ERROR': 'ERROR'}


def combine_decisions(existing, assembly):
    if assembly.get('state') != 'COMPLETE':
        part_decision = 'ERROR' if assembly.get('state') == 'ERROR' else 'REVIEW'
    else:
        part_decision = ASSEMBLY_STATES.get(assembly.get('three_frames', {}).get('state'), 'REVIEW')
    if existing not in ('PASS', 'FAIL', 'REVIEW', 'ERROR'):
        existing = 'ERROR'
    # Invalid evidence is kept visible; it never becomes a confident OK/NG.
    result = next(state for state in ('ERROR', 'REVIEW', 'FAIL', 'PASS')
                  if state in (existing, part_decision))
    return {'decision': result, 'existing_inspector': existing, 'assembly_inspector': part_decision,
            'policy': 'BOTH_REQUIRED_V1', 'source': 'INTEGRATED_INSPECTION',
            'reason': f'EXISTING_{existing}_ASSEMBLY_{part_decision}'}
