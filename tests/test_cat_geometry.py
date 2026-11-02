import json
import struct
import tempfile
import unittest
from pathlib import Path
import numpy as np
from catgun.geometry import make_cat,export


class OriginalCatGeometry(unittest.TestCase):
    def test_valid_normals_indices_and_winding(self):
        v,n,uv,f=make_cat().arrays()
        self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(n).all())
        self.assertLess(int(f.max()),len(v));self.assertGreater(len(f),1000)
        np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=1e-6)
        self.assertTrue(((uv>=0)&(uv<=1)).all())
        cross=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        self.assertTrue((np.linalg.norm(cross,axis=1)>1e-12).all())
        self.assertTrue((np.einsum('ij,ij->i',cross,n[f].mean(axis=1))>0).all())

    def test_deterministic_and_scaled(self):
        a=make_cat().arrays();b=make_cat().arrays()
        for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
        np.testing.assert_allclose(make_cat(2).arrays()[0],a[0]*2)

    def test_glb_and_obj_are_standalone_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            export(make_cat(),tmp);path=Path(tmp)
            raw=(path/'cat.glb').read_bytes();magic,version,length=struct.unpack_from('<III',raw)
            self.assertEqual((magic,version,length),(0x46546c67,2,len(raw)))
            size,kind=struct.unpack_from('<I4s',raw,12)
            self.assertEqual(kind,b'JSON');doc=json.loads(raw[20:20+size])
            self.assertEqual(doc['accessors'][0]['count'],3690)
            self.assertTrue((path/'cat.obj').read_text().startswith('# Original MWC cat'))
            self.assertTrue((path/'cat-palette.png').is_file())


if __name__=='__main__':unittest.main()
