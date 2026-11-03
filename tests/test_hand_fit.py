import unittest
import numpy as np
from operators.hand_fit import frame,fits
from operators.retarget import adapt,rotation_between


class AnatomicalHandFit(unittest.TestCase):
    def test_palm_uses_independent_length_and_roll_without_mirroring(self):
        # A long authored hand rolls 90 degrees to fit a smaller native palm.
        points=np.array([[0.,0,0],[0,0,2],[1,0,1],[-1,0,1]])
        roll=np.array([[0.,0,1],[0,1,0],[-1,0,0]])
        r=roll@rotation_between([0,0,1],[0,1,0]);q=points@r.T*.2+np.array([3.,4,5])
        sp=np.r_[points,points+np.array([5.,0,0])];tp=np.r_[q,q+np.array([2.,0,0])]
        names={n+'_'+side:4*k+j for k,side in enumerate(('L','R')) for j,n in enumerate(('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1'))}
        for side,h in fits(sp,tp,names,names).items():
            self.assertAlmostEqual(h['scale'],.2);self.assertAlmostEqual(np.linalg.det(h['rotation']),1.)
            ids=[names[n+'_'+side] for n in ('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1')]
            center=ids[0];actual=(sp[ids]-sp[center])@h['rotation'].T*h['scale']+tp[center]
            np.testing.assert_allclose(actual,tp[ids],atol=1e-7)
    def test_missing_or_degenerate_landmarks_fail_before_geometry_is_built(self):
        with self.assertRaisesRegex(ValueError,'landmarks'):fits(np.zeros((1,3)),np.zeros((1,3)),{}, {})
        with self.assertRaisesRegex(ValueError,'forward'):frame(*np.zeros((4,3)))
        with self.assertRaisesRegex(ValueError,'lateral'):frame([0,0,0],[0,0,1],[0,0,2],[0,0,3])
    def test_rotation_helper_does_not_change_landmark_arrays(self):
        a=np.array([0.,0,4]);b=np.array([0.,3,0]);before=(a.copy(),b.copy());rotation_between(a,b)
        np.testing.assert_array_equal(a,before[0]);np.testing.assert_array_equal(b,before[1])
    def test_adaptation_fits_native_palm_without_using_torso_scale_for_hand_volume(self):
        names=['Root_M','Head_M'];source=[[0.,0,0],[0,0,2]];native=[[0.,0,0],[0,0,4]]
        for side,sign in (('L',1),('R',-1)):
            names += [n+'_'+side for n in ('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1')]
            source += [[sign,0,1],[sign,0,1.5],[sign+.3,0,1.4],[sign-.3,0,1.4]]
            native += [[sign*1.6,0,2],[sign*1.6,0,2.2],[sign*1.6+.12,0,2.16],[sign*1.6-.12,0,2.16]]
        rest=np.repeat(np.eye(4)[None],len(names),axis=0);target=rest.copy();rest[:,:3,3]=source;target[:,:3,3]=native
        vertices=np.array([source[3],source[7],[0,0,.5]],float);indices=np.zeros((3,4),int);indices[:,0]=[2,6,0];weights=np.zeros((3,4));weights[:,0]=1
        before=target.copy()
        v,n,_,_,report=adapt(vertices,np.tile([0.,-1.,0.],(3,1)),names,np.linalg.inv(rest),indices,weights,names,np.linalg.inv(target),source_targets=dict(enumerate(names)),primary_sources={n:i for i,n in enumerate(names)},source_root=0,source_head=1,source_basis=np.eye(3),fit_hands=True)
        np.testing.assert_allclose(v[:2],np.array(native)[[3,7]],atol=1e-6)
        np.testing.assert_allclose(v[2],[0,0,1],atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(n,axis=1),1)
        np.testing.assert_array_equal(target,before)
        self.assertAlmostEqual(report['scale'],2)
        self.assertAlmostEqual(report['hand_fits']['L']['scale'],.4)


if __name__=='__main__':unittest.main()
