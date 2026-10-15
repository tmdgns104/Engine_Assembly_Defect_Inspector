"""A confirmed defect stays FAIL; uncertainty remains visible in its component."""
import copy
import unittest
from src.vision.integrated_decision import combine_decisions


class IntegratedDecisionTests(unittest.TestCase):
    def test_all_sixteen_completed_component_pairs(self):
        states = ('PASS', 'FAIL', 'REVIEW', 'ERROR')
        assembly_states = ('PASS_CANDIDATE', 'FAIL_CANDIDATE', 'REVIEW', 'ERROR')
        expected = (('PASS', 'FAIL', 'REVIEW', 'ERROR'),
                    ('FAIL', 'FAIL', 'FAIL', 'FAIL'),
                    ('REVIEW', 'FAIL', 'REVIEW', 'ERROR'),
                    ('ERROR', 'FAIL', 'ERROR', 'ERROR'))
        for i, existing in enumerate(states):
            for j, component in enumerate(assembly_states):
                with self.subTest(existing=existing, assembly=component):
                    value = combine_decisions(existing, dict(state='COMPLETE', three_frames=dict(state=component)))
                    self.assertEqual(value['decision'], expected[i][j])
                    self.assertEqual(value['existing_inspector'], existing)
                    self.assertEqual(value['assembly_inspector'], states[j])
                    self.assertEqual(value['policy'], 'ANY_CONFIRMED_FAIL_V2')

    def test_real_missing_failure_is_not_hidden_by_alignment_review(self):
        assembly = dict(state='COMPLETE', three_frames=dict(state='REVIEW'),
                        reason='SEED_INSUFFICIENT_SPATIAL_BODY_SUPPORT')
        original = copy.deepcopy(assembly)
        value = combine_decisions('FAIL', assembly)
        self.assertEqual(value['decision'], 'FAIL')
        self.assertEqual(value['reason'], 'EXISTING_FAIL_ASSEMBLY_REVIEW')
        self.assertEqual(assembly, original)

    def test_uncompleted_assembly_does_not_invent_a_defect(self):
        value = combine_decisions('PASS', dict(state='NOT_RUN', three_frames=dict(state='FAIL_CANDIDATE')))
        self.assertEqual(value['decision'], 'REVIEW')
        self.assertEqual(value['assembly_inspector'], 'REVIEW')

    def test_no_confirmed_failure_keeps_existing_uncertainty_or_error(self):
        for assembly, expected in [({}, 'REVIEW'), ({'state':'NOT_RUN'}, 'REVIEW'),
                                   ({'state':'ERROR'}, 'ERROR'), ({'state':'COMPLETE'}, 'REVIEW')]:
            self.assertEqual(combine_decisions('PASS', assembly)['decision'], expected)

    def test_unknown_basic_result_never_becomes_pass(self):
        self.assertEqual(combine_decisions('INVALID', dict(state='COMPLETE',
            three_frames=dict(state='PASS_CANDIDATE')))['decision'], 'ERROR')

    def test_confirmed_basic_defect_survives_failed_assembly(self):
        value = combine_decisions('FAIL', dict(state='ERROR', reason='ASSEMBLY_EXECUTION'))
        self.assertEqual(value['decision'], 'FAIL')
        self.assertEqual(value['assembly_inspector'], 'ERROR')


if __name__ == '__main__': unittest.main()
