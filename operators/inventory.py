"""Read shipped operator identities and exact prefab GUIDs without assemblies.

Build-specific OperatorInfo layout is checked against every named record and
the AssetBundle container. Names are never used as broad replacement regexes.
"""
import hashlib
import re
import struct
from pathlib import Path
import UnityPy


def inspect(bundle_root):
    bundle_root=Path(bundle_root)
    data=UnityPy.load(str(bundle_root.parents[1]/'data.unity3d'))
    script=next(o.path_id for o in data.objects if o.type.name=='MonoScript' and o.read().m_ClassName=='OperatorInfo')
    english=next(o.get_raw_data() for o in data.objects if o.assets_file.name=='resources.assets' and o.path_id==5335)
    names={}
    for match in re.finditer(rb'gd_operators_operator_(\d+)_name',english):
        offset=(match.end()+3)//4*4
        size=struct.unpack_from('<I',english,offset)[0]
        if size>4096:raise ValueError('Unexpected localized operator name size')
        names[int(match[1])]=english[offset+4:offset+4+size].decode('utf8')
    env=UnityPy.load(str(bundle_root/'src/thrid_person'))
    objects={o.path_id:o for o in env.objects}
    transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    by_go={t['m_GameObject']['m_PathID']:i for i,t in transforms.items()}
    roots={t['m_GameObject']['m_PathID'] for t in transforms.values() if not t['m_Father']['m_PathID']}
    container=next(o.read_typetree()['m_Container'] for o in env.objects if o.type.name=='AssetBundle')
    prefabs={}
    for guid,row in container:
        pointer=row['asset'];o=objects.get(pointer['m_PathID'])
        if pointer['m_FileID']==0 and o and o.path_id in roots:
            if guid in prefabs:raise ValueError('Ambiguous operator prefab GUID')
            prefabs[guid]=o
    renderers=[]
    for o in env.objects:
        if o.type.name!='SkinnedMeshRenderer':continue
        t=o.read_typetree();go=t['m_GameObject']['m_PathID'];tid=by_go[go];seen=set()
        while transforms[tid]['m_Father']['m_PathID']:
            if tid in seen:raise ValueError('Cyclic operator hierarchy')
            seen.add(tid);tid=transforms[tid]['m_Father']['m_PathID']
        renderers.append((transforms[tid]['m_GameObject']['m_PathID'],o,t,objects[go].peek_name()))
    result=[]
    for o in data.objects:
        if o.type.name!='MonoBehaviour' or o.assets_file.name!='resources.assets':continue
        raw=o.get_raw_data()
        if len(raw)<32 or struct.unpack_from('<iq',raw,16)!=(1,script):continue
        size=struct.unpack_from('<I',raw,28)[0]
        if size>256:raise ValueError('Unexpected OperatorInfo name')
        name=raw[32:32+size].decode('utf8');offset=(32+size+3)//4*4
        identity=struct.unpack_from('<I',raw,offset)[0]
        if identity>>24!=2:raise ValueError('Unexpected operator identity namespace')
        identifier=identity&0xffffff
        if not name.startswith(str(identifier)+'.'):raise ValueError('Operator identity/name mismatch')
        guid=raw[offset+128:offset+144].hex();prefab=prefabs.get(guid)
        if not prefab:raise ValueError('Operator prefab not found: '+name)
        owned=[{'path_id':str(r.path_id),'name':n,'bones':len(t['m_Bones']),'sha256':hashlib.sha256(r.get_raw_data()).hexdigest()} for root,r,t,n in renderers if root==prefab.path_id]
        if not owned:raise ValueError('Operator has no owned skinned renderers: '+name)
        result.append({'id':'operator_'+str(identifier),'name':names.get(identifier,name.split('.',1)[1]),'internal_name':name,'bundle':'src/thrid_person','prefab_guid':guid,'prefab_path_id':str(prefab.path_id),'resource_path_id':str(o.path_id),'renderers':owned,'identity_verified':True})
    if len(result)!=32 or len({x['id'] for x in result})!=len(result):raise ValueError('Expected 32 unique operator records for this game build')
    return sorted(result,key=lambda x:int(x['id'].split('_')[1]))
