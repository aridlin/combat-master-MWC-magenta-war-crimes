#!/usr/bin/env python3
"""Offline visual-only sight meshes and reticle pictures, with exact rollback."""
import argparse,copy,gc,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
import UnityPy
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from halftone.pipeline import build_id
from catgun.geometry import Mesh
from catgun.bundle import new_object,mesh_tree,verify_geometry
from deploy_halftone import close_game,replace_verified

KEEP={'Red Dot','Red Arrow','Toxic Tris','Blue Dot','Circle Dot','Sun','Pulse'}


def iron_mesh():
    m=Mesh()
    def box(center,size):
        c=np.array(center);s=np.array(size)/2
        for axis in range(3):
            for sign in [-1,1]:
                n=np.zeros(3);n[axis]=sign
                others=[i for i in range(3) if i!=axis];ids=[]
                for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                    p=c.copy();p[axis]+=sign*s[axis];p[others[0]]+=a*s[others[0]];p[others[1]]+=b*s[others[1]]
                    ids.append(len(m.vertices));m.vertices.append(tuple(p));m.normals.append(tuple(n));m.uv.append((.5,.5))
                m.face(ids[0],ids[1],ids[2]);m.face(ids[0],ids[2],ids[3])
    x=-.0001
    box((x,.006,-.1093),(.018,.012,.004))
    for sign in [-1,1]:box((x+sign*.0055,.0133,-.1093),(.007,.0054,.004))
    box((x,.002,.1013),(.014,.006,.008))
    box((x,.009,.1013),(.0016,.0114,.003))
    for sign in [-1,1]:box((x+sign*.0055,.008,.1013),(.002,.012,.003))
    return m


def change_texture(obj,image):
    t=obj.read();raw,_=image_to_texture2d(image.convert('RGBA'),4)
    t.m_Width,t.m_Height=image.size;t.m_TextureFormat=4;t.m_MipCount=1
    if t.m_MipMap is not None:t.m_MipMap=False
    t.image_data=raw;t.m_CompleteImageSize=len(raw)
    t.m_StreamData.path='';t.m_StreamData.offset=t.m_StreamData.size=0;t.save()


def check(settings):
    manifest=json.loads((Path(settings['output'])/'manifest.json').read_text());results=[]
    for b in manifest['files']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:raise ValueError('Sight artifact hash mismatch')
        before=UnityPy.load(b['backup']);after=UnityPy.load(b['output'])
        A={key(o.assets_file.name,o.path_id):o for o in before.objects};B={key(o.assets_file.name,o.path_id):o for o in after.objects}
        if set(B)!=set(A)|set(b['added']):raise ValueError('Unexpected sight object IDs')
        for oid,obj in A.items():
            change=b['changes'].get(oid)
            if not change:
                if obj.get_raw_data()!=B[oid].get_raw_data():raise ValueError('Unrelated original object changed: '+oid)
            elif change['kind'] in ('mesh','disabled'):
                a=obj.read_typetree();z=B[oid].read_typetree()
                if change['kind']=='mesh':a['m_Mesh']=change['new_mesh']
                else:a['m_Enabled']=False
                if a!=z:raise ValueError('Nonvisual fields changed')
            elif change['kind']=='reticle':
                image=B[oid].read().image.convert('RGBA');wanted=Image.open(Path(settings['output'])/change['reference']).convert('RGBA')
                if not np.array_equal(np.array(image),np.array(wanted)):raise ValueError('Reticle pixels mismatch')
                a=obj.read_typetree();z=B[oid].read_typetree()
                for field in ['m_Width','m_Height','m_TextureFormat','m_MipCount','m_MipMap','image data','m_CompleteImageSize','m_StreamData']:
                    a.pop(field,None);z.pop(field,None)
                if a!=z:raise ValueError('Unexpected reticle property change')
        for oid in b['added']:
            if B[oid].type.name=='Mesh':verify_geometry(B[oid],iron_mesh())
        results.append({'bundle':b['bundle'],'changed_objects':len(b['changes']),'new_objects':len(b['added']),'all_other_original_objects_byte_exact':True})
        del before,after,A,B;gc.collect()
    return {'files':results,'reticles_replaced':manifest['reticles_replaced'],'protected_names':sorted(KEEP),'in_game_tested':False}


