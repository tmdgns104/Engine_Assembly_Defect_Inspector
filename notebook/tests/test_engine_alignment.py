"""Rotating human guides use synthetic pixels only; no physical camera access."""
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from training.capture_windows.engine_alignment import alignment_marks, validate_alignment
from training.capture_windows.wizard_plan import target_roi
from training.capture_windows.wizard_quality import overlay
from test_dataset_wizard import wizard_frame
from test_engine_dataset_v1 import Fixture


class EngineAlignmentTests(unittest.TestCase):
    def test_clockwise_pixel_geometry_and_direction_on_wide_camera(self):
        roi = [.4, .25, .2, .5]
        for angle in (0, 30, 90, 120, 180, 240, 330):
            with self.subTest(angle=angle):
                polygon, center, exhaust, chevron = alignment_marks(roi, angle, (1280, 720))
                self.assertEqual(center, (640., 360.))
                radians = math.radians(angle)
                np.testing.assert_allclose(exhaust, [640+180*math.sin(radians), 360-180*math.cos(radians)])
                self.assertEqual(chevron[1], exhaust)
                self.assertAlmostEqual(math.dist(polygon[0], polygon[1]), 256)
                self.assertAlmostEqual(math.dist(polygon[1], polygon[2]), 360)
        top = alignment_marks(roi, 0, (1280, 720))[2]
        bottom = alignment_marks(roi, 180, (1280, 720))[2]
        self.assertGreater(bottom[1], top[1])

    def test_fixed_quality_region_and_original_pixels_are_unchanged(self):
        frame = wizard_frame(990)
        before = frame.image.copy()
        envelope, guide = [.1, .1, .8, .8], [.43, .30, .14, .40]
        pictures = []
        for angle in (0, 90, 120):
            placement = {'dx': 0, 'dy': 0, 'angle_deg': angle, 'rotation_only': True}
            np.testing.assert_allclose(target_roi(envelope, placement, (320, 240)), envelope)
            pictures.append(np.asarray(overlay(frame.image, envelope, placement, guide)))
        np.testing.assert_array_equal(frame.image, before)
        self.assertFalse(np.array_equal(pictures[0], pictures[1]))
        self.assertFalse(np.array_equal(pictures[1], pictures[2]))

    def test_all_angle_bounds_and_malformed_selections(self):
        validate_alignment([.43, .3, .14, .4], [.1, .1, .8, .8], (320, 240))
        for roi in ([.1, .1, .8, .8], [.05, .3, .15, .4], [0, 0, float('nan'), .4], [.4, .4, .01, .1]):
            with self.subTest(roi=roi), self.assertRaises(ValueError):
                validate_alignment(roi, [.1, .1, .8, .8], (320, 240))

    def test_setup_resume_keeps_display_geometry_without_auto_confirmation(self):
        with tempfile.TemporaryDirectory(prefix='align_', dir='.cache') as folder:
            fx = Fixture(folder)
            try:
                original_setup = fx.col.setup_id
                self.assertNotIn('alignment_roi', fx.col.setups[original_setup])
                guide = [.43, .3, .14, .4]
                fx.col.new_setup(wizard_frame(10002), [.1, .1, .8, .8], 'engine_zero_reference_clockwise', guide)
                with self.assertRaises(ValueError):
                    fx.col.new_setup(wizard_frame(10003), [.1, .1, .8, .8], 'engine_zero_reference_clockwise', [.1, .1, .8, .8])
                fx.reopen()
                self.assertEqual(fx.col.setups[fx.col.setup_id]['alignment_roi'], guide)
                self.assertIn(original_setup, fx.col.setups)
                self.assertEqual(fx.col.next_action()['kind'], 'crank_setup')
                self.assertFalse(fx.col.setups[fx.col.setup_id]['confirmed'])
                self.assertFalse(fx.col.final_test_unlocked)
                self.assertEqual(fx.col.summary()['saved'], 0)
                self.assertFalse(list(Path(folder).rglob('*.png')))
            finally:
                fx.col.close()


if __name__ == '__main__':
    unittest.main()
