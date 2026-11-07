import unittest
import numpy as np
from operators.pose_space import preview_transform,transform_pose


class WorldPoseSpace(unittest.TestCase):
    def test_world_up_is_independent_of_bind_mesh_up(self):
        # A Z-up bind mesh can have an evaluated Y-up pose. Converting by the
        # former makes an upright actor look as though it is falling backward.
        matrix=preview_transform(np.eye(4))
        np.testing.assert_allclose(matrix[:3,:3]@[0,1,0],[0,0,1])
        np.testing.assert_allclose(matrix[:3,:3]@[0,0,1],[0,-1,0])
        self.assertAlmostEqual(np.linalg.det(matrix[:3,:3]),1)

    def test_renderer_translation_rotation_scale_units_and_normals(self):
        renderer=np.array([[0,-3,0,10],[2,0,0,20],[0,0,4,30],[0,0,0,1.]])
        p=np.array([[1.,2,3]]);normal=np.array([[1.,1,1]])/np.sqrt(3);posed_inverse=np.eye(4)[None]
        old=[a.copy() for a in (p,normal,posed_inverse,renderer)]
        vertices,normals,bind=transform_pose(p,normal,posed_inverse,renderer,100.)
        np.testing.assert_allclose(vertices,[[.04,-.42,.22]])
        expected=np.array([-1/3,-1/4,1/2]);expected/=np.linalg.norm(expected)
        np.testing.assert_allclose(normals,[expected])
        # A transformed tangent stays perpendicular to the normal, even with
        # nonuniform scale; positions use translation but normals never do.
        tangent=preview_transform(renderer,100.)[:3,:3]@[1,-1,0]
        self.assertAlmostEqual(float(tangent@normals[0]),0)
        np.testing.assert_allclose((np.c_[vertices,[1]]@bind[0].T)[:,:3],p)
        for actual,before in zip((p,normal,posed_inverse,renderer),old):np.testing.assert_array_equal(actual,before)

    def test_invalid_frames_and_inputs_fail(self):
        for matrix,units in ((np.zeros((4,4)),1),(np.eye(4),0),(np.eye(4),float('nan')),(np.eye(3),1)):
            with self.subTest(matrix=matrix,units=units),self.assertRaises(ValueError):preview_transform(matrix,units)
        matrix=np.eye(4);matrix[3,0]=1
        with self.assertRaises(ValueError):preview_transform(matrix)
        with self.assertRaisesRegex(ValueError,'zero length'):transform_pose([[0,0,0]],[[0,0,0]],np.eye(4)[None],np.eye(4))


if __name__=='__main__':unittest.main()
