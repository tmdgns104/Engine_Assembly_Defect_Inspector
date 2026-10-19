"""Safety regressions for optional margins, real truncation and direction checks."""
import unittest
import cv2
import numpy as np

from recovery import essential_support, direction_score


class SafetyGates(unittest.TestCase):
    def setUp(self):
        self.polygon = [[60,0],[199,0],[199,248],[0,248],[0,75]]

    def test_missing_optional_corner_is_not_missing_evidence(self):
        support=np.ones((249,200),np.float32)
        cv2.fillPoly(support,[np.array([[0,0],[25,0],[0,25]])],0)
        self.assertLess(float(support.mean()),.999)  # Reproduces old rejection.
        self.assertTrue(essential_support(support,self.polygon)['ok'])

    def test_one_missing_critical_pixel_must_fail(self):
        support=np.ones((249,200),np.float32);support[150,100]=0
        self.assertGreater(float(support.mean()),.999)  # Old average hides this.
        self.assertFalse(essential_support(support,self.polygon)['ok'])

    def test_interpolation_from_outside_critical_region_must_fail(self):
        support=np.ones((249,200),np.float32);support[150,100]=.97
        self.assertFalse(essential_support(support,self.polygon)['ok'])

    def test_flat_occluded_anchor_is_not_direction_evidence(self):
        rng=np.random.default_rng(42);reference=rng.integers(0,255,(72,79),dtype=np.uint8)
        self.assertLess(direction_score(reference,np.full_like(reference,140)),.35)


if __name__=='__main__':unittest.main()
