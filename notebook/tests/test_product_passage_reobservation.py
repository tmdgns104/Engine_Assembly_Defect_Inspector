"""An untrusted shape sample cannot prove exit or poison a valid trajectory.

The first three boxes reproduce recorded Runtime geometry. Later paths are
synthetic boundary checks, not physical product-separation qualification.
"""
import unittest

from src.runtime.product_passage import ProductPassage
from src.runtime.production_profile import tracker_config
from notebook.tests.test_full_frame_request import ZONE, packet


class PassageShapeReobservationTests(unittest.TestCase):
    def setUp(self):
        self.config = tracker_config(ZONE)
        self.seq = 1
        self.at = 1.
        self.original = (.25345556736, .30545, .67958066463, .77381)
        self.outlier = (.20903673172, .30120, .68529949188, .77442)
        self.recovered = (.21072, .31368, .64845, .77442)
        self.passage = ProductPassage({'inspection_id': 'old'},
            self.frame(self.original), 'left', tracker_config=self.config)

    def frame(self, box):
        p = packet(self.seq, self.at, count=int(box is not None))
        p.update(width=1280, height=720)
        if box:
            p['provider']['observations'][0]['bbox'] = dict(
                zip(('x1', 'y1', 'x2', 'y2'), box))
        return p

    def observe(self, box):
        self.seq += 1
        self.at += .1
        p = self.frame(box)
        return self.passage.observe(p, self.at+.01)

    def test_recorded_shape_outlier_can_reassociate_without_exit_proof(self):
        self.assertIsNone(self.observe(self.outlier))
        self.assertFalse(self.passage.invalid)
        self.assertEqual(self.passage.box, dict(zip(('x1','y1','x2','y2'), self.original)))
        self.assertEqual(self.passage.outbound_samples, 0)
        self.assertIsNone(self.observe(self.recovered))
        self.assertFalse(self.passage.invalid)
        self.assertEqual(self.passage.outbound_samples, 1)
        self.assertIsNone(self.passage.proof)

    def test_opposite_direction_uses_same_reobservation_contract(self):
        mirror = lambda b: (1-b[2], b[1], 1-b[0], b[3])
        self.passage = ProductPassage({}, self.frame(mirror(self.original)),
            'right', tracker_config=self.config)
        self.observe(mirror(self.outlier))
        self.observe(mirror(self.recovered))
        self.assertFalse(self.passage.invalid)
        self.assertIsNone(self.passage.proof)

    def test_persistent_shape_uncertainty_expires_existing_loss_bound(self):
        for _ in range(self.config.max_missed_frames+2):
            self.assertIsNone(self.observe(self.outlier))
        self.assertTrue(self.passage.invalid)
        self.assertEqual(self.passage.reason, 'PRODUCT_PASSAGE_REOBSERVATION_LIMIT')
        self.assertIsNone(self.passage.proof)

    def test_existing_time_bound_also_expires_shape_reobservation(self):
        for _ in range(8):
            self.at += .3  # 0.4s per actual frame, below the continuity limit.
            self.assertIsNone(self.observe(self.outlier))
        self.assertTrue(self.passage.invalid)
        self.assertEqual(self.passage.reason, 'PRODUCT_PASSAGE_REOBSERVATION_LIMIT')

    def test_later_witnessed_tail_and_full_exit_window_can_prove_separation(self):
        self.observe(self.outlier)
        self.observe(self.recovered)
        for left, right in ((.16,.59),(.10,.53),(.04,.47),(0.,.43),
                            (0.,.33),(0.,.23),(0.,.13),(0.,.06)):
            self.assertIsNone(self.observe((left,.31,right,.77)))
        self.assertTrue(self.passage.tail)
        proof = None
        for _ in range(13):
            proof = self.observe(None) or proof
        self.assertIsNotNone(proof)
        self.assertTrue(proof['product_exit_claimed'])
        self.assertEqual(proof['inspection_id'], 'old')

    def test_shape_spike_and_absence_cannot_create_crossing_or_tail(self):
        self.observe((0., .30, .685, .78))
        self.assertFalse(self.passage.crossed)
        self.assertFalse(self.passage.tail)
        for _ in range(self.config.max_missed_frames+2):
            self.assertIsNone(self.observe(None))
        self.assertTrue(self.passage.invalid)
        self.assertIsNone(self.passage.proof)

    def test_uncertain_sample_cannot_hide_epoch_change_or_ambiguity(self):
        for cause in ('epoch', 'ambiguity', 'quality', 'reverse'):
            with self.subTest(cause=cause):
                self.setUp()
                self.observe(self.outlier)
                self.seq += 1
                self.at += .1
                p = self.frame(self.recovered)
                if cause == 'epoch': p['camera_epoch'] = 'replacement'
                if cause == 'ambiguity': p['provider']['status'] = 'AMBIGUOUS_FOREGROUND'
                if cause == 'quality': p['integrity']['valid'] = False
                if cause == 'reverse':
                    p['provider']['observations'][0]['bbox'].update(x1=.4, x2=.8)
                self.assertIsNone(self.passage.observe(p, self.at+.01))
                self.assertTrue(self.passage.invalid)
                self.assertIsNone(self.passage.proof)

    def test_repeated_shape_noise_with_stationary_body_is_not_departure(self):
        for _ in range(20):
            self.observe((.21, .30, .70, .78))
            self.observe(self.original)
        self.assertFalse(self.passage.invalid)
        self.assertFalse(self.passage.crossed)
        self.assertIsNone(self.passage.proof)


if __name__ == '__main__':
    unittest.main()
