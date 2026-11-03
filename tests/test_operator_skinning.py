import unittest
import numpy as np
from operators.skinning import validate_weights,cpu_skin

class Skinning(unittest.TestCase):
    def test_inverse_bind_poses_recover_source_vertices(self):
        p=np.array([[0,0,0],[1,2,3],[-2,.25,1.]])
        pose=np.repeat(np.eye(4)[None],2,axis=0);pose[1,:3,3]=[3,1,-2];bind=np.linalg.inv(pose)
        i=np.array([[0,1,0,0],[1,0,0,0],[0,1,0,0]]);w=np.array([[.25,.75,0,0],[1,0,0,0],[.5,.5,0,0]])
        np.testing.assert_allclose(cpu_skin(p,i,w,pose,bind),p,atol=1e-6)
    def test_head_only_accessory_follows_head_bone(self):
        p=np.array([[.1,1.8,.1],[-.1,1.8,.1]])
        pose=np.repeat(np.eye(4)[None],2,axis=0);pose[1,:3,3]=[0,.4,.2];bind=np.repeat(np.eye(4)[None],2,axis=0);i=np.array([[1,0,0,0]]*2);w=np.array([[1,0,0,0]]*2)
        np.testing.assert_allclose(cpu_skin(p,i,w,pose,bind),p+[0,.4,.2],atol=1e-6)
    def test_bad_weights_fail_before_serialization(self):
        for i,w in [([[2,0,0,0]],[[1,0,0,0]]),([[0,0,0,0]],[[0,0,0,0]]),([[0,0,0,0]],[[1,-.1,.1,0]]),([[.5,0,0,0]],[[1,0,0,0]])]:
            with self.subTest(i=i,w=w),self.assertRaises(ValueError):validate_weights(i,w,1,2)

if __name__=='__main__':unittest.main()
