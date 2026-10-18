"""Reuse only identical descriptor work within one input image."""
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'jetson'))
from src.vision.frame_matches import same_frame_matches


class Matcher:
    def __init__(self): self.calls=[]
    def knnMatch(self,left,right,k):
        self.calls.append(('knn',left.copy(),right.copy(),k))
        return tuple(tuple((int(a[0]),int(b[0])) for b in right[:k]) for a in left)
    def match(self,left,right):
        self.calls.append(('match',left.copy(),right.copy()))
        return tuple((int(a[0]),int(right[0,0])) for a in left)

class FrameMatchesTests(unittest.TestCase):
    def setUp(self):
        self.native=Matcher()
        self.owner=type('Estimator',(),{})()
        self.owner.matcher=self.native
        self.left=np.arange(8,dtype=np.uint8).reshape(2,4)
        self.right=np.arange(12,dtype=np.uint8).reshape(3,4)

    def test_identical_copied_descriptors_reuse_both_directions(self):
        with same_frame_matches(self.owner):
            matcher=self.owner.matcher
            expected=matcher.knnMatch(self.left,self.right,k=2)
            self.assertEqual(expected,matcher.knnMatch(self.left.copy(),self.right.copy(),k=2))
            reverse=matcher.match(self.right,self.left)
            self.assertEqual(reverse,matcher.match(self.right.copy(),self.left.copy()))
        self.assertEqual(len(self.native.calls),2)
        self.assertIs(self.owner.matcher,self.native)

    def test_different_frame_never_reuses_matches(self):
        for _ in range(2):
            with same_frame_matches(self.owner): self.owner.matcher.knnMatch(self.left,self.right,k=2)
        self.assertEqual(len(self.native.calls),2)

    def test_changed_bytes_shape_dtype_order_or_k_do_not_hit(self):
        with same_frame_matches(self.owner):
            matcher=self.owner.matcher
            matcher.knnMatch(self.left,self.right,k=2)
            changed=self.left.copy(); changed[0,0]=255
            matcher.knnMatch(changed,self.right,k=2)
            matcher.knnMatch(self.left.reshape(1,8),self.right,k=2)
            matcher.knnMatch(self.left.astype(np.int8),self.right,k=2)
            matcher.knnMatch(self.right,self.left,k=2)
            matcher.knnMatch(self.left,self.right,k=1)
        self.assertEqual(len(self.native.calls),6)

    def test_in_place_mutation_is_not_reused(self):
        with same_frame_matches(self.owner):
            first=self.owner.matcher.knnMatch(self.left,self.right,k=2)
            self.left[0,0]=101
            second=self.owner.matcher.knnMatch(self.left,self.right,k=2)
        self.assertNotEqual(first,second)
        self.assertEqual(len(self.native.calls),2)

    def test_exception_restores_original_matcher(self):
        with self.assertRaisesRegex(RuntimeError,'pose failed'):
            with same_frame_matches(self.owner): raise RuntimeError('pose failed')
        self.assertIs(self.owner.matcher,self.native)

    def test_over_capacity_keeps_results_correct_without_growing(self):
        with same_frame_matches(self.owner):
            matcher=self.owner.matcher
            for index in range(12):
                left=np.full((2,4),index,dtype=np.uint8)
                result=matcher.knnMatch(left,self.right,k=2)
                self.assertEqual(result[0][0][0],index)
            self.assertLessEqual(len(matcher.entries),4)
        self.assertEqual(len(self.native.calls),12)

    def test_real_opencv_correspondences_are_identical(self):
        import cv2
        rng=np.random.default_rng(26)
        reference=rng.integers(0,256,size=(50,32),dtype=np.uint8)
        current=reference[::-1].copy()
        self.owner.matcher=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=False)
        original=self.owner.matcher
        def values(matches):
            return [(m.queryIdx,m.trainIdx,m.imgIdx,m.distance) for m in matches]
        expected=[values(pair) for pair in original.knnMatch(reference,current,k=2)]
        expected_reverse=values(original.match(current,reference))
        with same_frame_matches(self.owner):
            for _ in range(2):
                self.assertEqual(expected,[values(pair) for pair in self.owner.matcher.knnMatch(reference.copy(),current.copy(),k=2)])
                self.assertEqual(expected_reverse,values(self.owner.matcher.match(current.copy(),reference.copy())))

if __name__=='__main__': unittest.main()
