import io,json,struct,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from weapon_models.geometry import BUILDERS,make_model,palette
from catgun.geometry import export


class WeaponModels(unittest.TestCase):
    def test_all_meshes_have_valid_visible_triangles_and_unit_normals(self):
        for name in BUILDERS:
            with self.subTest(model=name):
                v,n,uv,f=make_model(name).arrays()
                self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(n).all())
                self.assertLess(int(f.max()),len(v));self.assertTrue(((uv>=0)&(uv<=1)).all())
                np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=1e-6)
                cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
                self.assertTrue((np.einsum('ij,ij->i',cross,n[f].mean(axis=1))>0).all())

    def test_exported_glbs_embed_the_correct_model_palette_and_valid_buffers(self):
        for name in BUILDERS:
            with self.subTest(model=name),tempfile.TemporaryDirectory() as tmp:
                mesh=make_model(name);export(mesh,tmp,texture=palette(name),prefix=name)
                raw=Path(tmp,name+'.glb').read_bytes();magic,version,length=struct.unpack_from('<III',raw)
                self.assertEqual((magic,version,length),(0x46546c67,2,len(raw)))
                size,kind=struct.unpack_from('<I4s',raw,12);self.assertEqual(kind,b'JSON')
                doc=json.loads(raw[20:20+size]);start=20+size;bin_size,bin_kind=struct.unpack_from('<I4s',raw,start)
                self.assertEqual(bin_kind,b'BIN\0');binary=raw[start+8:start+8+bin_size]
                for view in doc['bufferViews']:self.assertLessEqual(view.get('byteOffset',0)+view['byteLength'],len(binary))
                self.assertEqual(doc['accessors'][0]['count'],len(mesh.vertices))
                view=doc['bufferViews'][doc['images'][0]['bufferView']];offset=view.get('byteOffset',0)
                img=Image.open(io.BytesIO(binary[offset:offset+view['byteLength']])).convert('RGB')
                np.testing.assert_array_equal(np.array(img),np.array(palette(name)))
                self.assertTrue(Path(tmp,name+'.obj').is_file())


if __name__=='__main__':unittest.main()
