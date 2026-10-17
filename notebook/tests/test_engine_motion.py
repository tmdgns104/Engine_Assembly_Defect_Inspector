"""Target motion in camera coordinates; clocks and detector boundary are explicit."""
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'jetson'))
from src.contracts import CameraFrame
from src.vision.engine_inspector import EngineInspector


class EngineMotionTests(unittest.TestCase):
    def setUp(self):
        self.engine = EngineInspector.__new__(EngineInspector)
        self.engine.previous_gray = self.engine.stable_since = None
        self.box = dict(x1=90., y1=45., x2=210., y2=135.)
        self.products = [dict(class_name='product_envelope', confidence=.9, bounding_box=self.box)]
        self.engine.estimator = NS(cfg={'decision_policy': {'product_confidence': .5}})
        self.engine.detector = NS(detect=lambda frame: NS(to_dict=lambda: dict(detections=self.products, inference_ms=0)))

    def scene(self, background=30, shift=0, angle=0):
        image = np.full((180,320,3), background, np.uint8)
        tile = np.full((70,100,3), 105, np.uint8)
        tile[10:25,10:45] = 230
        tile[35:60,60:90] = 40
        if angle:
            tile = cv2.warpAffine(tile, cv2.getRotationMatrix2D((50,35), angle, 1), (100,70), borderValue=(105,105,105))
        image[55:125,100+shift:200+shift] = tile
        return image

    def observe(self, image, source, *, epoch='e', valid=True, processing=None):
        frame = CameraFrame(image,str(source),datetime.now(timezone.utc),320,180,'synthetic')
        observation = dict(quality={'valid':valid},freshness=dict(camera_epoch=epoch,
            source_pts_ns=int(source*1e9),estimated_source_monotonic=source))
        with patch('src.vision.engine_inspector.time.monotonic',return_value=source if processing is None else processing):
            return self.engine.observe_product(frame,observation)

    def test_background_change_does_not_reset_stationary_product(self):
        # The box includes a border; change only pixels strictly outside it.
        for index in range(6):
            image = self.scene()
            image[:, :80] = 240 if index%2 else 10
            last = self.observe(image,10+index*.2)
        self.assertTrue(last['stable'])

    def test_translation_is_not_hidden_by_following_the_bbox(self):
        self.observe(self.scene(),10)
        for index in range(1,5):
            shift=index*4
            self.box.update(x1=90.+shift,x2=210.+shift)
            last=self.observe(self.scene(shift=shift),10+index*.2)
            self.assertFalse(last['stable'])
            self.assertGreater(last['motion_fraction'],.008)

    def test_rotation_is_rejected(self):
        self.observe(self.scene(),10)
        for index in range(1,4):
            self.assertFalse(self.observe(self.scene(angle=index*12),10+index*.2)['stable'])

    def test_occlusion_pixel_change_breaks_current_streak(self):
        for i in range(6):self.observe(self.scene(),10+i*.2)
        obscured=self.scene();obscured[65:115,130:180]=10
        self.assertFalse(self.observe(obscured,11.2)['stable'])
        # If the existing pose/quality system reports uncertainty, it cannot
        # become stable merely by leaving the occluder still.
        self.assertFalse(self.observe(obscured,12.,valid=False)['stable'])
        self.assertFalse(self.observe(self.scene(),12.2)['stable'])

    def test_outside_or_nonfinite_envelope_cannot_become_stable(self):
        for box in ({'x1':-10,'y1':45,'x2':210,'y2':135},
                    {'x1':float('nan'),'y1':45,'x2':210,'y2':135}):
            with self.subTest(box=box):
                self.box.update(box)
                self.assertFalse(self.observe(self.scene(),10)['stable'])

    def test_source_clock_rollback_resets_stability(self):
        for i in range(6):self.observe(self.scene(),10+i*.2)
        self.assertFalse(self.observe(self.scene(),9.8)['stable'])

    def test_bbox_jitter_without_pixel_motion_does_not_imply_motion(self):
        for index in range(6):
            self.box.update(x1=90.+index%2,x2=210.+index%2)
            last=self.observe(self.scene(),10+index*.2)
        self.assertTrue(last['stable'])

    def test_mask_does_not_silently_tighten_existing_pixel_budget(self):
        # Existing 320x180 threshold permits 200 changed pixels. Dividing by
        # the much smaller target area would unintentionally change that limit.
        for i in range(6):
            image=self.scene();image[80:90,140:160]=230 if i%2 else 105
            last=self.observe(image,10+i*.2)
        self.assertTrue(last['stable'])

    def test_processing_delay_cannot_fill_source_stability_time(self):
        for index in range(3):
            last=self.observe(self.scene(),10+index*.1,processing=100+index*2)
        self.assertFalse(last['stable'])

    def test_loss_multiple_targets_and_invalid_quality_reset_stability(self):
        for kind in ('lost','multiple','quality'):
            with self.subTest(kind=kind):
                self.setUp()
                for i in range(6): self.observe(self.scene(),10+i*.2)
                saved=self.products
                if kind=='lost':self.products=[]
                if kind=='multiple':self.products=saved*2
                self.assertFalse(self.observe(self.scene(),11.2,valid=kind!='quality')['stable'])
                self.products=saved
                self.assertFalse(self.observe(self.scene(),11.4)['stable'])

    def test_epoch_and_repeated_source_time_cannot_preserve_stability(self):
        for i in range(6):self.observe(self.scene(),10+i*.2)
        self.assertFalse(self.observe(self.scene(),11,epoch='e')['stable'])
        self.assertFalse(self.observe(self.scene(),11.2,epoch='new')['stable'])

    def test_moving_then_stopped_requires_full_stability_interval(self):
        self.observe(self.scene(),10)
        self.observe(self.scene(shift=5),10.2)
        for t in (10.4,10.6,10.8):self.assertFalse(self.observe(self.scene(shift=5),t)['stable'])
        self.assertTrue(self.observe(self.scene(shift=5),11.2)['stable'])

    def test_new_request_reset_does_not_inherit_stable_preview(self):
        for i in range(6):self.observe(self.scene(),10+i*.2)
        self.engine.reset_motion()
        self.assertFalse(self.observe(self.scene(),11.2)['stable'])

    def test_same_mask_and_fixed_denominator_preserve_original_pixel_budget(self):
        self.observe(self.scene(),10)
        last=self.observe(self.scene(shift=4),10.2)
        evidence=last['motion_evidence']
        self.assertEqual(evidence['coordinate_space'],'camera_pixels')
        self.assertEqual(evidence['comparison_area_pixels'],120*90)
        self.assertEqual(evidence['normalization_area_pixels'],320*180)
        self.assertAlmostEqual(last['motion_fraction'],evidence['changed_pixels']/(320*180))
        self.assertAlmostEqual(evidence['target_area_motion_fraction'],evidence['changed_pixels']/(120*90))
        self.assertEqual(evidence['difference_threshold'],25)
        self.assertEqual(evidence['motion_fraction_threshold'],.008)
        self.assertEqual(evidence['stable_seconds'],.6)


if __name__=='__main__':unittest.main()
