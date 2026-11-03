import copy,unittest
from operators.lenses import configure_tree,SPEC,STATES,DISABLED
from operators.review import material_appearance


class LensRenderState(unittest.TestCase):
    def test_lens_uses_real_transparent_shader_with_no_opaque_auxiliary_passes(self):
        source={'m_Shader':copy.deepcopy(SPEC['shader']),'m_SavedProperties':{'m_Floats':[('_ZWrite',1.)]},'m_ValidKeywords':[],'m_InvalidKeywords':['old'],'m_CustomRenderQueue':-1,'stringTagMap':[('RenderType','Opaque')],'disabledShaderPasses':[]}
        result=configure_tree(source)
        self.assertEqual(dict(result['m_SavedProperties']['m_Floats']),STATES)
        self.assertEqual(result['m_ValidKeywords'],['_SURFACE_TYPE_TRANSPARENT'])
        self.assertTrue(set(DISABLED)<=set(result['disabledShaderPasses']))
        self.assertEqual(dict(result['stringTagMap'])['RenderType'],'Transparent')
        self.assertEqual(source['m_SavedProperties']['m_Floats'],[('_ZWrite',1.)])
    def test_character_graph_cannot_silently_substitute_for_glass(self):
        with self.assertRaisesRegex(ValueError,'URP Lit'):
            configure_tree({'m_Shader':{'m_FileID':2,'m_PathID':9216735585210638481}})
    def test_preview_does_not_show_false_transparency_from_unsupported_body_floats(self):
        tree={'m_Name':'lens','m_Shader':{'m_FileID':2,'m_PathID':9216735585210638481},'m_SavedProperties':{'m_Floats':list(STATES.items()),'m_Colors':[('_BaseColor',dict(r=.32,g=.095,b=.035,a=.4))]}}
        old=material_appearance(tree);self.assertEqual(old['base_color_linear'][3],1);self.assertNotIn('transparent',old)
        tree['m_Shader']=copy.deepcopy(SPEC['shader']);new=material_appearance(tree)
        self.assertEqual(new['base_color_linear'][3],.4);self.assertTrue(new['transparent']);self.assertTrue(new['cull_backfaces'])


if __name__=='__main__':unittest.main()
