import copy
import unittest
import numpy as np
from operators.leaf_tips import cap
from operators.retarget import adapt


class LeafTips(unittest.TestCase):
    def test_cap_keeps_native_off_axis_direction_and_excludes_other_bones(self):
        # The last segment bends sideways; projecting it onto the previous
        # joint axis would miss the native surface by a full centimetre.
        vertices=np.array([[.001,0,0],[.002,0,0],[.003,0,0],
                           [.02,.01,0],[.02,.01,0],[.02,.01,0],
                           [.5,.5,.5]])
        indices=np.zeros((7,4),int);indices[-1,0]=1
        weights=np.zeros((7,4));weights[:,0]=1
        point,support=cap(vertices,indices,weights,0,[0,0,0],[1,0,0])
        np.testing.assert_allclose(point,[.02,.01,0]);self.assertEqual(support,3)

    def fixture(self):
        source=['root','head','finger3','tip4'];target=['Root_M','Head_M','IndexFinger3_L']
        rest=np.repeat(np.eye(4)[None],4,axis=0);rest[:,:3,3]=[[0,0,0],[0,0,1],[0,0,.5],[.02,0,.5]]
        native=rest[:3].copy();native[2,:3,3]=[0,.1,.5]
        positions=np.array([[.02,0,.5],[.02,0,.5],[0,0,.2]])
        indices=np.zeros((3,4),int);indices[:,0]=[2,3,0]
        weights=np.zeros((3,4));weights[:,0]=1
        args=(positions,np.tile([0.,0,1.],(3,1)),source,np.linalg.inv(rest),indices,weights,target,np.linalg.inv(native))
        options=dict(source_targets={0:'Root_M',1:'Head_M',2:'IndexFinger3_L',3:'IndexFinger3_L'},primary_sources={'Root_M':0,'Head_M':1,'IndexFinger3_L':2},source_root=0,source_head=1,source_basis=np.eye(3))
        leaf={2:dict(source=[.02,0,.5],target=[-.01,.11,.5],tip_index=3)}
        return args,options,leaf

    def test_leaf_endpoint_and_tip_alias_fit_without_changing_skin_or_torso(self):
        args,options,leaf=self.fixture();before=copy.deepcopy(args)
        old=adapt(*args,**options)
        result=adapt(*args,**options,leaf_tips=leaf)
        np.testing.assert_allclose(result[0][:2],[[-.01,.11,.5]]*2,atol=1e-6)
        np.testing.assert_array_equal(result[0][2],old[0][2])
        for k in (2,3):np.testing.assert_array_equal(result[k],old[k])
        np.testing.assert_allclose(np.linalg.norm(result[1],axis=1),1)
        for k in (0,1,3,4,5,7):np.testing.assert_array_equal(args[k],before[k])

    def test_disabled_leaf_fit_is_byte_identical(self):
        args,options,_=self.fixture()
        for a,b in zip(adapt(*args,**options)[:4],adapt(*args,**options,leaf_tips={})[:4]):
            self.assertEqual(a.tobytes(),b.tobytes())

    def test_degenerate_or_excessive_leaf_fit_fails_instead_of_clamping(self):
        args,options,leaf=self.fixture()
        for source in ([0,0,.5],[2,0,.5]):
            bad=copy.deepcopy(leaf);bad[2]['source']=source
            with self.assertRaisesRegex(ValueError,'Degenerate fingertip|scale guard'):
                adapt(*args,**options,leaf_tips=bad)

    def test_cap_rejects_missing_support_and_nonfinite_geometry(self):
        points=np.zeros((3,3));indices=np.zeros((3,4),int);weights=np.zeros((3,4));weights[:,0]=1
        with self.assertRaisesRegex(ValueError,'Degenerate distal cap'):cap(points,indices,weights,0,[0,0,0])
        with self.assertRaisesRegex(ValueError,'Insufficient'):cap(points,indices,weights,1,[0,0,0])
        points[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'Invalid fingertip geometry'):cap(points,indices,weights,0,[0,0,0])


if __name__=='__main__':unittest.main()
