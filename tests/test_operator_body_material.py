import copy,unittest
from types import SimpleNamespace
from operators.body_material import template,SPEC


class Material:
    type=SimpleNamespace(name='Material')
    def __init__(self,pid,name='body',shader=None):
        self.path_id=pid;self.name=name
        self.tree={'m_Shader':copy.deepcopy(shader or SPEC['shader']),
                   'm_SavedProperties':{'m_TexEnvs':[(n,{}) for n in ('_BaseMap','_BumpMap','_MetallicGlossMap')]}}
        self.assets_file=SimpleNamespace(externals=[SimpleNamespace(path='unused'),SimpleNamespace(path='archive:/'+SPEC['shader_archive'])])
    def peek_name(self):return self.name
    def read_typetree(self):return copy.deepcopy(self.tree)


class ReplacementBodyTemplate(unittest.TestCase):
    def setUp(self):
        self.canonical=Material(int(SPEC['native_template_id']),SPEC['native_template_name'])
        self.native=Material(42)
        self.objects={self.canonical.path_id:self.canonical,42:self.native}
    def test_external_pointer_does_not_resolve_same_path_id_in_wrong_file(self):
        obj,record=template(self.objects,{'m_FileID':5,'m_PathID':42})
        self.assertIs(obj,self.canonical);self.assertEqual(record['reason'],'external native material')
    def test_native_local_graph_stays_selected(self):
        obj,record=template(self.objects,{'m_FileID':0,'m_PathID':42})
        self.assertIs(obj,self.native)
    def test_helmet_graph_does_not_become_an_authored_body_shader(self):
        self.native.tree['m_Shader']['m_PathID']=-4829422393666354369
        obj,record=template(self.objects,{'m_FileID':0,'m_PathID':42})
        self.assertIs(obj,self.canonical);self.assertIn('another shader',record['reason'])
    def test_first_person_keeps_skin_graph_and_rejects_unreviewed_external(self):
        self.native.tree['m_Shader']['m_PathID']=99
        obj,_=template(self.objects,{'m_FileID':0,'m_PathID':42},first_person=True)
        self.assertIs(obj,self.native)
        with self.assertRaisesRegex(ValueError,'External first-person'):
            template(self.objects,{'m_FileID':5,'m_PathID':42},first_person=True)
    def test_changed_external_table_or_template_interface_fails(self):
        for changed in ('archive','name','slots'):
            with self.subTest(changed=changed):
                obj=copy.deepcopy(self.canonical)
                if changed=='archive':obj.assets_file.externals[1].path='different'
                if changed=='name':obj.name='different'
                if changed=='slots':obj.tree['m_SavedProperties']['m_TexEnvs']=[]
                with self.assertRaises(ValueError):template({obj.path_id:obj},{'m_FileID':4,'m_PathID':42})


if __name__=='__main__':unittest.main()
