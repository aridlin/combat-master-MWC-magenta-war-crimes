#!/usr/bin/env python3
"""Static Lynx mesh/hierarchy and representative UV audit; no game writes."""
import gc
import json
import re
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from halftone.assets import key, pointer, dump

ROOT=Path(__file__).resolve().parent


def inspect_bundle(source, relative):
    env=UnityPy.load(str(source))
    names={}
    for obj in env.objects:
        if obj.type.name in ('GameObject','Mesh','Material','AnimationClip'):
            names[key(obj.assets_file.name,obj.path_id)]=obj.peek_name()
    transforms={}; go_transforms={}; filters={}
    for obj in env.objects:
        if obj.type.name=='Transform':
            t=obj.read(); oid=key(obj.assets_file.name,obj.path_id); go=pointer(t.m_GameObject,obj.assets_file)
            transforms[oid]={'name':names.get(go,''),'parent':pointer(t.m_Father,obj.assets_file),
                'local_position':[t.m_LocalPosition.x,t.m_LocalPosition.y,t.m_LocalPosition.z],
                'local_scale':[t.m_LocalScale.x,t.m_LocalScale.y,t.m_LocalScale.z]}
            go_transforms[go]=oid
        elif obj.type.name=='MeshFilter':
            f=obj.read(); filters[pointer(f.m_GameObject,obj.assets_file)]=pointer(f.m_Mesh,obj.assets_file)
    def hierarchy(go):
        current=go_transforms.get(go); chain=[]; seen=set()
        while current in transforms and current not in seen:
            seen.add(current); t=transforms[current]; chain.append({'id':current,**t}); current=t['parent']
        return list(reversed(chain))
    renderers=[]
    for obj in env.objects:
        if obj.type.name in ('MeshRenderer','SkinnedMeshRenderer'):
            r=obj.read(); go=pointer(r.m_GameObject,obj.assets_file)
            mesh=pointer(getattr(r,'m_Mesh',None),obj.assets_file) or filters.get(go)
            chain=hierarchy(go)
            if re.search(r'(?i)lynx|gm6',names.get(go,'')+' '+names.get(mesh,'')+' '+'/'.join(x['name'] for x in chain)):
                renderers.append({'id':key(obj.assets_file.name,obj.path_id),'type':obj.type.name,
                    'game_object':go,'name':names.get(go,''),'mesh':mesh,'mesh_name':names.get(mesh,''),
                    'materials':[{'id':pointer(p,obj.assets_file),'name':names.get(pointer(p,obj.assets_file),'external')}
                                 for p in r.m_Materials if p.m_PathID],
                    'bones':len(getattr(r,'m_Bones',[]) or []),'hierarchy':chain})
    animations=[{'id':oid,'name':name} for oid,name in names.items() if re.search(r'(?i)lynx|gm6',name)]
    nodes=[{'id':oid,**t} for oid,t in transforms.items()
           if re.search(r'(?i)lynx|gm6|muzzle|firepoint',t['name'])]
    samples=[]
    selected=[]
    for obj in env.objects:
        if obj.type.name=='Mesh':
            name=names.get(key(obj.assets_file.name,obj.path_id),'')
            if (re.search(r'(?i)GM6_Lynx_Receiver_01_LOD0|GM6_Lynx_Barrel_02_LOD0',name)
                or (relative=='src/thrid_person' and len(selected)<1)):
                selected.append(obj)
    for obj in selected[:3]:
        sample={'id':key(obj.assets_file.name,obj.path_id),'name':obj.peek_name()}
        try:
            mesh=obj.read(); handler=MeshHandler(mesh); handler.process()
            vertices=np.asarray(handler.m_Vertices,dtype=float)
            uv=np.asarray(handler.m_UV0,dtype=float)
            triangles=np.asarray([t for part in handler.get_triangles() for t in part],dtype=int)
            # get_triangles() returns flat indices in some versions.
            triangles=triangles.reshape(-1,3)
            sample.update({'vertices':len(vertices),'triangles':len(triangles),
                'submeshes':len(mesh.m_SubMeshes),'uv0_count':len(uv),
                'bindposes':len(mesh.m_BindPose),'compressed_mesh':mesh.m_MeshCompression,
                'bounds_min':vertices.min(axis=0).tolist(),'bounds_max':vertices.max(axis=0).tolist(),
                'uv_min':uv.min(axis=0).tolist(),'uv_max':uv.max(axis=0).tolist()})
            a,b,c=vertices[triangles[:,0]],vertices[triangles[:,1]],vertices[triangles[:,2]]
            ua,ub,uc=uv[triangles[:,0],:2],uv[triangles[:,1],:2],uv[triangles[:,2],:2]
            areas=np.linalg.norm(np.cross(b-a,c-a),axis=1)/2
            uvareas=np.abs((ub[:,0]-ua[:,0])*(uc[:,1]-ua[:,1])-(ub[:,1]-ua[:,1])*(uc[:,0]-ua[:,0]))/2
            valid=(areas>1e-12)&(uvareas>1e-12)
            scale=np.sqrt(areas[valid]/uvareas[valid])
            sample['local_units_per_uv_area_scale_quantiles']=np.quantile(scale,[.1,.5,.9]).tolist()
            sample['world_scale_limitation']='Local units only: prefab/runtime scaling and UV island anisotropy prevent a verified 1.28m world tile.'
            # Read/serialize no-op capability test. No modified mesh is deployed.
            original=obj.get_raw_data(); obj.read().save()
            sample['noop_mesh_serialization_byte_exact']=obj.data==original
        except Exception as exc:
            sample['error']=str(exc)
        samples.append(sample)
    result={'bundle':relative,'lynx_renderers':renderers,'named_assets':animations,
            'lynx_and_muzzle_nodes':nodes,'uv_and_mesh_samples':samples}
    del env; gc.collect()
    return result


def main():
    config=json.loads((ROOT/'halftone.json').read_text()); root=Path(config['bundle_root'])
    records=[]
    for relative in ('src/weapons/weapons','src/weapons/attachments','src/first_person','root/game_prefabs','src/thrid_person'):
        source=ROOT/'backups/thrid_person.original' if relative=='src/thrid_person' else root/relative
        print('Inspecting meshes/hierarchy:',relative,flush=True)
        records.append(inspect_bundle(source,relative))
    dump(ROOT/'reports/halftone/lynx-investigation.json',{'bundles':records,
        'implementation_status':'Assessment only; no cat mesh or weapon hierarchy deployed.',
        'constraints':['Lynx is multipart, not a single texture or mesh.',
            'Parts may be reused by first/third-person presentations and gunsmith variants.',
            'No trusted cat mesh with compatible vertex/bone/UV layout is supplied.',
            'No-op mesh serialization alone does not validate modified geometry, animation or muzzle alignment.',
            'Minimal next prototype: isolated Unity scene with an authored rigid cat attached to an unchanged receiver transform; keep muzzle nodes, animations, sounds and game scripts intact.']})


if __name__=='__main__': main()
