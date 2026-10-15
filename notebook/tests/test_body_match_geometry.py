"""Coordinate errors here would move every part crop, so test exact maps."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'diagnostics/body_matching'))
from geometry import quarter_turn, transform, body_regions, regions_at
from relative_lk import relative_body
import cv2


class BodyCoordinates(unittest.TestCase):
    def test_quarter_turn_preserves_pixel_identity_and_inverse(self):
        image = np.arange(35).reshape(5,7)
        points = np.array([[0,0],[6,0],[0,4],[6,4],[3,2]])
        for turn in range(4):
            rotated, matrix = quarter_turn(image,turn)
            mapped = transform(points,matrix).astype(int)
            np.testing.assert_array_equal(rotated[mapped[:,1],mapped[:,0]], image[points[:,1],points[:,0]])
            np.testing.assert_allclose(transform(mapped,np.linalg.inv(matrix)),points)

    def test_hole_background_is_excluded(self):
        labels = body_regions((30,30),{'body_regions':[{'annulus':[15,15,8,4]}]})
        np.testing.assert_array_equal(regions_at(np.array([[15,15],[21,15],[29,15],[-1,15]]),labels),[0,1,0,0])

    def test_homography_divides_projective_coordinate(self):
        p=np.array([[50,40],[10,20]])
        m=np.array([[1,0,5],[0,1,3],[.001,.002,1]])
        np.testing.assert_allclose(transform(transform(p,m),np.linalg.inv(m)),p)

    def test_relative_translation_preserves_two_surface_coordinates(self):
        rng=np.random.default_rng(22025)
        gray=rng.integers(0,256,(160,240),dtype=np.uint8)
        raw=cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)
        labels=np.zeros(gray.shape,np.uint8)
        labels[20:80,20:90]=1; labels[90:150,150:230]=2
        target=cv2.warpAffine(raw,np.float64([[1,0,1],[0,1,0]]),(240,160))
        result=relative_body(raw,target,labels)
        self.assertIsNotNone(result['matrix'])
        np.testing.assert_allclose(result['matrix'],[[1,0,1],[0,1,0]],atol=.03)
        self.assertTrue(all(n>=3 for n in result['support']))
        # Relative accuracy never certifies a reference-to-product pose.
        self.assertNotIn(result['reason'],('VALID','PASS'))

    def test_relative_blank_does_not_invent_identity_pose(self):
        raw=np.full((100,100,3),40,np.uint8)
        result=relative_body(raw,raw.copy(),np.ones((100,100),np.uint8))
        self.assertIsNone(result['matrix'])
        self.assertEqual(result['reason'],'INSUFFICIENT_RELATIVE_BODY_SUPPORT')


if __name__=='__main__':
    unittest.main()
