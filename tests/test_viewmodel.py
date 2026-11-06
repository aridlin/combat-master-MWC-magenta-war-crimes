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

    def test_leaf_axis_shrinks_only_radius_and_keeps_unit_scale_byte_identical(self):
        rest=np.repeat(np.eye(4)[None],2,axis=0);rest[1,:3,3]=[0,0,.02]
        native={'bone_names':['j_index_2_L','j_index_3_L'],'inverse_bind':np.linalg.inv(rest)}
        endpoint=np.array([.02,.01,.03]);axis=endpoint-rest[1,:3,3];axis/=np.linalg.norm(axis)
        radial=np.cross(axis,[0,0,1.]);radial*=.004/np.linalg.norm(radial)
        v=np.array([endpoint,endpoint+radial]);n=np.tile(radial/np.linalg.norm(radial),(2,1))
        bi=np.zeros((2,4),int);bi[:,0]=1;bw=np.zeros((2,4));bw[:,0]=1
        corrected=slim(v,n,bi,bw,native,.65,.7,leaf_endpoints={'IndexFinger3_L':endpoint})
        np.testing.assert_allclose(corrected[0],[endpoint,endpoint+.7*radial],atol=1e-8)
        default=slim(v,n,bi,bw,native,.6,1.)
        explicit=slim(v,n,bi,bw,native,.6,1.,leaf_endpoints={'IndexFinger3_L':endpoint})
        for a,b in zip(default[:2],explicit[:2]):self.assertEqual(a.tobytes(),b.tobytes())
        for a,b in zip(slim(v,n,bi,bw,native,.6,.7)[:2],slim(v,n,bi,bw,native,.6,.7,leaf_endpoints={})[:2]):
            self.assertEqual(a.tobytes(),b.tobytes())
        for bad in ({'IndexFinger2_L':endpoint},{'IndexFinger3_R':endpoint},{3:endpoint},
                    {'IndexFinger3_L':[1,2]},{'IndexFinger3_L':[1,np.nan,3]},
                    {'IndexFinger3_L':rest[1,:3,3]}):
            with self.assertRaisesRegex(ValueError,'first-person leaf endpoint'):
                slim(v,n,bi,bw,native,.6,.7,leaf_endpoints=bad)

    def test_transition_normal_matches_finite_difference_of_the_deformation(self):
        rest=np.repeat(np.eye(4)[None],2,axis=0);rest[1,:3,3]=[0,0,.02]
        native={'bone_names':['j_index_2_L','j_index_3_L'],'inverse_bind':np.linalg.inv(rest)}
        endpoint=np.array([.02,.01,.03]);point=rest[1,:3,3]+.45*(endpoint-rest[1,:3,3])+[.001,-.002,0]
        normal=np.array([.3,.8,-.1]);normal/=np.linalg.norm(normal)
        def evaluate(p,endpoints):
            p=np.atleast_2d(p);bi=np.zeros((len(p),4),int);bi[:,0]=1
            bw=np.zeros((len(p),4));bw[:,0]=1
            return slim(p,np.tile(normal,(len(p),1)),bi,bw,native,.65,.7,leaf_endpoints=endpoints)
        endpoints={'IndexFinger3_L':endpoint}
        epsilon=1e-5;offsets=np.eye(3)*epsilon
        jacobian=((evaluate(point+offsets,endpoints)[0]-evaluate(point-offsets,endpoints)[0])/(2*epsilon)).T
        expected=np.linalg.solve(jacobian.T,normal);expected/=np.linalg.norm(expected)
        actual=evaluate(point,endpoints)[1][0]
        np.testing.assert_allclose(actual,expected,atol=2e-4)
        # A normal using only an interpolated radius frame misses the blend's
        # spatial derivative; this interior point exercises that derivative.
        self.assertGreater(np.linalg.norm(actual-evaluate(point,{})[1][0]),.02)
        behind=rest[1,:3,3]-.2*(endpoint-rest[1,:3,3])
        for a,b in zip(evaluate(behind,endpoints)[:2],evaluate(behind,{})[:2]):
            self.assertEqual(a.tobytes(),b.tobytes())


if __name__=='__main__':unittest.main()
