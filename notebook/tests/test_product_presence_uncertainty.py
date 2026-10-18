"""Only evaluated missing parts may be classified as an assembly FAIL."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import numpy as np
from src.decision.engine_dynamic import SLOTS, inspect_frame, aggregate_three


class ProductPresenceUncertaintyTests(unittest.TestCase):
    def frame(self, number, **changes):
        value=dict(frame_id=str(number),source_pts_ns=number,inspection_id='test',camera_epoch='epoch',
            decision='PASS',reason_code='ALL_REQUIRED_PARTS_PRESENT',quality_valid=True,
            assignment_reliable=True,slot_states=dict.fromkeys(SLOTS,'PRESENT'))
        value.update(changes)
        return value

    def test_below_threshold_is_unassessed_not_missing_parts(self):
        estimator=SimpleNamespace(cfg={'decision_policy':{'product_confidence':.5}},estimate=Mock())
        detections=[dict(class_name='product_envelope',confidence=.48528575897216797,
                         bounding_box=dict(x1=2,y1=2,x2=18,y2=18))]
        result=inspect_frame(np.zeros((20,20,3),np.uint8),detections,estimator)
        self.assertEqual(result['decision'],'REVIEW')
        self.assertEqual(result['product_selection']['detail'],'CANDIDATES_BELOW_THRESHOLD')
        self.assertEqual(result['slot_states'],dict.fromkeys(SLOTS,'NOT_EVALUATED'))
        self.assertEqual(result['defects'],[])
        estimator.estimate.assert_not_called()

    def test_no_product_does_not_prove_missing_parts(self):
        estimator=SimpleNamespace(cfg={'decision_policy':{'product_confidence':.5}})
        result=inspect_frame(np.zeros((20,20,3),np.uint8),[],estimator)
        self.assertEqual(result['decision'],'REVIEW')
        self.assertEqual(result['product_selection']['detail'],'NO_RETURNED_CANDIDATES')

    def test_any_unassessed_frame_blocks_pass_and_fail(self):
        for count in (1,3):
            frames=[self.frame(i) for i in (1,2,3)]
            for i in range(count):
                frames[i].update(decision='FAIL',reason_code='PRODUCT_ENVELOPE_NOT_FOUND',
                    slot_states=dict.fromkeys(SLOTS,'NOT_EVALUATED'))
            with self.subTest(count=count):
                result=aggregate_three(frames)
                self.assertEqual(result['decision'],'REVIEW')
                self.assertEqual(result['defects'],[])
                self.assertEqual(len(result['blocking_frames']),count)

    def test_three_evaluated_missing_observations_still_fail(self):
        frames=[self.frame(i) for i in (1,2,3)]
        for frame in frames:frame['slot_states']['pipe_left']='MISSING'
        result=aggregate_three(frames)
        self.assertEqual(result['decision'],'FAIL')
        self.assertEqual(result['reason_code'],'LEFT_PIPE_MISSING')
        self.assertEqual(result['slot_states']['pipe_left'],'MISSING_CONFIRMED')

    def test_three_present_observations_still_pass(self):
        self.assertEqual(aggregate_three([self.frame(i) for i in (1,2,3)])['decision'],'PASS')

    def test_bad_frame_identity_remains_error(self):
        frame=self.frame(1,reason_code='PRODUCT_ENVELOPE_NOT_FOUND',decision='FAIL')
        result=aggregate_three([copy.deepcopy(frame) for _ in range(3)])
        self.assertEqual(result['decision'],'ERROR')
        self.assertEqual(result['reason_code'],'FRESH_FRAME_IDENTITY_INVALID')
