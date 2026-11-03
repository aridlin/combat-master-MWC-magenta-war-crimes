import unittest
import numpy as np
from operators.viewmodel import slim,settings


class ViewmodelVolume(unittest.TestCase):
    def test_radius_shrinks_while_joint_axis_and_reach_stay_fixed(self):
        rest=np.repeat(np.eye(4)[None],4,axis=0);rest[:,:3,3]=[[0,0,0],[0,0,1],[0,0,2],[0,0,2.2]];native={'bone_names':['j_shoulder_L','j_elbow_L','j_hand_L','j_mid_1_L'],'inverse_bind':np.linalg.inv(rest)}
        positions=np.array([[0,0,1.5],[.1,0,1.5],[0,0,2.1],[.1,0,2.1]]);original=positions.copy();normals=np.repeat([[1.,0,0]],4,axis=0);bi=np.zeros((4,4),int);bi[:,0]=[1,1,2,2];bw=np.zeros((4,4));bw[:,0]=1
        v,n,report=slim(positions,normals,bi,bw,native,.55,.6)
        np.testing.assert_allclose(v[[0,2]],positions[[0,2]]);np.testing.assert_allclose(v[:,2],positions[:,2]);np.testing.assert_allclose(v[[1,3],0],[.055,.06]);np.testing.assert_allclose(np.linalg.norm(n,axis=1),1);np.testing.assert_array_equal(positions,original);self.assertFalse(report['third_person_geometry_changed'])

    def test_shrek_has_stronger_first_person_reduction_than_default(self):
        self.assertLess(settings('shrek')['arm_radius_scale'],settings('titanfall_pilot')['arm_radius_scale'])
        self.assertLess(settings('shrek')['hand_radius_scale'],settings('titanfall_pilot')['hand_radius_scale'])


if __name__=='__main__':unittest.main()