def build(config,settings):
    build_id(config);out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh sight output directory')
    if set(settings.get('sources',{}))!={'root/root','src/weapons/weapons','src/weapons/attachments'}:raise ValueError('Run prepare to record the intended installed baseline first')
    mapping=json.loads(Path(settings['mapping']).read_text());base=Path(config['bundle_root']);sun={}
    for identifier in [264,518]:
        d=next(d for d in mapping if d['id']==identifier);e=UnityPy.load(str(base/d['bundle']))
        o=next(o for o in e.objects if o.type.name=='Texture2D' and o.peek_name()==d['texture']['name']);sun[identifier]=o.read().image.convert('RGBA');sun[identifier].save(out/f'sun-{identifier}.png');del e;gc.collect()
    result={'files':[],'reticles_replaced':0,'in_game_tested':False,'keep':sorted(KEEP)}
    for rel,expected_hash in settings['sources'].items():
        source=base/rel
        if digest(source)!=expected_hash:raise ValueError('Installed sight baseline changed: '+rel)
        backup=Path(settings['backups'])/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():raise ValueError('Sight backup already exists')
        shutil.copyfile(source,backup);env=UnityPy.load(str(backup));expected=inventory(env)
        objects={key(o.assets_file.name,o.path_id):o for o in env.objects};changes={};added=[]
        for d in mapping:
            if not settings.get('reticles',True) or d['bundle']!=rel or d['label'] in KEEP:continue
            obj=next(o for o in env.objects if o.type.name=='Texture2D' and o.peek_name()==d['texture']['name']);reference=518 if 512<=d['id']<768 else 264
            change_texture(obj,sun[reference]);changes[key(obj.assets_file.name,obj.path_id)]={'kind':'reticle','id':d['id'],'name':d['label'],'reference':f'sun-{reference}.png'};result['reticles_replaced']+=1
        if rel=='src/weapons/attachments' and settings.get('iron',True):
            original=list(env.objects);names={o.path_id:o.peek_name() for o in original if o.type.name=='GameObject'}
            filters=[o for o in original if o.type.name=='MeshFilter' and names.get(o.read().m_GameObject.m_PathID,'').startswith('Dino_scope_LOD')]
            # This name also appears in the standalone blueprint prefab: select
            # only the inspected Steg Spikes prefab's exact three filter IDs.
            transforms={o.path_id:o.read_typetree() for o in original if o.type.name=='Transform'}
            parents={t['m_GameObject']['m_PathID']:names.get(transforms.get(t['m_Father']['m_PathID'],{}).get('m_GameObject',{}).get('m_PathID'),'') for t in transforms.values()}
            filters=[o for o in filters if parents.get(o.read().m_GameObject.m_PathID)=='Dino_Ironsight']
            if len(filters)!=3:raise ValueError('Unexpected Steg Spikes LOD layout')
            template=objects[key(filters[0].assets_file.name,filters[0].read().m_Mesh.m_PathID)]
            mesh=new_object(template,'MWC-Steg-standard-iron',objects);mesh.save_typetree(mesh_tree(template.read_typetree(),iron_mesh(),'MWC_StandardIronSight'));added.append(key(mesh.assets_file.name,mesh.path_id))
            for obj in filters:
                tree=obj.read_typetree();tree['m_Mesh']={'m_FileID':0,'m_PathID':mesh.path_id};obj.save_typetree(tree)
                changes[key(obj.assets_file.name,obj.path_id)]={'kind':'mesh','new_mesh':tree['m_Mesh']}
            # Existing material assignments stay intact. Hide only the old
            # luminous front-dot renderers belonging to this prefab.
            target_gos=set()
            transforms={o.path_id:o.read_typetree() for o in original if o.type.name=='Transform'}
            roots={o.path_id for o in original if o.type.name=='GameObject' and o.peek_name()=='Dino_Ironsight'}
            for tid,t in transforms.items():
                go=t['m_GameObject']['m_PathID'];name=names.get(go,'')
                father=transforms.get(t['m_Father']['m_PathID'],{})
                if name.startswith('Yironsight_front_up_04_Dots_LOD') and father.get('m_GameObject',{}).get('m_PathID') in roots:target_gos.add(go)
            for obj in original:
                if obj.type.name=='MeshRenderer' and obj.read().m_GameObject.m_PathID in target_gos:
                    tree=obj.read_typetree();tree['m_Enabled']=False;obj.save_typetree(tree);changes[key(obj.assets_file.name,obj.path_id)]={'kind':'disabled'}
            if len(target_gos)!=3:raise ValueError('Unexpected Steg front-dot layout')
        for oid in list(changes)+added:
            o=objects[oid];expected[(o.assets_file.name,o.path_id)]={'type':o.type.name,'sha256':hashlib.sha256(o.data).hexdigest()}
        output=out/rel;output.parent.mkdir(parents=True,exist_ok=True)
        output.write_bytes(env.file.save(packer='lz4'));del env,objects;gc.collect()
        reopened=UnityPy.load(str(output))
        if inventory(reopened)!=expected:raise ValueError('Sight serialization mismatch')
        del reopened;gc.collect()
        result['files'].append({'bundle':rel,'backup':str(backup.resolve()),'output':str(output.resolve()),'source_sha256':digest(backup),'output_sha256':digest(output),'changes':changes,'added':added})
        dump(out/'manifest.json',result)
    return check(settings)


