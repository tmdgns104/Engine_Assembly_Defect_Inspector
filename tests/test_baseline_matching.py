import unittest
from training.scripts.evaluate_baseline import match_detections


class BaselineMatchingTests(unittest.TestCase):
    def setUp(self):
        self.target = [{'class_id': 0, 'xyxy': [0, 0, 10, 10]}]
        self.prediction = {'class_id': 0, 'xyxy': [0, 0, 10, 10], 'confidence': 0.9}

    def test_correct_match(self):
        result = match_detections([self.prediction], self.target)
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['false_negative_indices'], [])

    def test_wrong_class_is_fp_and_fn(self):
        result = match_detections([{**self.prediction, 'class_id': 1}], self.target)
        self.assertEqual(result['false_positive_indices'], [0])
        self.assertEqual(result['false_negative_indices'], [0])

    def test_duplicate_is_one_fp(self):
        result = match_detections([self.prediction, {**self.prediction, 'confidence': 0.5}], self.target)
        self.assertEqual(len(result['matches']), 1)
        self.assertEqual(result['false_positive_indices'], [1])

    def test_low_iou_is_fp_and_fn(self):
        result = match_detections([{**self.prediction, 'xyxy': [8, 8, 18, 18]}], self.target)
        self.assertEqual(result['false_positive_indices'], [0])
        self.assertEqual(result['false_negative_indices'], [0])


if __name__ == '__main__':
    unittest.main()
