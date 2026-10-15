"""Combine two independent inspection results without inventing evidence."""
POLICY = 'ANY_CONFIRMED_FAIL_V2'
ASSEMBLY_STATES = {'PASS_CANDIDATE': 'PASS', 'FAIL_CANDIDATE': 'FAIL',
                   'REVIEW': 'REVIEW', 'ERROR': 'ERROR'}


def combine_decisions(existing, assembly):
    if assembly.get('state') != 'COMPLETE':
        part_decision = 'ERROR' if assembly.get('state') == 'ERROR' else 'REVIEW'
    else:
        part_decision = ASSEMBLY_STATES.get(assembly.get('three_frames', {}).get('state'), 'REVIEW')
    if existing not in ('PASS', 'FAIL', 'REVIEW', 'ERROR'):
        existing = 'ERROR'
    # Either completed component can prove a defect. Preserve the other
    # component's REVIEW/ERROR for diagnosis; it cannot erase that defect.
    # STOP, lost requests and storage failures still block publication outside
    # this pure decision function. Only two PASS components produce PASS.
    result = next(state for state in ('FAIL', 'ERROR', 'REVIEW', 'PASS')
                  if state in (existing, part_decision))
    return {'decision': result, 'existing_inspector': existing, 'assembly_inspector': part_decision,
            'policy': POLICY, 'source': 'INTEGRATED_INSPECTION',
            'reason': f'EXISTING_{existing}_ASSEMBLY_{part_decision}'}
