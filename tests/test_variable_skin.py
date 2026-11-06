"""Binary weights checked against independent live-Editor reference values."""
import json,unittest
from pathlib import Path
import numpy as np
from operators.variable_skin import encode,decode,fallback,skinned_tree_variable

FIXTURES=Path(__file__).parent/'fixtures/variable-skin'

class VariableSkinTests(unittest.TestCase):
    def setUp(self):
        self.reference=json.loads((FIXTURES/'unity-reference.json').read_text())
        self.words=self.reference['packed_words']

    def test_unity_authored_words_and_api_weights_match_exactly(self):
        indices,weights=decode(self.words,3,8)
        self.assertEqual(encode(indices,weights,8),self.words)
        self.assertEqual(list(np.count_nonzero(weights,axis=1)),[1,4,8])
        np.testing.assert_array_equal(np.concatenate([i[w>0] for i,w in zip(indices,weights)]),self.reference['boneIndices'])
        np.testing.assert_array_equal(np.concatenate([w[w>0] for w in weights]).astype('f4'),np.asarray(self.reference['weights'],'f4'))

    def test_python_authored_distributions_match_actual_editor_readback(self):
        i=np.zeros((3,7),np.uint16);w=np.zeros((3,7),float)
        for v,(bones,values) in enumerate([([7],[1]),([4,2,6,0,5],[5,4,3,2,1]),([1,3,5,7,0,2,6],[7,6,5,4,3,2,1])]):
            i[v,:len(bones)]=bones;w[v,:len(bones)]=np.array(values)/sum(values)
        actual_i,actual_w=decode(encode(i,w,8),3,8)
        oracle=json.loads((FIXTURES/'python-readback.json').read_text())
        np.testing.assert_array_equal(np.concatenate([i[w>0] for i,w in zip(actual_i,actual_w)]),oracle['boneIndices'])
        np.testing.assert_array_equal(np.concatenate([w[w>0] for w in actual_w]).astype('f4'),np.asarray(oracle['weights'],'f4'))
        self.assertLess(oracle['unlimitedBakeMaximumError'],2e-7)
        self.assertGreater(oracle['fourBoneBakeMaximumError'],.01)

    def test_fallback_is_top_four_normalized_and_full_field_is_retained(self):
        i,w=decode(self.words,3,8);fi,fw=fallback(i,w)
        np.testing.assert_array_equal(fi[2],[0,1,2,3])
        np.testing.assert_allclose(fw.sum(1),1,atol=2e-7)
        self.assertEqual(np.count_nonzero(w[2]),8)
        self.assertLess(w[2,:4].sum(),.8)
        self.assertEqual(encode(i,w,8),self.words)

    def test_malformed_packed_header_mass_bone_and_order_are_rejected(self):
        for position,value in [(0,3),(3,len(self.words)+1),(4,0x00010000),(4,0xffff0008),(6,self.words[5]+65536)]:
            with self.subTest(position=position,value=value):
                broken=self.words.copy();broken[position]=value
                with self.assertRaises(ValueError):decode(broken,3,8)

    def test_invalid_source_fields_are_rejected(self):
        for i,w,bones in [([[0,0]],[[.5,.5]],8),([[0,8]],[[.5,.5]],8),([[0,1]],[[.6,.6]],8),([[0,1]],[[1.1,-.1]],8),([[0,1]],[[np.nan,1]],8),([[.5,1]],[[.5,.5]],8),([[True,False]],[[.5,.5]],8),([[0,1]],[[.5,.5]],True)]:
            with self.subTest(i=i,w=w,bones=bones):
                with self.assertRaises(ValueError):encode(i,w,bones)
        for i,w in [([[-1]],[[1]]),([[.5]],[[1]]),([[0,0]],[[.5,.5]]),([[0,1]],[[0,0]]),([[0]],[[np.inf]])]:
            with self.subTest(fallback_indices=i):
                with self.assertRaises(ValueError):fallback(i,w)

    def test_malformed_dimensions_and_word_types_are_rejected(self):
        for words,vertices,bones in [(self.words,3.5,8),(self.words,True,8),([True]*17,3,8),([complex(1,1)]*17,3,8),(['4']*17,3,8),(self.words,3,8.5),([4,5,9,17]+[-1]*13,3,8)]:
            with self.subTest(vertices=vertices,bones=bones):
                with self.assertRaises(ValueError):decode(words,vertices,bones)

    def test_unsigned_sixteen_bit_bone_index_boundary(self):
        i,w=decode(encode([[65535]],[[1.]],65536),1,65536)
        self.assertEqual(int(i[0,0]),65535)
        self.assertEqual(float(w[0,0]),1.)
        with self.assertRaises(ValueError):fallback(i,w)

    def test_serialized_writer_preserves_full_field_and_bounds_extra_bones(self):
        import UnityPy
        from UnityPy.helpers.MeshHelper import MeshHandler
        from catgun.geometry import Mesh
        from operators.bundles import geometry_check
        env=UnityPy.load(str(FIXTURES/'ReferenceWeights.asset'))
        obj=next(o for o in env.objects if o.type.name=='Mesh')
        template=obj.read_typetree();h=MeshHandler(obj.read());h.process()
        mesh=Mesh();mesh.vertices=np.asarray(h.m_Vertices).tolist();mesh.normals=np.asarray(h.m_Normals).tolist();mesh.uv=[[.5,.5]]*3
        mesh.faces=np.concatenate([np.asarray(t).reshape(-1,3) for t in h.get_triangles()]).tolist()
        i,w=decode(self.words,3,8)
        tree,fi,fw=skinned_tree_variable(template,mesh,'MWC variable-weight test',i,w,8)
        self.assertEqual(tree['m_VariableBoneCountWeights']['m_Data'],self.words)
        # Bone 7 affects only vertex 2 through the full eight-influence row.
        # It is absent from that vertex's four-weight fallback.
        self.assertNotIn(7,fi[2])
        bounds=tree['m_BonesAABB'][7]
        self.assertTrue(all(np.isfinite(list(bounds[k].values())).all() for k in ('m_Min','m_Max')))
        obj.save_typetree(tree)
        checked=UnityPy.load(env.file.save())
        actual=next(o for o in checked.objects if o.type.name=='Mesh')
        geometry_check(actual,mesh,fi,fw)
        self.assertEqual(actual.read_typetree()['m_VariableBoneCountWeights']['m_Data'],self.words)

if __name__=='__main__':unittest.main()
