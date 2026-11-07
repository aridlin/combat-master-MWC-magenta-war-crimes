import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from bundle_utils import digest
from operators.pose_input import read_world_pose,main_world_renderer
from operators.pose_space import transform_pose
from operators.skinning import cpu_skin


class PrivateWorldPoseInput(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
        self.bind=np.tile(np.eye(4),(2,1,1)).astype('<f4');self.bind[1,1,3]=-1
        self.pose=np.tile(np.eye(4),(2,1,1));self.pose[0,1,3]=1
        self.pose[1,:3,:3]=[[0,-1,0],[1,0,0],[0,0,1]];self.pose[1,1,3]=2
        self.arrays={'pose':self.pose.copy(),'bind':self.bind.copy(),'world':np.eye(4)}
        self.report={'rig_kind':'third_person','operator':'operator_30','source_bundle_sha256':'owned-original','source_unchanged':True,'clip_source_unchanged':True,'clip':'Owned two-bone diagnostic','frame':3,'time':.1,'renderers':[{'renderer':'7','bones':2,'bone_names':['root','hand'],'pose_space':'renderer_local','world_space':'Unity Y-up','pose_array':'pose','inverse_bind_array':'bind','renderer_to_world_array':'world'}]}
        self.save()

    def save(self):
        np.savez_compressed(self.path/'pose.npz',**self.arrays)
        self.report['pose_data_sha256']=digest(self.path/'pose.npz')
        (self.path/'review.json').write_text(json.dumps(self.report))

    def read(self,**kw):
        args=dict(directory=self.path,source_hash='owned-original',operator='operator_30',renderer=7,bone_names=['root','hand'],inverse_bind=self.bind)
        args.update(kw);return read_world_pose(**args)

    def test_exact_rig_skinning_and_world_axes_match_independent_example(self):
        pose,world,info=self.read()
        points=cpu_skin([[1,1,0]],[[0,1,0,0]],[[.5,.5,0,0]],pose,self.bind)
        np.testing.assert_allclose(points,[[.5,2.5,0]])
        vertices,normals,bind=transform_pose(points,[[0,0,1]],np.linalg.inv(pose),world)
        np.testing.assert_allclose(vertices,[[.5,0,2.5]])
        np.testing.assert_allclose(normals,[[0,-1,0]])
        np.testing.assert_allclose(np.linalg.inv(bind)[1,:3,3],[0,0,2])
        self.assertEqual(info['clip'],'Owned two-bone diagnostic')
        np.testing.assert_array_equal(pose,self.pose)

    def test_another_operator_source_or_bone_order_is_rejected(self):
        for args in ({'operator':'operator_0'},{'source_hash':'other-original'},{'bone_names':['hand','root']},{'renderer':8},{'inverse_bind':np.tile(np.eye(4),(2,1,1))}):
            with self.subTest(args=args),self.assertRaises(ValueError):self.read(**args)

    def test_data_corruption_and_old_unhashed_exports_are_rejected(self):
        with (self.path/'pose.npz').open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):self.read()
        self.save();self.report.pop('pose_data_sha256');(self.path/'review.json').write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,'hash'):self.read()

    def test_absent_world_space_ambiguous_renderer_and_unverified_source_fail(self):
        initial=copy.deepcopy(self.report)
        for change in ('rig','source','clip_source','space','duplicate'):
            self.report=copy.deepcopy(initial)
            if change=='rig':self.report['rig_kind']='first_person'
            elif change=='source':self.report['source_unchanged']=False
            elif change=='clip_source':self.report['clip_source_unchanged']=False
            elif change=='space':self.report['renderers'][0].pop('renderer_to_world_array')
            else:self.report['renderers']*=2
            self.save()
            with self.subTest(change=change),self.assertRaises(ValueError):self.read()

    def test_singular_nonfinite_or_nonaffine_pose_and_frame_fail(self):
        original={k:v.copy() for k,v in self.arrays.items()}
        for change in ('singular','nan','projective','world'):
            self.arrays={k:v.copy() for k,v in original.items()}
            if change=='singular':self.arrays['pose'][0,0]=0
            elif change=='nan':self.arrays['pose'][0,0,0]=np.nan
            elif change=='projective':self.arrays['pose'][0,3,0]=1
            else:self.arrays['world'][0]=0
            self.save()
            with self.subTest(change=change),self.assertRaises(ValueError):self.read()

    def test_main_renderer_is_lod_zero_even_when_path_order_differs(self):
        record={'operator':'owned','renderers':[{'renderer':'-5'},{'renderer':'2'},{'renderer':'7'}]}
        targets=[{'id':'owned','renderers':[{'path_id':-5,'name':'body_LOD2'},{'path_id':2,'name':'body_LOD1'},{'path_id':7,'name':'body_LOD0'}]}]
        self.assertEqual(main_world_renderer(record,targets),7)

    def test_absent_or_ambiguous_main_renderer_never_falls_back_to_first(self):
        record={'operator':'owned','renderers':[{'renderer':'-5'},{'renderer':'7'}]}
        for targets in ([],[{'id':'owned','renderers':[{'path_id':-5,'name':'body_LOD1'}]}],[{'id':'owned','renderers':[{'path_id':-5,'name':'body_LOD0'},{'path_id':7,'name':'other_LOD0'}]}]):
            with self.subTest(targets=targets),self.assertRaises(ValueError):main_world_renderer(record,targets)


if __name__=='__main__':unittest.main()