def deploy(config,settings,action,dry_run):
    build_id(config);r=json.loads((Path(settings['output'])/'manifest.json').read_text());plan=[]
    for b in r['files']:
        target=Path(config['bundle_root'])/b['bundle'];current=digest(target)
        if current not in [b['source_sha256'],b['output_sha256']]:raise ValueError('Unknown installed sight bundle')
        src=Path(b['output'] if action=='install' else b['backup']);wanted=b['output_sha256'] if action=='install' else b['source_sha256']
        if digest(src)!=wanted:raise ValueError('Sight deployment source mismatch')
        plan.append((b,target,src,current,wanted))
    if dry_run:return {'action':action,'dry_run':True,'bundles':[b['bundle'] for b,*_ in plan]}
    if action=='install':check(settings)
    close_game(config);completed=[]
    try:
        for b,target,src,current,wanted in plan:
            if current!=wanted:replace_verified(src,target,current,wanted)
            completed.append((b,target,current,wanted))
    except Exception:
        for b,target,current,wanted in reversed(completed):
            if current!=wanted:replace_verified(Path(b['backup'] if action=='install' else b['output']),target,wanted,current)
        raise
    return {'action':action,'files':[{'bundle':b['bundle'],'sha256':digest(target)} for b,target,*_ in plan],'in_game_tested':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','build','verify','install','restore']);p.add_argument('--config',default='sights.json');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=json.loads(Path(a.config).read_text());c=json.loads(Path(s['base_config']).read_text())
    if a.action=='prepare':
        build_id(c);s['sources']={r:digest(Path(c['bundle_root'])/r) for r in ['root/root','src/weapons/weapons','src/weapons/attachments']}
        Path(a.config).write_text(json.dumps(s,indent=2)+'\n');r={'recorded_baseline':s['sources'],'game_files_changed':False}
    else:r=build(c,s) if a.action=='build' else check(s) if a.action=='verify' else deploy(c,s,a.action,a.dry_run)
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
