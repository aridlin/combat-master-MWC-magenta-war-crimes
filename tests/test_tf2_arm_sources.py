import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from operators.tf2_arms import add_landmarks
from model_import.tf2 import import_models


class AuthoredTF2Arms(unittest.TestCase):
    def fixture(self,root):
        source,world=Path(root)/'arms',Path(root)/'world'
        source.mkdir();world.mkdir()
        names=['bip_'+joint+'_'+side for side in ('L','R') for joint in ('upperArm','lowerArm','hand')]
        bind=np.repeat(np.eye(4,dtype='<f4')[None],6,axis=0)
        bind[:,:3,3]=np.arange(18).reshape(6,3)
        arrays=dict(positions=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype='<f4'),
            normals=np.array([[0,0,1]]*3,dtype='<f4'),uv=np.zeros((3,2),dtype='<f4'),
            faces=np.array([[0,1,2]],dtype='<u4'),face_materials=np.array([0],dtype='<i4'),
            bone_indices=np.array([[0,0,0],[1,0,0],[2,0,0]],dtype='u1'),
            bone_weights=np.array([[1,0,0]]*3,dtype='<f4'),
            inverse_bind=bind,bone_parents=np.full(6,-1,dtype='<i4'))
        np.savez_compressed(source/'source.npz',**arrays)
        (source/'source.json').write_text(json.dumps(dict(id='tf2_medic',source_variant='first_person_arms',bone_names=names,bone_parents=[-1]*6)))
        reference=np.concatenate([bind,np.eye(4,dtype='<f4')[None].repeat(2,axis=0)])
        reference[-1,1,3]=-10
        np.savez_compressed(world/'source.npz',inverse_bind=reference)
        (world/'source.json').write_text(json.dumps(dict(id='tf2_medic',bone_names=names+['bip_pelvis','bip_head'])))
        return source,world,arrays

    def test_only_two_unweighted_landmarks_are_added(self):
        with tempfile.TemporaryDirectory() as root:
            source,world,before=self.fixture(root);add_landmarks(source,world)
            with np.load(source/'source.npz',allow_pickle=False) as after:
                for name,value in before.items():
                    np.testing.assert_array_equal(after[name][:6] if name in ('inverse_bind','bone_parents') else after[name],value)
                self.assertEqual(len(after['inverse_bind']),8)
                self.assertLess(int(after['bone_indices'].max()),6)
                np.testing.assert_array_equal(after['bone_parents'][-2:],[-1,-1])
            meta=json.loads((source/'source.json').read_text())
            self.assertTrue(meta['fit_landmarks']['authored_geometry_and_skin_preserved'])
            with self.assertRaisesRegex(ValueError,'already-added'):add_landmarks(source,world)

    def test_different_class_rejected_before_any_source_write(self):
        with tempfile.TemporaryDirectory() as root:
            source,world,_=self.fixture(root);p=world/'source.json';meta=json.loads(p.read_text());meta['id']='tf2_scout';p.write_text(json.dumps(meta));before=(source/'source.npz').read_bytes()
            with self.assertRaisesRegex(ValueError,'same class'):add_landmarks(source,world)
            self.assertEqual((source/'source.npz').read_bytes(),before)

    def test_unreviewed_coordinate_frame_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            source,world,_=self.fixture(root)
            with np.load(world/'source.npz') as data:bind=data['inverse_bind'].copy()
            bind[0,0,3]+=1
            np.savez_compressed(world/'source.npz',inverse_bind=bind)
            with self.assertRaisesRegex(ValueError,'coordinate mismatch'):add_landmarks(source,world)

    def test_arm_import_rejects_weapon_before_reading_vpk(self):
        with tempfile.TemporaryDirectory() as root,patch('model_import.tf2.VPK') as vpk:
            with self.assertRaisesRegex(ValueError,'Unknown'):import_models(Path(root)/'tf',Path(root)/'out',['medigun'],first_person=True)
            vpk.assert_not_called()
