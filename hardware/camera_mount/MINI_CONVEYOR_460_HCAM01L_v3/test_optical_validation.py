"""Small adversarial checks for the optical intersection predicate."""
import unittest
import numpy as np
import trimesh
import optical_validation as optical


class OpticalIntersectionTests(unittest.TestCase):
    def setUp(self):
        self.origin=np.array([0.,0.,10.])
        self.normals,self.bounds=optical.fov_planes(self.origin,90,70,2,0,0)
        self.probe=[0,0,5]

    def result(self,mesh):
        return optical.intersection_check(mesh,self.normals,self.bounds,self.probe)['intersection']

    def test_far_box_clear(self):
        mesh=trimesh.creation.box([2,2,2])
        mesh.apply_translation([30,0,5])
        self.assertEqual(self.result(mesh),'NONE')

    def test_solid_inside_fov_rejected(self):
        mesh=trimesh.creation.box([2,2,2])
        mesh.apply_translation([0,0,5])
        self.assertEqual(self.result(mesh),'FOUND')

    def test_crossing_without_inside_vertices(self):
        mesh=trimesh.creation.box([100,100,1])
        mesh.apply_translation([0,0,5])
        self.assertFalse(np.any(np.all(mesh.vertices@self.normals.T<=self.bounds,axis=1)))
        self.assertEqual(self.result(mesh),'FOUND')

    def test_fov_fully_enclosed_by_mesh(self):
        self.assertEqual(self.result(trimesh.creation.box([100,100,100])),'FOUND')

    def test_pupil_rear_is_not_optical_space(self):
        mesh=trimesh.creation.box([2,2,2])
        mesh.apply_translation([0,0,12])
        self.assertEqual(self.result(mesh),'NONE')

    def test_clear_cavity_is_not_solid_containment(self):
        outside=trimesh.creation.box([100,100,100])
        cavity=trimesh.creation.box([60,60,60])
        cavity.invert()
        shell=trimesh.util.concatenate([outside,cavity])
        self.assertEqual(self.result(shell),'NONE')

    def test_margin_rejects_near_boundary(self):
        mesh=trimesh.creation.box([1,1,1])
        mesh.apply_translation([10,0,5])
        self.assertEqual(self.result(mesh),'NONE')
        n,b=optical.fov_planes(self.origin,90,70,2,5,0)
        self.assertEqual(optical.intersection_check(mesh,n,b,self.probe)['intersection'],'FOUND')


if __name__=='__main__':
    unittest.main()
