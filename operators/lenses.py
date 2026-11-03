"""Use the shipped URP Lit shader for genuinely alpha-blended shooting lenses.

The body Custom Lit graph has fixed One/Zero blending and cannot become glass
by adding _Surface floats. Clone an exact local URP Lit material instead; its
existing external shader reference points to the shared native shader bundle.
"""
import copy,hashlib,json
from pathlib import Path
import numpy as np
from UnityPy.streams import EndianBinaryReader

SPEC=json.loads((Path(__file__).resolve().parents[1]/'config/operator-lens-material.json').read_text())
STATES={'_Surface':1.,'_Blend':0.,'_SrcBlend':5.,'_DstBlend':10.,
        '_SrcBlendAlpha':1.,'_DstBlendAlpha':10.,'_ZWrite':0.,'_Cull':2.,
        '_AlphaClip':0.,'_AlphaToMask':0.,'_Metallic':0.,'_Smoothness':.45,
        '_BlendModePreserveSpecular':0.}
DISABLED=['DepthOnly','DepthNormals','DepthNormalsOnly','SHADOWCASTER','MOTIONVECTORS']


def template(objects):
    obj=objects.get(int(SPEC['native_template_id']))
    if obj is None or obj.type.name!='Material' or obj.peek_name()!=SPEC['native_template_name'] or hashlib.sha256(obj.get_raw_data()).hexdigest()!=SPEC['native_template_sha256']:
        raise ValueError('Reviewed native lens material template changed')
    tree=obj.read_typetree();pointer=tree['m_Shader']
    if pointer!=SPEC['shader'] or SPEC['shader_archive'] not in obj.assets_file.externals[pointer['m_FileID']-1].path:
        raise ValueError('Reviewed lens shader reference changed')
    return obj


def configure_tree(tree):
    if tree['m_Shader']!=SPEC['shader']:raise ValueError('Shooting lens requires the reviewed URP Lit shader')
    tree=copy.deepcopy(tree);floats=dict(tree['m_SavedProperties']['m_Floats']);floats.update(STATES)
    tree['m_SavedProperties']['m_Floats']=list(floats.items());tree['m_ValidKeywords']=['_SURFACE_TYPE_TRANSPARENT'];tree['m_InvalidKeywords']=[]
    if 'm_ShaderKeywords' in tree:tree['m_ShaderKeywords']='_SURFACE_TYPE_TRANSPARENT'
    tags=dict(tree.get('stringTagMap',[]));tags['RenderType']='Transparent';tree['stringTagMap']=list(tags.items())
    tree['m_CustomRenderQueue']=3000;tree['disabledShaderPasses']=sorted(set(tree.get('disabledShaderPasses',[]))|set(DISABLED))
    return tree


def configure(obj):
    # UnityPy's read_typetree reads the original reader, not pending obj.data.
    # Preserve the newly assigned name, colors and neutral maps when finishing.
    if obj.data is None:raise ValueError('Expected a newly built lens material')
    pending=copy.copy(obj);pending.reader=EndianBinaryReader(obj.data,endian=obj.reader.endian);pending.byte_start=0;pending.byte_size=len(obj.data)
    obj.save_typetree(configure_tree(pending.read_typetree()));return obj


def verify(obj):
    tree=obj.read_typetree();floats=dict(tree['m_SavedProperties']['m_Floats'])
    if tree['m_Shader']!=SPEC['shader'] or any(not np.isclose(floats.get(k,-999),v) for k,v in STATES.items()):raise ValueError('Shooting lens shader/blend/depth state changed')
    if tree['m_ValidKeywords']!=['_SURFACE_TYPE_TRANSPARENT'] or tree['m_CustomRenderQueue']!=3000 or dict(tree['stringTagMap']).get('RenderType')!='Transparent' or not set(DISABLED)<=set(tree['disabledShaderPasses']):raise ValueError('Shooting lens queue/keyword/pass configuration changed')
    color=dict(tree['m_SavedProperties']['m_Colors'])['_BaseColor']
    if not 0<color['a']<1:raise ValueError('Shooting lens must retain partial opacity')
    return {'shader':SPEC['shader_name'],'alpha_blending':True,'depth_write':False,'backface_culling':True,'in_game_tested':False}
