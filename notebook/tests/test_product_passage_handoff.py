"""Publication-time detector loss must not discard the bound product geometry."""
import copy
import unittest

from src.runtime.product_passage import ProductPassage
from src.runtime.production_profile import tracker_config
from notebook.tests.test_full_frame_request import ZONE, packet


class PassageHandoffTests(unittest.TestCase):
    def setUp(self):
        self.config = tracker_config(ZONE)
        self.identity = dict(inspection_id='current', request_token='b:1:2')

    def frame(self, seq, box=None, *, at=None):
        p = packet(seq, at if at is not None else seq*.1,
                   count=int(box is not None))
        p.update(width=1280, height=720)
        if box:
            p['provider']['observations'][0]['bbox'] = dict(
                zip(('x1', 'y1', 'x2', 'y2'), box))
        return p

    def history(self):
        # Actual second-cycle geometry: 2871 is the last positive observation,
        # 2878 is empty at publication, 2881 positively reacquires the same box.
        seed = self.frame(2871, (.345561,.174128,.892626,.869771))
        return [seed] + [self.frame(i) for i in range(2872,2879)]

    def passage(self, history):
        return ProductPassage.from_history(self.identity, history, 'left',
                                           tracker_config=self.config)

    def test_empty_publication_frame_reuses_current_observed_identity(self):
        history = self.history()
        original = copy.deepcopy(history)
        p = self.passage(history)
        self.assertFalse(p.invalid, p.status())
        self.assertIsNone(p.proof)
        for i in (2879, 2880):
            self.assertIsNone(p.observe(self.frame(i), i*.1+.01))
        q = self.frame(2881, (.346419,.184702,.890820,.816044))
        self.assertIsNone(p.observe(q, q['monotonic_s']+.01))
        self.assertFalse(p.invalid, p.status())
        self.assertEqual(p.identity, self.identity)
        self.assertEqual(history, original)
        self.assertIsNone(p.proof)  # Reacquisition is never product departure.

    def test_no_positive_baseline_is_not_a_frame_loss_or_exit(self):
        p = self.passage([self.frame(i) for i in range(10,24)])
        self.assertTrue(p.invalid)
        self.assertEqual(p.reason, 'PRODUCT_PASSAGE_PRODUCT_BASELINE_MISSING')
        self.assertIsNone(p.proof)

    def test_missed_limit_and_unobserved_time_remain_enforced(self):
        for mode in ('count', 'time'):
            p = self.passage(self.history())
            for i in range(2879,2890):
                q = self.frame(i)
                if mode == 'time':
                    q['monotonic_s'] += (i-2878)*.35
                    q['processed_monotonic'] = q['monotonic_s']+.01
                p.observe(q,q['monotonic_s']+.01)
            self.assertTrue(p.invalid, mode)
            self.assertIsNone(p.proof)

    def test_reacquisition_rejects_disjoint_or_replaced_or_invalid_product(self):
        for mode in ('disjoint','epoch','generation','hash','quality','ambiguity'):
            p = self.passage(self.history())
            q = self.frame(2879, (.34,.18,.89,.86))
            if mode == 'disjoint':
                q['provider']['observations'][0]['bbox'] = dict(x1=0.,y1=.2,x2=.1,y2=.8)
            elif mode in ('epoch','generation','hash'):
                q[dict(epoch='camera_epoch',generation='generation',hash='package_sha256')[mode]]='other'
            elif mode == 'quality': q['integrity']['valid']=False
            else: q['provider']['status']='AMBIGUOUS_FOREGROUND'
            self.assertIsNone(p.observe(q,q['monotonic_s']+.01))
            self.assertTrue(p.invalid, mode)

    def test_history_preserves_intervening_invalidity(self):
        history=self.history()
        history[-2]['integrity']['valid']=False
        p=self.passage(history)
        self.assertTrue(p.invalid)
        self.assertIsNone(p.proof)


if __name__ == '__main__':
    unittest.main()
