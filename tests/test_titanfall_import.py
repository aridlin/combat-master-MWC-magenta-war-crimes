import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from model_import.titanfall2 import pack_source,import_models
from operators.assets import load


def data():
    return dict(positions=np.array([[0,0,0],[1,0,0],[0,1,0],[2,0,0],[3,0,0],[2,1,0]],dtype='<f4'),
                normals=np.array([[0,0,1]]*6,dtype='<f4'),uv=np.array([[0,0],[1,0],[0,1]]*2,dtype='<f4'),
                faces=np.array([[0,1,2],[3,4,5]],dtype='<u4'),face_materials=np.array([0,1],dtype='<i4'),
                bone_indices=np.zeros((6,3),dtype='u1'),bone_weights=np.array([[1,0,0]]*6,dtype='<f4'),
                inverse_bind=np.eye(4,dtype='<f4')[None],bone_parents=np.array([-1],dtype='<i4'),
                bone_names=['def_c_hip'],textures=['body','gear'],parts=[])


class CompactPilotImport(unittest.TestCase):
    def test_packing_preserves_all_authored_geometry_and_skin(self):
        with tempfile.TemporaryDirectory() as root:
            d=data();out=Path(root)/'packed'
            pack_source(d,{0:Image.new('RGB',(64,32),'red'),1:Image.new('RGB',(32,64),'green')},out,{'source':'Synthetic test fixture','id':'test'})
            mesh,image,bi,bw,meta=load(out)
            np.testing.assert_array_equal(mesh.vertices,d['positions']);np.testing.assert_array_equal(mesh.faces,d['faces'])
            np.testing.assert_array_equal(bi,d['bone_indices']);np.testing.assert_array_equal(bw,d['bone_weights'])
            self.assertEqual(meta['native_material_tile_pixels'],512);self.assertEqual(meta['vertices'],6);self.assertTrue(meta['prepacked'])
            self.assertEqual({p.name for p in out.iterdir()},{'source.json','source.npz','albedo.png'})
            self.assertEqual([p.name for p in Path(root).iterdir()],['packed'])
            self.assertFalse(meta['game_files_modified']);self.assertFalse(meta['in_game_tested'])

    def test_shared_material_vertices_and_missing_image_fail_explicitly(self):
        with tempfile.TemporaryDirectory() as root:
            d=data();images={0:Image.new('RGB',(1,1)),1:Image.new('RGB',(1,1))}
            with self.assertRaisesRegex(ValueError,'images'):pack_source(d,{0:images[0]},Path(root)/'bad',{'source':'test'})
            d['faces'][1,0]=0
            with self.assertRaisesRegex(ValueError,'boundary'):pack_source(d,images,Path(root)/'bad',{'source':'test'})

    def test_output_cannot_be_inside_game_or_overwrite_existing_sources(self):
        with tempfile.TemporaryDirectory() as root:
            game=Path(root)/'game';game.mkdir()
            with self.assertRaisesRegex(ValueError,'outside'):import_models(game,'unused',game/'output')
            with self.assertRaisesRegex(ValueError,'Unknown'):import_models(game,'unused',Path(root)/'out',names=['wrong'])
            out=Path(root)/'exists';out.mkdir()
            with self.assertRaisesRegex(ValueError,'fresh'):import_models(game,'unused',out)


if __name__=='__main__':unittest.main()
