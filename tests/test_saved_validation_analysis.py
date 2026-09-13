import unittest
from training.scripts.analyze_saved_validation import box_iou, distribution, summary


class SavedValidationAnalysisTests(unittest.TestCase):
    def test_known_iou_and_disjoint_boxes(self):
        self.assertAlmostEqual(box_iou([0, 0, 2, 2], [1, 0, 3, 2]), 1 / 3)
        self.assertEqual(box_iou([0, 0, 1, 1], [1, 0, 2, 1]), 0)

    def test_distribution_known_values(self):
        values = distribution([1, 2, 3])
        self.assertEqual(values['mean'], 2)
        self.assertEqual(values['median'], 2)
        self.assertAlmostEqual(values['p10'], 1.2)

    def test_missing_iou_is_not_invented_for_fn(self):
        images = [{'targets': [{}, {}], 'predictions': [{'confidence': .8}, {'confidence': .7}],
                   'false_positive_indices': [1], 'false_negative_indices': [1]}]
        result = summary(images, [{'iou': .75}])
        self.assertEqual((result['objects'], result['matched_objects'], result['fp'], result['fn']), (2, 1, 1, 1))
        self.assertEqual(result['iou_below_0_75'], 0)
        self.assertEqual(result['iou']['mean'], .75)

    def test_empty_distribution_is_explicit(self):
        self.assertIsNone(distribution([]))


if __name__ == '__main__':
    unittest.main()
