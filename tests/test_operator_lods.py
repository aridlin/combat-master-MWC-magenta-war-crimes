import json,tempfile,unittest
from pathlib import Path
import numpy as np
from operators.assets import load
from operators.lods import select_source,load_lod


def sources(root):
    high=Path(root)/'high';low=Path(root)/'low'
    materials=[{'name':name,'pixels':name+'.npy','base_color_linear':[1,1,1,1],'alpha_mode':'opaque'} for name in ('body','head')]
    for folder,chosen in [(high,[0,1]),(low,[1])]:
        folder.mkdir();count=3*len(chosen);vertices=np.tile([[0,0,0],[1,0,0],[0,1,0]],(len(chosen),1)).astype('<f4')
        np.savez_compressed(folder/'source.npz',positions=vertices,normals=np.tile([0,0,1],(count,1)).astype('<f4'),uv=np.tile([[0,0],[1,0],[0,1]],(len(chosen),1)).astype('<f4'),faces=np.arange(count,dtype='<u4').reshape(-1,3),face_materials=np.arange(len(chosen),dtype='<i4'),bone_indices=np.zeros((count,3),dtype='u1'),bone_weights=np.tile([1,0,0],(count,1)).astype('<f4'),inverse_bind=np.eye(4,dtype='<f4')[None],bone_parents=np.array([-1],dtype='<i4'))
        for index in chosen:np.save(folder/materials[index]['pixels'],np.tile([1.,0,0,1] if index else [0.,0,1,1],(2,2,1)).astype('<f4'))
        meta={'id':'tf2_owned','source_variant':'world','bone_names':['root'],'materials':[materials[index] for index in chosen]}
        if folder==low:meta['source_lod']=1
        (folder/'source.json').write_text(json.dumps(meta))
    return high,low


class OperatorLODs(unittest.TestCase):
    def test_shared_atlas_preserves_missing_material_slots_and_authored_uvs(self):
        with tempfile.TemporaryDirectory() as root:
            high,low=sources(root);_,palette,*_=load(high);mesh,image,indices,weights,meta=load_lod(low,high)
            self.assertEqual(image.size,(1040,520));self.assertEqual(image.tobytes(),palette.tobytes())
            np.testing.assert_allclose(mesh.uv,[[524/1040,4/520],[1036/1040,4/520],[524/1040,516/520]],atol=1e-7,rtol=0)
            self.assertEqual(image.getpixel((780,260)),(255,0,0,255));self.assertEqual(image.getpixel((260,260)),(0,0,255,255))
            self.assertTrue(meta['shared_lod0_atlas']);self.assertEqual(len(mesh.faces),1)
            np.testing.assert_array_equal(weights,[[1,0,0]]*3);np.testing.assert_array_equal(indices,np.zeros((3,3)))

    def test_wrong_palette_model_or_skeleton_is_rejected(self):
        for change in ('pixels','model','skeleton'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as root:
                high,low=sources(root)
                if change=='pixels':np.save(low/'head.npy',np.ones((2,2,4),dtype='<f4'))
                elif change=='model':
                    p=low/'source.json';meta=json.loads(p.read_text());meta['id']='another';p.write_text(json.dumps(meta))
                else:
                    with np.load(low/'source.npz') as z:data={k:z[k] for k in z.files}
                    data['inverse_bind'][0,0,3]=1;np.savez_compressed(low/'source.npz',**data)
                with self.assertRaises(ValueError):load_lod(low,high)

    def test_broader_authored_uv_range_keeps_its_own_atlas_without_clamping(self):
        with tempfile.TemporaryDirectory() as root:
            high,low=sources(root)
            with np.load(low/'source.npz') as z:data={k:z[k] for k in z.files}
            data['uv'][1,0]=2;np.savez_compressed(low/'source.npz',**data)
            original,own_image,*_=load(low)
            mesh,image,_,_,meta=load_lod(low,high)
            self.assertFalse(meta['shared_lod0_atlas']);self.assertEqual(meta['independent_lod_atlas_reason'],'authored_uv_extent')
            self.assertEqual(image.tobytes(),own_image.tobytes());np.testing.assert_array_equal(mesh.uv,original.uv)

    def test_native_level_shared_renderer_and_far_level_selection(self):
        spec={'source':'high','lod_sources':{'1':'middle','2':'low'}}
        self.assertEqual(select_source(spec,[0]),(Path('high'),0,None))
        self.assertEqual(select_source(spec,[1]),(Path('middle'),1,Path('high')))
        self.assertEqual(select_source(spec,[2,3]),(Path('low'),2,Path('high')))
        self.assertEqual(select_source(spec,[0,1]),(Path('high'),0,None))
        self.assertEqual(select_source(spec,[4]),(Path('low'),2,Path('high')))

    def test_missing_normals_are_reconstructed_without_changing_valid_authored_data(self):
        with tempfile.TemporaryDirectory() as root:
            high,low=sources(root)
            with np.load(low/'source.npz') as z:data={k:z[k] for k in z.files}
            data['normals'][0]=0;data['normals'][1]=[.1,0,.9]
            np.savez_compressed(low/'source.npz',**data)
            mesh,_,indices,weights,meta=load_lod(low,high)
            self.assertEqual(meta['missing_authored_normals_reconstructed'],1)
            np.testing.assert_array_equal(mesh.normals[0],[0,0,1])
            np.testing.assert_array_equal(mesh.normals[1:],data['normals'][1:])
            np.testing.assert_array_equal(mesh.vertices,data['positions'])
            np.testing.assert_array_equal(mesh.faces,data['faces'])
            np.testing.assert_array_equal(indices,data['bone_indices'])
            np.testing.assert_array_equal(weights,data['bone_weights'])

    def test_missing_normal_on_degenerate_geometry_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            high,low=sources(root)
            with np.load(low/'source.npz') as z:data={k:z[k] for k in z.files}
            data['normals'][0]=0;data['positions'][:]=0
            np.savez_compressed(low/'source.npz',**data)
            with self.assertRaisesRegex(ValueError,'no usable incident face'):load_lod(low,high)

    def test_first_person_keeps_its_authored_source_and_ignores_world_lods(self):
        spec={'source':'body','first_person_source':'arms','lod_sources':{'1':'lower-body'}}
        self.assertEqual(select_source(spec,[2],first_person=True),(Path('arms'),0,None))

    def test_invalid_source_maps_fail_without_silent_fallback(self):
        for mapping in ([],{'2':'gap'},{'0':'override-main'},{'01':'alias'},{'8':'unreviewed'}):
            with self.subTest(mapping=mapping),self.assertRaises(ValueError):select_source({'source':'main','lod_sources':mapping},[1])
