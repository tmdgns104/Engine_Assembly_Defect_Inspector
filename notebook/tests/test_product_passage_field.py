"""Recorded geometry regressions; no images, PLC writes or field qualification.

Coordinates below reproduce the real Runtime consumer's stopped/outbound
sequence. The successor is synthetic and is never evidence of a field repeat.
"""
import unittest

from src.runtime.product_passage import ProductPassage
from src.runtime.production_profile import tracker_config
from notebook.tests.test_full_frame_request import ZONE, packet


class FieldPassageTests(unittest.TestCase):
    def setUp(self):
        self.seq = 2002
        self.at = 1.
        self.origin = self.make((.3570, .2374, .9071, .9079))
        self.p = ProductPassage({'inspection_id': 'old', 'request_token': 'b:1:1'},
                                self.origin, 'left', tracker_config=tracker_config(ZONE))

    def make(self, coords):
        p = packet(self.seq, self.at, count=int(coords is not None))
        p.update(width=1280, height=720)
        if coords is not None:
            p['provider']['observations'][0]['bbox'] = dict(zip(('x1','y1','x2','y2'), coords))
        return p

    def frame(self, coords, gap=1):
        self.seq += gap
        self.at += .1*gap
        p = self.make(coords)
        return self.p.observe(p, self.at+.01)

    def outbound(self):
        # Includes subpixel stationary jitter, shape jitter and one dropped
        # Runtime observation. None of those alone is clearance evidence.
        coordinates = [(.3572,.2383,.9062,.8732), (.3560,.2379,.9060,.8886),
            (.3564,.2363,.9075,.8893), (.3574,.2367,.8968,.8496),
            (.3057,.2327,.8618,.8897), (.2848,.2412,.8499,.8985),
            (.2535,.2396,.8203,.9244), (.2151,.2439,.7883,.8781),
            (.1769,.2280,.7678,1.), (.1426,.2406,.7236,1.),
            (.1,.2356,.6867,1.), (.0516,.227,.6398,1.),
            (.0451,.2344,.6008,1.), (.008,.2355,.5897,1.),
            (.0031,.2497,.4871,1.), (0.,.2378,.4597,1.),
            (0.,.2918,.3842,1.), (0.,.3043,.3342,1.),
            (0.,.3119,.2969,1.), (0.,.3078,.247,1.),
            None, (0.,.3217,.2022,1.), (0.,.3166,.1968,.778)]
        for i, box in enumerate(coordinates):
            self.assertIsNone(self.frame(box, gap=2 if i==4 else 1))
        self.assertFalse(self.p.invalid, self.p.status())

    def test_recorded_outbound_needs_positive_new_entry_not_absence(self):
        self.outbound()
        for _ in range(20):
            self.assertIsNone(self.frame(None))
        self.assertIsNone(self.p.proof)
        proof = None
        for left in (.85,.82,.79,.76,.73,.7,.67):
            proof = self.frame((left,.24,1.,.86)) or proof
        self.assertIsNotNone(proof, self.p.status())
        self.assertEqual(proof['reason'],'OUTBOUND_PRODUCT_AND_NEW_UPSTREAM_ENTRY')
        self.assertFalse(proof['whole_scene_empty_required'])
        self.assertFalse(proof['product_exit_claimed'])

    def test_no_outbound_path_no_new_cycle(self):
        for _ in range(20):
            self.frame(None)
        for left in (.85,.8,.75,.7):
            self.assertIsNone(self.frame((left,.24,1.,.86)))
        self.assertIsNone(self.p.proof)

    def test_stationary_jitter_never_qualifies(self):
        for _ in range(20):
            self.assertIsNone(self.frame((.356,.236,.907,.90)))
        self.assertIsNone(self.p.proof)

    def test_old_product_reappearing_at_exit_is_not_new_entry(self):
        self.outbound()
        for _ in range(20):
            self.frame(None)
        for _ in range(10):
            self.assertIsNone(self.frame((0.,.3,.2,.8)))
        self.assertIsNone(self.p.proof)

    def test_new_box_in_middle_without_entry_is_not_new_cycle(self):
        self.outbound()
        for _ in range(20):
            self.frame(None)
        for _ in range(10):
            self.assertIsNone(self.frame((.4,.24,.9,.86)))
        self.assertIsNone(self.p.proof)

    def test_frame_loss_does_not_accumulate_clear_window(self):
        self.outbound()
        for _ in range(12):
            self.assertIsNone(self.frame(None,gap=2))
        for left in (.85,.82,.79):
            self.assertIsNone(self.frame((left,.24,1.,.86)))

    def test_reverse_and_ambiguity_still_block(self):
        for kind in ('reverse','ambiguity','epoch'):
            with self.subTest(kind=kind):
                self.setUp();self.outbound()
                if kind=='reverse':
                    self.frame((.10,.3,.4,.9))
                else:
                    self.seq+=1;self.at+=.1
                    p=self.make(None)
                    if kind=='epoch':p['camera_epoch']='different'
                    else:p['provider']['status']='AMBIGUOUS_FOREGROUND'
                    self.p.observe(p,self.at+.01)
                self.assertTrue(self.p.invalid)
                self.assertIsNone(self.p.proof)

    def test_interrupted_new_entry_is_not_accumulated(self):
        self.outbound()
        for _ in range(20):self.frame(None)
        self.frame((.85,.24,1.,.86))
        self.frame((.82,.24,1.,.86))
        self.frame((0.,.3,.2,.8))  # The old exit strip is occupied again.
        self.assertIsNone(self.frame((.79,.24,1.,.86)))
        self.assertIsNone(self.p.proof)

    def test_entry_evidence_survives_product_becoming_fully_visible(self):
        self.outbound()
        for _ in range(20):self.frame(None)
        self.assertIsNone(self.frame((.85,.24,1.,.86)))
        self.assertIsNone(self.frame((.82,.24,1.,.86)))
        proof=self.frame((.77,.24,.99,.86))
        self.assertIsNotNone(proof,self.p.status())

    def test_recorded_outbound_width_changes_use_adjacent_geometry(self):
        # Actual next field trial 2703..2719: gradual bbox width changes while
        # both horizontal edges move left. A fixed initial-width ceiling lost
        # this continuous track at 2719 (0.59226 versus 0.58828 ceiling).
        self.origin=self.make((.35843,.24587,.89670,.95530))
        self.p=ProductPassage({'inspection_id':'old'},self.origin,'left',
                              tracker_config=tracker_config(ZONE))
        boxes=[
            (0.35877, 0.24543, 0.89886, 0.94469),
            (0.35815, 0.24273, 0.89691, 0.94595),
            (0.35954, 0.24388, 0.89694, 0.91972),
            (0.35694, 0.24112, 0.8938, 0.92124),
            (0.34144, 0.24512, 0.88807, 0.89494),
            (0.314, 0.24383, 0.87876, 0.9352),
            (0.29123, 0.24093, 0.85327, 0.8953),
            (0.26092, 0.23754, 0.84244, 1),
            (0.24162, 0.24337, 0.81504, 0.9764),
            (0.23756, 0.23596, 0.79652, 1),
            (0.20093, 0.2281, 0.76865, 1),
            (0.19058, 0.231, 0.75304, 1),
            (0.14917, 0.22536, 0.7352, 1),
            (0.13063, 0.2301, 0.71553, 1),
            (0.1051, 0.23488, 0.69157, 1),
            (0.08427, 0.23268, 0.67653, 1),
        ]
        for b in boxes:
            self.assertIsNone(self.frame(b))
            self.assertFalse(self.p.invalid,self.p.status())

    def test_sudden_unassociated_width_expansion_still_blocks(self):
        # A width-only outlier stays untrusted. Sustained uncertainty still
        # expires the existing loss bound; it never supplies departure proof.
        for _ in range(self.p.tracker_config.max_missed_frames+2):
            self.assertIsNone(self.frame((.10,.24,.92,.95)))
            self.assertIsNone(self.p.proof)
        self.assertTrue(self.p.invalid)
        self.assertIsNone(self.p.proof)

    def test_observed_edge_entry_not_exactly_clipped_to_image_boundary(self):
        # Actual first-entry boxes 2578..2584 from the same field recording,
        # replayed as a synthetic successor, not a proven physical repeat.
        self.outbound()
        for _ in range(20):self.frame(None)
        proof=None
        for box in [(0.88551,0.19666,0.99710,0.82111),
                    (0.87940,0.22041,0.99706,0.82302),
                    (0.84716,0.23720,0.99892,0.84064),
                    (0.84219,0.24326,0.99934,0.84647),
                    (0.82561,0.24869,0.99891,0.89081),
                    (0.80335,0.24405,0.99896,0.91342),
                    (0.78898,0.24721,0.99931,0.87907)]:
            proof=self.frame(box) or proof
            self.assertFalse(self.p.invalid,self.p.status())
        self.assertIsNotNone(proof,self.p.status())
        self.assertFalse(proof['product_exit_claimed'])


if __name__ == '__main__':
    unittest.main()
