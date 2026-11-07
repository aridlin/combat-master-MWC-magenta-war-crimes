import copy,unittest
from types import SimpleNamespace
from PIL import Image
from operators.material_data import verify


class Material:
    def __init__(self,weapon):
        self.tree={'m_SavedProperties':{
            'm_Floats':[('_IsWeapon',float(weapon)),('Smoothness',.12)],
            'm_TexEnvs':[(name,{'m_Texture':{'m_FileID':0,'m_PathID':pid}})
                         for name,pid in [('Albedo',3),('Metallic',1),('Normal',2)]]}}
    def read_typetree(self):return copy.deepcopy(self.tree)


def texture(pixel,linear=True):
    return SimpleNamespace(read=lambda:SimpleNamespace(
        m_ColorSpace=0 if linear else 1,image=Image.new('RGBA',(2,2),pixel)))


class NativeDataMapProfiles(unittest.TestCase):
    def test_existing_character_map_and_normal_remain_accepted(self):
        # Character mode reads red, so the established map has no metalness.
        verify(Material(False),{1:texture((0,255,255,255)),2:texture((128,128,255,255))},True)

    def test_weapon_rejects_the_character_map_that_makes_it_fully_metallic(self):
        objects={1:texture((0,255,255,255)),2:texture((128,128,255,255))}
        with self.assertRaisesRegex(ValueError,'Neutral data texture changed: Metallic'):
            verify(Material(True),objects,True,weapon_mode=True)
        # Blue is the metalness channel in the reviewed weapon branch;
        # retain alpha for the existing smoothness scalar and the normal map.
        objects[1]=texture((0,255,0,255))
        verify(Material(True),objects,True,weapon_mode=True)

    def test_weapon_profile_does_not_silently_change_material_mode(self):
        with self.assertRaisesRegex(ValueError,'reviewed weapon-mode material'):
            verify(Material(False),{},weapon_mode=True)

    def test_correct_pixel_values_still_require_linear_data_and_neutral_normals(self):
        objects={1:texture((0,255,0,255),linear=False),2:texture((128,128,255,255))}
        with self.assertRaisesRegex(ValueError,'Metallic'):
            verify(Material(True),objects,weapon_mode=True)
        objects[1]=texture((0,255,0,255));objects[2]=texture((255,255,255,255))
        with self.assertRaisesRegex(ValueError,'Normal'):
            verify(Material(True),objects,weapon_mode=True)


if __name__=='__main__':unittest.main()
