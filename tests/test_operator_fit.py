import unittest
import numpy as np
from operators.retarget import adapt,rotation_between
from operators.glasses import create
from operators.assets import load
from operators.skinning import validate_weights
from pathlib import Path


class Fitting(unittest.TestCase):
    def test_short_pelvis_helper_cannot_stretch_coat_and_accessory_keeps_offset(self):
        names=['hips','tiny_spine_helper','chest','head','head_accessory'];positions=np.array([[.2,0,-.4],[.1,0,.75]]);normals=np.array([[0,1.,0]]*2)
        rest=np.repeat(np.eye(4)[None],5,axis=0);rest[:,2,3]=[0,.0001,.5,1,.75];rest[4,0,3]=.1
        target=rest.copy();target[:,2,3]=[0,.25,.5,1,1.2];target[4,0,3]=0
        tn=['Root_M','Spine1_M','Chest_M','Head_M','HeadEnd_M'];indices=np.array([[0,0,0,0],[4,0,0,0]]);weights=np.array([[1.,0,0,0]]*2)
        v,n,bi,bw,_=adapt(positions,normals,names,np.linalg.inv(rest),indices,weights,tn,np.linalg.inv(target),source_targets={0:'Root_M',1:'Spine1_M',2:'Chest_M',3:'Head_M',4:'Head_M'},primary_sources={'Root_M':0,'Spine1_M':1,'Chest_M':2,'Head_M':3},source_root=0,source_head=3,source_basis=np.eye(3))
        np.testing.assert_allclose(v,positions,atol=1e-6);self.assertEqual(bi[1,0],3);np.testing.assert_allclose(bw.sum(1),1)

    def test_antiparallel_rotation_is_finite_and_proper(self):
        r=rotation_between([0,1.,0],[0,-1.,0]);np.testing.assert_allclose(r@[0,1.,0],[0,-1.,0],atol=1e-8);self.assertAlmostEqual(np.linalg.det(r),1.)

    def test_mesh_frame_and_units_do_not_change_the_fitted_shape(self):
        names=['Root_M','Spine1_M','Spine2_M','Chest_M','Neck_M','Head_M'];rest=np.repeat(np.eye(4)[None],6,axis=0);rest[:,2,3]=[0,.25,.50,.65,.9,1.];bind=np.linalg.inv(rest);p=np.array([[.2,.1,.9],[-.1,0,.2]]);n=np.array([[0,-1.,0]]*2);i=np.array([[5,0,0,0],[0,0,0,0]]);w=np.array([[1.,0,0,0]]*2);options=dict(source_targets={k:v for k,v in enumerate(names)},primary_sources={v:k for k,v in enumerate(names)},source_root=0,source_head=5,source_basis=np.eye(3))
        v,nn,_,_,_=adapt(p,n,names,bind,i,w,names,bind,**options)
        frame=np.array([[1.,0,0],[0,0,1],[0,-1,0]]);transform=np.eye(4);transform[:3,:3]=100*frame;other=np.linalg.inv(transform@rest)
        vv,nnn,_,_,_=adapt(p,n,names,bind,i,w,names,other,**options)
        np.testing.assert_allclose(vv@frame/100,v,atol=1e-6);np.testing.assert_allclose(nnn@frame,nn,atol=1e-6)

    def test_glasses_are_separate_finite_meshes_with_a_curved_wrap(self):
        frame,shield,meta=create([0,0,1.63])
        for mesh in (frame,shield):
            v,n,uv,f=mesh.arrays();self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(n).all());self.assertLess(f.max(),len(v));self.assertLess(len(v),65536)
        v=np.asarray(shield.vertices);self.assertGreater(np.ptp(v[:,1]),.03);self.assertTrue(meta['head_attachment']);self.assertFalse(meta['in_game_tested'])

    def test_packaged_operator_sources_are_hash_verified_and_weighted(self):
        root=Path(__file__).resolve().parents[1]/'assets/operator-sources'
        for name in ('shrek','fishguy','mario','minecraft_steve'):
            mesh,texture,indices,weights,meta=load(root/name);validate_weights(indices,weights,len(mesh.vertices),len(meta['bone_names']));self.assertGreater(texture.width,256);self.assertFalse(meta['in_game_tested'])


if __name__=='__main__':unittest.main()
