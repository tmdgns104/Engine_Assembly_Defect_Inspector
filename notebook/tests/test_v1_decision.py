"""V1 classification is optional; missing/corrupt durable evidence is not."""
import unittest
from copy import deepcopy
from notebook.tests.assembly_result_fixture import assembly_result
from src.vision.integrated_decision import combine_decisions


class V1DecisionTests(unittest.TestCase):
    def test_component_matrix(self):
        expected = [('PASS','PASS','PASS','PASS'), ('FAIL','FAIL','FAIL','FAIL'),
                    ('REVIEW','REVIEW','REVIEW','REVIEW'), ('ERROR','ERROR','ERROR','ERROR')]
        for i, basic in enumerate(('PASS','FAIL','REVIEW','ERROR')):
            for j, assembly in enumerate(('PASS_CANDIDATE','FAIL_CANDIDATE','REVIEW','ERROR')):
                with self.subTest(basic=basic, assembly=assembly):
                    value=combine_decisions(basic, assembly_result(assembly))
                    self.assertEqual(value['decision'], expected[i][j])
                    self.assertTrue(value['publication_allowed'])
                    self.assertEqual(value['policy'], 'BASIC_PRESENCE_ASSEMBLY_REFERENCE_V2')

    def test_summary_candidate_cannot_prove_fail_or_replace_raw_evidence(self):
        value=combine_decisions('PASS',dict(state='COMPLETE', three_frames={'state':'FAIL_CANDIDATE'}))
        self.assertFalse(value['publication_allowed'])
        self.assertNotEqual(value['decision'],'PASS')

    def test_geometry_crops_scores_and_frame_agreement_required(self):
        mutations = [lambda f:f['preprocessing'].update(status='FAILED'),
            lambda f:f['preprocessing']['pose'].update(ok=False),
            lambda f:f['safe_inspection_zone'].update(inside=False),
            lambda f:f['images'].pop('exhaust'),
            lambda f:f['parts']['exhaust'].update(valid=False),
            lambda f:f['parts']['exhaust'].update(predicted_state='CORRECT'),
            lambda f:f['parts']['exhaust'].update(class_scores={'MISSING':float('nan')}),
            lambda f:f.update(quality_review_reasons=['BODY_MOTION'])]
        for mutate in mutations:
            value=assembly_result('FAIL_CANDIDATE');mutate(value['frames'][1])
            result=combine_decisions('PASS',value)
            self.assertEqual(result['decision'],'PASS')
            self.assertFalse(result['assembly_confirmed_fail'])
            self.assertEqual(result['assembly_inspector'],'REVIEW')

    def test_raw_identity_integrity_and_unavailable_record_are_system_faults(self):
        mutations=[lambda f:f.update(frame_id='camera:0'),
            lambda f:f.update(camera_epoch='other'),
            lambda f:f.update(source_pts_ns=100),
            lambda f:f['evidence_validation']['integrity'].update(valid=False),
            lambda f:f.pop('raw_sha256')]
        for mutate in mutations:
            value=assembly_result();mutate(value['frames'][1])
            self.assertFalse(combine_decisions('PASS',value)['publication_allowed'])
        for value in ({}, {'state':'NOT_RUN'}, {'state':'ERROR','reason':'RAW_FILE_HASH_MISMATCH'},
                      {'state':'ERROR','reason':'ASSEMBLY_RECORDING_FAILED'}):
            self.assertFalse(combine_decisions('PASS',value)['publication_allowed'])

    def test_invalid_image_quality_cannot_be_upgraded_to_pass(self):
        value=assembly_result('REVIEW'); value['frames'][1]['evidence_validation'].update(quality_valid=False)
        result=combine_decisions('PASS',value)
        self.assertEqual(result['decision'],'REVIEW')

    def test_original_component_records_are_not_mutated(self):
        value=assembly_result('REVIEW');original=deepcopy(value)
        combine_decisions('PASS',value)
        self.assertEqual(value,original)
        self.assertEqual(combine_decisions('PASS',value)['assembly_reason'],'BODY_ALIGNMENT_UNCERTAIN')


if __name__=='__main__': unittest.main()
