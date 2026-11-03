import unittest
import numpy as np
from operators.hand_fit import frame,fits,transition
from operators.retarget import adapt,rotation_between


class AnatomicalHandFit(unittest.TestCase):
    def test_palm_width_controls_volume_independently_of_length(self):
        p=np.array([[0.,0,0],[0,0,2],[1,0,1],[-1,0,1]])
        q=p*np.array([.3,.3,.1])
        names={n+'_'+s:4*k+j for k,s in enumerate(('L','R')) for j,n in enumerate(('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1'))}
        for result in fits(np.r_[p,p+[5,0,0]],np.r_[q,q+[2,0,0]],names,names).values():
            self.assertAlmostEqual(result['scale'],.3)
            self.assertAlmostEqual(result['length_scale'],.1)
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


class WristTransition(unittest.TestCase):
    def geometry(self):
        points=np.array([[x,y,0.] for offset in (0.,3.) for x in (0.,.4,.7,1.,1.3) for y in (offset,offset+.2)])
        faces=np.array([[o+i,o+i+2,o+i+1] for o in (0,10) for i in range(0,8,2)]+[[o+i+1,o+i+2,o+i+3] for o in (0,10) for i in range(0,8,2)])
        rest=np.repeat(np.eye(4)[None],4,axis=0);rest[:,:3,3]=[[0,0,0],[1,0,0],[0,3,0],[1,3,0]]
        indices=np.zeros((20,4),int);indices[:,0]=[0]*6+[1]*4+[2]*6+[3]*4
        weights=np.zeros((20,4));weights[:,0]=1
        trial=points.copy();trial[[6,7,8,9,16,17,18,19],2]=.2
        return points,faces,trial,np.linalg.inv(rest),indices,weights,{0:'Elbow_L',1:'Wrist_L',2:'Elbow_R',3:'Wrist_R'},{'Elbow_L':0,'Wrist_L':1,'Elbow_R':2,'Wrist_R':3}

    def test_taper_preserves_fixed_body_and_fitted_hands(self):
        p,f,t,b,i,w,s,a=self.geometry();original=(i.copy(),w.copy(),f.copy())
        v,n,report=transition(p,f,p,t,np.tile([0.,0,1.],(20,1)),b,i,w,s,a)
        np.testing.assert_array_equal(v[[0,1,10,11]],p[[0,1,10,11]].astype('<f4'))
        np.testing.assert_allclose(v[[6,7,8,9,16,17,18,19]],t[[6,7,8,9,16,17,18,19]])
        self.assertTrue(np.all((v[[2,3,4,5,12,13,14,15],2]>0)&(v[[2,3,4,5,12,13,14,15],2]<.2)))
        np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=1e-6)
        for before,after in zip(original,(i,w,f)):np.testing.assert_array_equal(before,after)
        self.assertTrue(report['outside_hand_and_distal_forearm_unchanged'])

    def test_reflected_output_winding_has_outward_normals(self):
        p,f,t,b,i,w,s,a=self.geometry();baseline=p*np.array([-1,1,1]);trial=t*np.array([-1,1,1]);faces=f[:,[0,2,1]]
        v,n,_=transition(p,faces,baseline,trial,np.tile([0.,0,1.],(20,1)),b,i,w,s,a)
        face_normals=np.cross(v[faces[:,1]]-v[faces[:,0]],v[faces[:,2]]-v[faces[:,0]])
        self.assertTrue(np.all(np.einsum('ij,ij->i',face_normals,n[faces].mean(1))>0))

    def test_missing_landmarks_fail_explicitly(self):
        p,f,t,b,i,w,s,a=self.geometry();del a['Elbow_L']
        with self.assertRaisesRegex(ValueError,'elbow and wrist'):transition(p,f,p,t,np.tile([0.,0,1.],(20,1)),b,i,w,s,a)


if __name__=='__main__':unittest.main()
