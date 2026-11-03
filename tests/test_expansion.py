import json,tempfile,unittest
from pathlib import Path
import numpy as np
from weapon_models.imported import load
from weapon_models.bundles import model_asset
from skybox.pixels import colors,face_directions,faces

class AuthoredAssets(unittest.TestCase):
    def test_imported_assets_keep_attribution_and_valid_mesh_attributes(self):
        for name in ('scorpion','fishing_rod','toaster'):
            with self.subTest(name=name):
                mesh,texture,meta=load(name);v,n,uv,f=mesh.arrays()
                self.assertFalse(meta['geometry_created']);self.assertTrue(meta['author']);self.assertTrue(meta['source_url'].startswith('https://'))
                self.assertEqual(len(f),meta['triangles']);self.assertTrue(np.isfinite(v).all());self.assertTrue(np.isfinite(n).all());self.assertLess(f.max(),len(v));self.assertLess(len(v),65536)
                self.assertTrue(((uv>=0)&(uv<=1)).all());np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=2e-6)
                self.assertGreater(texture.width,256)
    def test_missing_authored_asset_never_silently_builds_a_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):load('scorpion',root=d)
    def test_explicit_legacy_and_authored_assets_remain_distinct(self):
        old=model_asset({'models':{'scorpion':{'asset':'legacy_procedural'}}},'scorpion')[0]
        new=model_asset({'models':{'scorpion':{'asset':'authored'}}},'scorpion')[0]
        self.assertNotEqual(len(old.faces),len(new.faces))
    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):model_asset({'models':{'scorpion':{'asset':'whatever'}}},'scorpion')

class Sky(unittest.TestCase):
    def test_shared_cube_edges_are_sampled_identically(self):
        v=np.linspace(-1,1,101);edge=np.ones_like(v)
        a=face_directions(0,-edge,v);b=face_directions(4,edge,v)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(colors(a),colors(b))
        a=face_directions(0,edge,v);b=face_directions(5,-edge,v)
        np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(colors(a),colors(b))
    def test_day_sun_and_night_moon_are_explicit_modes(self):
        sun=np.array([.45,.72,.35]);sun/=np.linalg.norm(sun)
        np.testing.assert_array_equal(colors(sun),[255,255,225]);np.testing.assert_array_equal(colors(sun,night=True),[213,221,229])
        self.assertFalse(np.array_equal(colors(sun,night=True),colors(sun)))
    def test_faces_have_exact_rgba_dimensions(self):
        result=faces(64);self.assertEqual(len(result),6)
        for f in result:self.assertEqual(f.size,(64,64));self.assertEqual(f.mode,'RGBA');self.assertTrue((np.asarray(f)[:,:,3]==255).all())

if __name__=='__main__':unittest.main()
