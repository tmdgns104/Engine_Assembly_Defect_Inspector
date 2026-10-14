"""Preview admission never grants Worker quality or assembly acceptance."""
import copy
import unittest
from unittest.mock import patch
from src.vision.engine_inspector import assess_dynamic, SLOTS
from src.vision.integrated_decision import combine_decisions


class PreservedQuality(unittest.TestCase):
    def test_moving_frame_remains_review_after_admission(self):
        observations=[{'engine_dynamic':{'stable':s,'frame_id':str(i)}}
                      for i,s in enumerate((True,False,True))]
        value=dict(decision='PASS',reason_code='THREE_VALID_FRAMES',frames=[])
        with patch('src.vision.engine_inspector.aggregate_three',return_value=copy.deepcopy(value)):
            result=assess_dynamic(observations,{}, {'confirmed':True})
        self.assertEqual(result['decision'],'REVIEW')
        self.assertEqual(result['reason_code'],'ENGINE_OR_HAND_MOTION')
        self.assertEqual(result['blocking_frames'][0]['frame_id'],'1')

    def test_quality_pose_and_partial_visibility_failure_not_promoted(self):
        for code in ('ENGINE_POSE_UNCERTAIN','IMAGE_QUALITY_INSUFFICIENT',
                     'SLOT_OUTSIDE_FRAME','MULTIPLE_PRODUCT_ENVELOPES'):
            with self.subTest(code=code):
                value=dict(decision='REVIEW',reason_code=code)
                with patch('src.vision.engine_inspector.aggregate_three',return_value=value):
                    result=assess_dynamic([{'engine_dynamic':{'stable':True}}]*3,{}, {'confirmed':True})
                self.assertEqual(result,value)

    def test_stable_frames_still_require_existing_visibility_confirmation(self):
        value=dict(decision='PASS',reason_code='THREE_VALID_FRAMES')
        with patch('src.vision.engine_inspector.aggregate_three',return_value=value):
            result=assess_dynamic([{'engine_dynamic':{'stable':True}}]*3,{}, {'confirmed':True})
        self.assertEqual(result['decision'],'REVIEW')
        self.assertEqual(result['reason_code'],'HUMAN_VISIBILITY_NOT_CONFIRMED')
