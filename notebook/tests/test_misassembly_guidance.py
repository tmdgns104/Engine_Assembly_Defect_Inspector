"""Regression checks for the restored placement and clockwise rotation guide."""
import unittest
from pathlib import Path

import numpy as np

from training.capture_windows.misassembly import load_capture_plan, capture_profile
from training.capture_windows.misassembly_guidance import DEFAULT_BODY_ROI, guide_geometry, render_guide


class GuidanceTests(unittest.TestCase):
    def test_default_box_is_original_train_setup(self):
        import json
        path=Path(__file__).parents[1]/'training/capture_windows/assets/reference-framing.json'
        reference=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(DEFAULT_BODY_ROI, reference['alignment_roi'])
        self.assertEqual(reference['split'], 'train')
        self.assertFalse(reference['annotation_bbox'])
        for angle in range(0, 360, 10):
            for position in ('CENTER', 'OFFSET_RIGHT'):
                guide_geometry(DEFAULT_BODY_ROI, position, angle, (1280,720))
        geo = guide_geometry(DEFAULT_BODY_ROI, 'CENTER', 0, (1280,720))
        self.assertAlmostEqual(geo['center'][1], (.07631578947368421+.8263157894736842/2)*720)
        self.assertGreater(max(y for x,y in geo['polygon']), 679)
        self.assertLess(max(y for x,y in geo['polygon']), 700)

    def test_box_center_rotation_and_raw_preservation(self):
        raw = np.full((720, 1280, 3), 80, dtype=np.uint8)
        roi = [.4, .28, .2, .44]
        center = guide_geometry(roi, 'CENTER', 0, (1280, 720))
        right = guide_geometry(roi, 'OFFSET_RIGHT', 90, (1280, 720))
        self.assertAlmostEqual(right['center'][0] - center['center'][0], 1280 * .08)
        self.assertAlmostEqual(right['tip'][1], right['center'][1])
        self.assertGreater(right['tip'][0], right['center'][0])
        shown = render_guide(raw, roi, 'OFFSET_RIGHT', 90)
        self.assertFalse(np.array_equal(np.asarray(shown), raw))
        self.assertTrue((raw == 80).all())

    def test_all_rotation_corners_stay_in_frame(self):
        for angle in range(0, 360, 10):
            for position in ('CENTER', 'OFFSET_RIGHT'):
                geo = guide_geometry([.4, .28, .2, .44], position, angle, (1280, 720))
                for x, y in geo['polygon']:
                    self.assertTrue(0 <= x < 1280 and 0 <= y < 720)
        with self.assertRaises(ValueError):
            guide_geometry([.1, .1, .8, .8], 'OFFSET_RIGHT', 0, (1280, 720))

    def test_defects_complete_360_in_state_groups(self):
        path = Path(__file__).parents[1] / 'training/capture_windows/assets/misassembly-plan.json'
        plan = load_capture_plan(path)
        groups = {}
        for step in plan['steps']:
            groups.setdefault((step['scenario_id'], step['target_position']), []).append(step['target_engine_angle'])
        for (scenario, position), angles in groups.items():
            if scenario != 'NORMAL' and not scenario.startswith('MISSING'):
                self.assertEqual(angles, list(range(0, 360, 10)))
        self.assertEqual(sum(s.get('capture_reason') == 'new_device_control' for s in plan['steps']), 6)
        gaps = [s for s in plan['steps'] if s.get('capture_reason') == 'missing_recorded_training_angle']
        self.assertEqual(len(gaps), 144)
        for step in gaps:
            self.assertNotIn(step['target_engine_angle'], plan['existing_coverage'][step['scenario_id']])
        self.assertEqual(len(plan['steps']), 654)
        profile = capture_profile(plan)
        self.assertEqual(profile['scenarios']['MISSING_PIPE_LEFT']['expected_counts']['gray_pipe'], 1)
        self.assertEqual(profile['scenarios']['MISSING_ALL_TARGETS']['expected_counts'],
                         {'gray_pipe': 0, 'exhaust_top': 0, 'symbol_module': 0})


if __name__ == '__main__':
    unittest.main()
