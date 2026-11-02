import copy
import unittest
from halftone.materials import check_material_diff


class Reader:
    def __init__(self,tree): self.tree=tree
    def read_typetree(self): return copy.deepcopy(self.tree)


class DiffuseWhitelist(unittest.TestCase):
    def setUp(self):
        self.before={'m_Shader':{'m_PathID':99},'m_SavedProperties':{
            'm_Floats':[('EnableCamo',1.0),('Smoothness',.7),('_Metallic',.8)],
            'm_Colors':[('AlbedoColor',{'r':.4,'g':.5,'b':.6,'a':.25})],
            'm_TexEnvs':[('Normal',{'m_PathID':100})]}}
        self.after=copy.deepcopy(self.before)
        self.after['m_SavedProperties']['m_Floats'][0]=('EnableCamo',0.0)
        for c in ('r','g','b'): self.after['m_SavedProperties']['m_Colors'][0][1][c]=1.0

    def test_accepts_only_diffuse_cleanup(self):
        check_material_diff(Reader(self.before),Reader(self.after))

    def test_rejects_alpha_change(self):
        self.after['m_SavedProperties']['m_Colors'][0][1]['a']=1
        with self.assertRaises(ValueError): check_material_diff(Reader(self.before),Reader(self.after))

    def test_rejects_smoothness_or_shader_changes(self):
        self.after['m_Shader']['m_PathID']=101
        with self.assertRaises(ValueError): check_material_diff(Reader(self.before),Reader(self.after))

    def test_declared_albedo_copy_binding_allowed(self):
        self.before['m_SavedProperties']['m_TexEnvs'].append(('_BaseMap',{'m_Texture':{'m_FileID':0,'m_PathID':10}}))
        self.after['m_SavedProperties']['m_TexEnvs'].append(('_BaseMap',{'m_Texture':{'m_FileID':0,'m_PathID':20}}))
        binding={'slot':'_BaseMap','file_id':0,'old_path_id':10,'new_path_id':20}
        check_material_diff(Reader(self.before),Reader(self.after),[binding])

    def test_data_map_binding_not_allowed(self):
        binding={'slot':'Normal','file_id':0,'old_path_id':10,'new_path_id':20}
        with self.assertRaises(ValueError): check_material_diff(Reader(self.before),Reader(self.after),[binding])
        self.after['m_Shader']['m_PathID']=99
        self.after['m_SavedProperties']['m_Floats'][1]=('Smoothness',1)
        with self.assertRaises(ValueError): check_material_diff(Reader(self.before),Reader(self.after))


if __name__=='__main__': unittest.main()
