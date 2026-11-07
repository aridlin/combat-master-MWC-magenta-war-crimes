"""Explicit data maps for the reviewed native character and weapon paths.

That graph has no _Metallic scalar. An unbound _MetallicGlossMap defaults to
white (metallic), and an unbound normal map also defaults to white. These are
linear data textures, independent of the character's sRGB albedo atlas.

UniversalSkinshader uses blue for metalness when _IsWeapon is true, while its
character branch uses red. Keep the established character maps unchanged;
weapon_mode also clears blue for the explicitly reviewed Sonic weapon donor.
"""
from PIL import Image
from UnityPy.export.Texture2DConverter import image_to_texture2d
from catgun.bundle import new_object


PIXELS={'metallic':(0,255,255,255),'normal':(128,128,255,255)}
WEAPON_PIXELS={**PIXELS,'metallic':(0,255,0,255)}


def create(template,objects,*,weapon_mode=False):
    result={}
    for role,pixel in (WEAPON_PIXELS if weapon_mode else PIXELS).items():
        obj=new_object(template,'MWC_OperatorNeutral_'+role,objects);texture=obj.read();image=Image.new('RGBA',(2,2),pixel);raw,_=image_to_texture2d(image,4);texture.m_Name='MWC_OperatorNeutral_'+role;texture.m_Width=texture.m_Height=2;texture.m_TextureFormat=4;texture.image_data=raw;texture.m_CompleteImageSize=len(raw);texture.m_MipCount=1
        if texture.m_MipMap is not None:texture.m_MipMap=False
        texture.m_ColorSpace=0;texture.m_StreamData.path='';texture.m_StreamData.offset=texture.m_StreamData.size=0;texture.m_TextureSettings.m_FilterMode=0;texture.m_TextureSettings.m_WrapU=texture.m_TextureSettings.m_WrapV=1;texture.save();result[role]=obj
    return result


def verify(material,objects,require_albedo=False,*,weapon_mode=False):
    """Check serialized bindings, including the separate first-person shader."""
    tree=material.read_typetree();slots=dict(tree['m_SavedProperties']['m_TexEnvs']);floats=dict(tree['m_SavedProperties']['m_Floats'])
    if weapon_mode and floats.get('_IsWeapon')!=1:raise ValueError('Weapon data maps require the reviewed weapon-mode material')
    expected_pixels=WEAPON_PIXELS if weapon_mode else PIXELS
    if require_albedo and not any(slots.get(name,{}).get('m_Texture',{}).get('m_PathID') for name in ('_BaseMap','_MainTex','Albedo')):raise ValueError('Authored character albedo is unbound')
    for role,names in [('metallic',('_MetallicGlossMap','_SpecGlossMap','Metallic')),('normal',('_BumpMap','Normal'))]:
        found=False
        for name in names:
            if name not in slots:continue
            pointer=slots[name]['m_Texture'];texture=objects.get(pointer['m_PathID'])
            if pointer['m_FileID'] or texture is None:raise ValueError('Neutral data texture is unbound: '+name)
            data=texture.read()
            image=data.image;pixels=image.get_flattened_data() if hasattr(image,'get_flattened_data') else image.getdata()
            if data.m_ColorSpace!=0 or set(pixels)!={expected_pixels[role]}:raise ValueError('Neutral data texture changed: '+name)
            found=True
        if not found:raise ValueError('Character material lacks explicit '+role+' data')
    for name in ('_Smoothness','Smoothness'):
        if name in floats and not 0<=floats[name]<=.5:raise ValueError('Unexpected character smoothness')
