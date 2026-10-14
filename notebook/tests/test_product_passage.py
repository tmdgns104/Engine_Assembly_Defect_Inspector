"""Synthetic geometry only: not a field visibility or sensor qualification."""
import copy
import unittest
from src.runtime.product_passage import ProductPassage
from notebook.tests.test_full_frame_request import packet


class ProductPassageTests(unittest.TestCase):
    def setUp(self):
        self.seq=1
        self.at=1.
        self.initial=packet(self.seq,self.at)
        self.p=ProductPassage(dict(inspection_id='a'*32,track_id=1),self.initial,'right')

    def frame(self, box=None, count=1):
        self.seq+=1;self.at+=.2
        args={'count':count}
        if box:args['box']=dict(x1=box[0],y1=.1,x2=box[1],y2=.6)
        p=packet(self.seq,self.at,**args)
        return self.p.observe(p,self.at+.01)

    def tail(self):
        for box in ((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.),(.8,1.),(.9,1.)):
            self.frame(box)
        self.assertTrue(self.p.tail,self.p.status())

    def test_continuous_exit_then_new_product_no_empty_scene(self):
        self.tail()
        for _ in range(7):proof=self.frame((.1,.7))
        self.assertTrue(proof['next_product_visible'])
        self.assertFalse(proof['whole_scene_empty_required'])
        self.assertFalse(proof['sensor_cycle_observed'])
        self.assertEqual(len(proof['sequences']),7)

    def test_transient_loss_does_not_close_identity(self):
        self.frame(count=0)
        for _ in range(10):self.frame()
        self.assertTrue(self.p.invalid)
        self.assertIsNone(self.p.proof)

    def test_initial_clipping_or_box_growth_cannot_be_exit(self):
        for change in ('clipped','growth'):
            self.setUp()
            if change=='clipped':
                p=copy.deepcopy(self.initial);p['provider']['observations'][0]['bbox']['x2']=1.
                self.p=ProductPassage({},p,'right')
                for box in ((.2,1.),(.5,1.),(.8,1.),(.9,1.)):self.frame(box)
            else:self.frame((.1,1.))
            for _ in range(9):self.frame(count=0)
            self.assertIsNone(self.p.proof)

    def test_frame_gap_epoch_bad_integrity_ambiguity_fail_closed(self):
        for bad in ('gap','epoch','quality','ambiguity'):
            self.setUp();self.tail()
            p=packet(self.seq+1,self.at+.2,count=0)
            if bad=='gap':p['sequence']+=1
            if bad=='epoch':p['camera_epoch']='other'
            if bad=='quality':p['integrity']['valid']=False
            if bad=='ambiguity':p['provider']['status']='AMBIGUOUS_FOREGROUND'
            self.assertIsNone(self.p.observe(p,self.at+.21))
            self.assertTrue(self.p.invalid)

    def test_residual_exit_product_and_short_window_do_not_pass(self):
        self.tail()
        for _ in range(8):self.frame((.9,1.))
        for _ in range(5):self.frame((.1,.7))
        self.assertIsNone(self.p.proof)

    def test_leftward_exit_uses_same_policy(self):
        p=copy.deepcopy(self.initial)
        p['provider']['observations'][0]['bbox'].update(x1=.3,x2=.9)
        self.p=ProductPassage({},p,'left')
        for a,b in ((.2,.8),(.1,.7),(0.,.6),(0.,.5),(0.,.4),(0.,.3),(0.,.2),(0.,.1)):
            self.frame((a,b))
        for _ in range(7):proof=self.frame((.3,.9))
        self.assertEqual(proof['edge'],'left')

    def test_exit_tail_reversal_never_becomes_upstream_new_product(self):
        for edge in ('right', 'left'):
            with self.subTest(edge=edge):
                self.setUp()
                if edge == 'left':
                    p=copy.deepcopy(self.initial)
                    p['provider']['observations'][0]['bbox'].update(x1=.3,x2=.9)
                    self.p=ProductPassage({},p,'left')
                outbound=((.2,.8),(.3,.9),(.4,1.),(.5,1.),(.6,1.),(.7,1.),(.8,1.),(.9,1.))
                reversed_path=((.8,1.),(.7,1.),(.6,1.),(.5,1.),(.4,1.),(.3,.9),(.2,.8),(.1,.7))
                for a,b in outbound+reversed_path+((.1,.7),)*8:
                    self.frame((a,b) if edge=='right' else (1-b,1-a))
                self.assertTrue(self.p.invalid)
                self.assertEqual(self.p.reason,'PRODUCT_EXIT_TAIL_REVERSED_OR_CHANGED')
                self.assertIsNone(self.p.proof)

if __name__=='__main__':unittest.main()
