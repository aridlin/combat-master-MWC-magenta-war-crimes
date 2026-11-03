"""Choose a local replacement material without importing foreign PPtr tables.

Two native world operators use external materials; another uses a helmet graph.
An authored replacement body can use the reviewed local character graph instead.
Do not copy an external material's shader pointer into a different asset file.
"""
import json
from pathlib import Path

SPEC=json.loads((Path(__file__).resolve().parents[1]/'config/operator-body-material.json').read_text())


def _character_graph(obj):
    if obj is None or obj.type.name!='Material':return False
    pointer=obj.read_typetree()['m_Shader']
    if pointer!=SPEC['shader']:return False
    external=obj.assets_file.externals
    return 0<pointer['m_FileID']<=len(external) and SPEC['shader_archive'] in external[pointer['m_FileID']-1].path


def template(objects,pointer,first_person=False):
    native=objects.get(pointer['m_PathID']) if pointer['m_FileID']==0 else None
    if first_person:
        if native is None or native.type.name!='Material':raise ValueError('External first-person material needs a reviewed local skin template')
        return native,{'selection':'native first-person material','path_id':native.path_id}
    if _character_graph(native):
        return native,{'selection':'native local character graph','path_id':native.path_id}
    reviewed=objects.get(int(SPEC['native_template_id']))
    if not _character_graph(reviewed) or reviewed.peek_name()!=SPEC['native_template_name']:
        raise ValueError('Reviewed local replacement body material changed')
    slots=dict(reviewed.read_typetree()['m_SavedProperties']['m_TexEnvs'])
    if not {'_BaseMap','_BumpMap','_MetallicGlossMap'}<=slots.keys():
        raise ValueError('Reviewed body material texture slots changed')
    # The existing texture modules may have changed this template's albedo
    # binding. The new material builder replaces all of its texture bindings;
    # validate the stable shader/interface rather than rejecting that composition.
    return reviewed,{'selection':'reviewed local character graph','path_id':reviewed.path_id,
                     'reason':'external native material' if pointer['m_FileID'] else 'native material uses another shader',
                     'original_material_pointer':dict(pointer)}
