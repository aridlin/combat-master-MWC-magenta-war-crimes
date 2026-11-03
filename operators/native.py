"""Exact native operator renderer/bind-pose inspection; no installation writes."""
import hashlib,json
from pathlib import Path
import numpy as np
import UnityPy


def native_rig(env,target):
    objects={o.path_id:o for o in env.objects};transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    owned={int(r['path_id']):r for r in target['renderers']};renderers={};meshes={};lods={}
    for rid,record in owned.items():
        obj=objects.get(rid)
        if not obj or obj.type.name!='SkinnedMeshRenderer' or hashlib.sha256(obj.get_raw_data()).hexdigest()!=record['sha256']:raise ValueError('Native operator renderer changed: '+str(rid))
        tree=obj.read_typetree();pointer=tree['m_Mesh']
        if pointer['m_FileID']!=0:raise ValueError('Expected a local operator mesh')
        renderers[rid]=tree;meshes[rid]=objects[pointer['m_PathID']]
    for obj in env.objects:
        if obj.type.name!='LODGroup':continue
        tree=obj.read_typetree()
        for level,lod in enumerate(tree['m_LODs']):
            for row in lod['renderers']:
                ptr=row['renderer']
                if ptr['m_FileID']==0 and ptr['m_PathID'] in owned:lods.setdefault(level,set()).add(ptr['m_PathID'])
    if not lods:raise ValueError('Operator has no reviewed LOD group')
    primary={level:max(ids,key=lambda i:meshes[i].read_typetree()['m_VertexData']['m_VertexCount']) for level,ids in lods.items()}
    snapshots={}
    for rid in set(primary.values()):
        tree=renderers[rid];mesh=meshes[rid].read_typetree();pointers=tree['m_Bones']
        if any(p['m_FileID']!=0 for p in pointers):raise ValueError('Expected a local operator skeleton')
        ids=[p['m_PathID'] for p in pointers];index={i:n for n,i in enumerate(ids)};names=[];parents=[]
        for i in ids:
            transform=transforms[i];names.append(objects[transform['m_GameObject']['m_PathID']].peek_name());parent=transform['m_Father']['m_PathID'];seen=set()
            while parent and parent not in index:
                if parent in seen:raise ValueError('Cyclic native transform hierarchy')
                seen.add(parent);parent=transforms[parent]['m_Father']['m_PathID']
            parents.append(index.get(parent,-1))
        bind=np.asarray([[[p['e'+str(i)+str(j)] for j in range(4)] for i in range(4)] for p in mesh['m_BindPose']],dtype='<f4')
        if bind.shape!=(len(ids),4,4) or not np.isfinite(bind).all():raise ValueError('Invalid native inverse bind data')
        snapshots[rid]={'bone_names':names,'bone_parents':parents,'inverse_bind':bind,'renderer':tree,'mesh_object':meshes[rid],'mesh_tree':mesh}
    return {'objects':objects,'renderers':renderers,'meshes':meshes,'primary':primary,'snapshots':snapshots,'target':target}


def export(bundle_root,target_id,output):
    root=Path(__file__).resolve().parents[1];targets=json.loads((root/'config/operator-targets.json').read_text())['operators'];target=next(t for t in targets if t['id']==target_id);env=UnityPy.load(str(Path(bundle_root)/target['bundle']));rig=native_rig(env,target);rid=rig['primary'][min(rig['primary'])];s=rig['snapshots'][rid];output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output.with_suffix('.npz'),inverse_bind=s['inverse_bind'],bone_parents=np.asarray(s['bone_parents'],dtype='<i4'))
    output.with_suffix('.json').write_text(json.dumps({'id':target_id,'name':target['name'],'bone_names':s['bone_names'],'bone_parents':s['bone_parents'],'primary_renderers':{str(k):str(v) for k,v in rig['primary'].items()},'renderer_path_id':str(rid)},indent=2)+'\n')
    return {'operator':target_id,'primary_renderers':rig['primary'],'bones':len(s['bone_names'])}
