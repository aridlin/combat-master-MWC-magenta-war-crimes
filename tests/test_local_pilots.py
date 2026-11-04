import hashlib,json,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from model_import.titanfall2 import MODELS,pack_source
from operators.local_pilots import verify,register,sources
from operators.library import prepare

MODEL='titanfall_grapple'


def package(root):
    names=['def_c_hip','def_c_spineA','def_c_spineB','def_c_spineC','def_c_neckA','def_c_head']
    names += [f'def_{side}_{bone}' for side in ('l','r') for bone in ('clav','shoulder','elbow','wrist','thigh','knee','ankle','ball')]
    data=dict(positions=np.array([[0,0,0],[1,0,0],[0,1,0]],dtype='<f4'),normals=np.array([[0,0,1]]*3,dtype='<f4'),uv=np.array([[0,0],[1,0],[0,1]],dtype='<f4'),faces=np.array([[0,1,2]],dtype='<u4'),face_materials=np.zeros(1,dtype='<i4'),bone_names=names,bone_parents=np.array([-1]+[0]*(len(names)-1),dtype='<i4'),inverse_bind=np.repeat(np.eye(4,dtype='<f4')[None],len(names),axis=0),bone_indices=np.zeros((3,3),dtype='u1'),bone_weights=np.array([[1,0,0]]*3,dtype='<f4'),textures=['body'],parts=[])
    out=Path(root)/MODEL;pack_source(data,{0:Image.new('RGB',(16,16),'green')},out,{'id':MODEL,'source_model':MODELS[MODEL][0],'source':'Synthetic local cache fixture'})
    return out


class LocalPilots(unittest.TestCase):
    def test_verified_registration_reuse_and_independent_magenta(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);source=package(root/'prepared');state=root/'state'
            self.assertEqual(len(verify(source,MODEL)),3)  # Authored VVD's three influence slots are valid.
            row=register(state,source.parent);self.assertFalse(row[0]['reused'])
            before={p.name:p.read_bytes() for p in source.iterdir()}
            self.assertTrue(register(state,source.parent)[0]['reused'])
            config={'titanfall2_source_root':str(state/'operator-imports')}
            self.assertEqual(sources(config,{MODEL})[MODEL]['profile'],'titanfall2_native')
            self.assertEqual(prepare(config,{'operator_0':MODEL},root/'work')[MODEL]['style'],'magenta')
            self.assertEqual(prepare(config,{'operator_0':MODEL},root/'work',appearance={'model_magenta':{MODEL:False}})[MODEL]['style'],'original')
            self.assertEqual(before,{p.name:p.read_bytes() for p in source.iterdir()})
            self.assertFalse((state/'state.json').exists())

    def test_source_revisions_are_backed_up_and_corruption_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);source=package(root/'prepared');state=root/'state';register(state,source.parent)
            old=(state/'operator-imports'/MODEL/'source.json').read_bytes();metadata=json.loads((source/'source.json').read_text());metadata['title']='A revised local package';(source/'source.json').write_text(json.dumps(metadata))
            row=register(state,source.parent)[0];backup=Path(row['previous_source_backup']);self.assertEqual((backup/'source.json').read_bytes(),old)
            cached=state/'operator-imports'/MODEL;unchanged=(cached/'albedo.png').read_bytes();(source/'albedo.png').write_bytes(b'damaged')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):register(state,source.parent)
            self.assertEqual((cached/'albedo.png').read_bytes(),unchanged)

    def test_missing_or_wrong_model_is_not_silently_substituted(self):
        with self.assertRaisesRegex(ValueError,'Import native'):sources({}, {MODEL})
        with tempfile.TemporaryDirectory() as root:
            source=package(Path(root)/'prepared');meta=json.loads((source/'source.json').read_text());meta['id']='fishguy';(source/'source.json').write_text(json.dumps(meta))
            with self.assertRaisesRegex(ValueError,'identity/profile'):verify(source,MODEL)
            (source/'unknown.py').write_text('raise RuntimeError("must not execute")')
            with self.assertRaisesRegex(ValueError,'exactly'):verify(source,MODEL)


if __name__=='__main__':unittest.main()
