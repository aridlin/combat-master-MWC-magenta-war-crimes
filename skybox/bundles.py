"""Clone sky-only textures and rebind only explicitly reviewed sky materials.

Original textures stay byte-exact so existing reflection/lighting references do
not acquire the replacement image. Scene RenderSettings and lights are untouched.
"""
import copy,gc,hashlib,json,shutil
from pathlib import Path
import UnityPy
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest,inventory
from halftone.assets import key,pointer,dump
from halftone.pipeline import build_id
from catgun.bundle import new_object
from .pixels import faces,NAMES
TARGETS={
 'src/maps/maps':['Skybox_v2_BR','Skybox','mossymountains'],
 'src/maps/brmap_oilplatforms_s':['Mat_Skybox_Sunset_BR','skybox_day_BR'],
 'src/maps/map_depot_s':['Skybox_Depot'],
 'src/maps/map_drains_s':['Skybox_drains'],
 'src/maps/map_warehouse_s':['skybox_day'],
 'src/maps/map_electro_s':['farmsky'],
 'src/maps/map_museum_s':['museum_sky'],
 'src/maps/map_talencecm_s':['autumn_field_4k']}

# Unity's six-sided labels are viewed from inside the sky: Left is +X.
# https://docs.unity.com/en-us/engine/6000.3/manual/creating-environments/sky/skybox-material-reference/shader-skybox-6sided
FACE_SLOTS={'_LeftTex':0,'_RightTex':1,'_UpTex':2,'_DownTex':3,'_FrontTex':4,'_BackTex':5}


def texture_slots(tree):
    slots=[name for name,value in tree['m_SavedProperties']['m_TexEnvs']]
    if slots==['_Tex']:return {'_Tex':None}
    if len(slots)==6 and set(slots)==set(FACE_SLOTS):return FACE_SLOTS.copy()
    raise ValueError('Unsupported or ambiguous sky texture layout: '+tree['m_Name'])


def encoded(size,night,face=None):
    images=faces(size,night)
    return b''.join(image_to_texture2d(image,4)[0] for image in (images if face is None else [images[face]]))

def verify(settings):
    manifest=json.loads((Path(settings['output'])/'manifest.json').read_text());declared={x['new_id']:x for b in manifest['files'] for x in b['clones']};count=0;face_materials=0;face_textures=0
    for b in manifest['files']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:raise ValueError('Sky artifact hash mismatch')
        A=UnityPy.load(b['backup']);B=UnityPy.load(b['output']);old={key(o.assets_file.name,o.path_id):o for o in A.objects};new={key(o.assets_file.name,o.path_id):o for o in B.objects};clones={r['new_id']:r for r in b['clones']};edits={r['id']:r for r in b['changes']}
        if set(new)!=set(old)|set(clones):raise ValueError('Unexpected sky object set')
        for oid,o in old.items():
            if oid not in edits:
                if o.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Unrelated lighting/environment object changed: '+oid)
            else:
                want=o.read_typetree();layout=texture_slots(want);sources={slot:pointer(value.m_Texture,o.assets_file) for slot,value in o.read().m_SavedProperties.m_TexEnvs}
                bindings=edits[oid].get('bindings',[{'slot':'_Tex','new_pointer':edits[oid].get('new_pointer')}])
                if {r['slot'] for r in bindings}!=set(layout) or len(bindings)!=len(layout):raise ValueError('Incomplete sky texture bindings')
                for binding in bindings:
                    matches=[v for slot,v in want['m_SavedProperties']['m_TexEnvs'] if slot==binding['slot']]
                    if len(matches)!=1:raise ValueError('Ambiguous sky texture binding')
                    if 'old_pointer' in binding and matches[0]['m_Texture']!=binding['old_pointer']:raise ValueError('Original sky binding changed')
                    matches[0]['m_Texture']=binding['new_pointer']
                if want!=new[oid].read_typetree():raise ValueError('Sky change outside texture pointer')
                for slot,value in new[oid].read().m_SavedProperties.m_TexEnvs:
                    reference=pointer(value.m_Texture,new[oid].assets_file)
                    if reference not in declared:raise ValueError('Sky binding does not resolve to declared cloned texture')
                    if declared[reference]['source_id']!=sources[slot] or declared[reference].get('face')!=layout[slot]:raise ValueError('Sky texture bound to the wrong source or directional face')
                face_materials+=int(len(layout)==6)
        for oid,r in clones.items():
            t=new[oid].read_typetree();size=settings.get('size',256);raw=t['image data'];stride=size*size*4
            face=r.get('face');image_count=6 if face is None else 1;expected_type='Cubemap' if face is None else 'Texture2D'
            if new[oid].type.name!=expected_type or len(raw)!=stride*image_count or t['m_ImageCount']!=image_count or t['m_TextureFormat']!=4 or t['m_Width']!=size or t['m_Height']!=size or t['m_MipCount']!=1:raise ValueError('Invalid sky texture layout')
            if bytes(raw)!=encoded(size,r['night'],face):raise ValueError('Sky face bytes mismatch')
            face_textures+=int(face is not None)
            original=old[r['source_id']]
            if original.get_raw_data()!=new[r['source_id']].get_raw_data():raise ValueError('Original sky/reflection texture was edited')
        count+=len(edits);del A,B,old,new;gc.collect()
    return {'sky_materials':count,'six_sided_materials':face_materials,'cloned_2d_faces':face_textures,'original_cubemaps_lights_scene_settings_geometry_and_non_sky_objects_byte_exact':True,'original_sky_2d_textures_byte_exact':True,'in_game_tested':False,'lighting_runtime_behavior_tested':False}

def build(config,settings):
    build_id(config);out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh sky output directory')
    root=Path(config['bundle_root']);envs={};object_index={};before={};paths={};clone_requests={};bindings=[]
    for rel in TARGETS:
        source=root/rel
        if digest(source)!=settings['sources'][rel]:raise ValueError('Sky source changed: '+rel)
        backup=Path(settings['backups'])/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():
            if digest(backup)!=settings['sources'][rel]:raise ValueError('Sky backup belongs to another baseline: '+rel)
        else:shutil.copyfile(source,backup)
        env=UnityPy.load(str(backup));envs[rel]=env;before[rel]=inventory(env);paths[rel]=backup
        for o in env.objects:object_index[key(o.assets_file.name,o.path_id)]=(rel,o)
    for rel,names in TARGETS.items():
        for name in names:
            found=[o for o in envs[rel].objects if o.type.name=='Material' and o.peek_name()==name]
            if len(found)!=1:raise ValueError('Sky material missing or ambiguous: '+rel+'/'+name)
            o=found[0];layout=texture_slots(o.read_typetree())
            for slot,value in o.read().m_SavedProperties.m_TexEnvs:
                reference=pointer(value.m_Texture,o.assets_file);face=layout[slot];expected_type='Cubemap' if face is None else 'Texture2D';night='night' in name.lower();request=(reference,face,night)
                if reference not in object_index or object_index[reference][1].type.name!=expected_type:raise ValueError('Unresolved sky '+expected_type+': '+str(reference))
                clone_requests[request]=True;bindings.append((rel,o,slot,request))
    clones={};reports={rel:{'bundle':rel,'backup':str(paths[rel].resolve()),'changes':[],'clones':[]} for rel in TARGETS}
    for source_id,face,night in clone_requests:
        rel,o=object_index[source_id];objects={key(x.assets_file.name,x.path_id):x for x in envs[rel].objects};label='MWC-minecraft-sky-'+source_id+('' if face is None else ':face='+str(face))+(':night' if night else '');new=new_object(o,label,objects);t=copy.deepcopy(o.read_typetree());size=settings.get('size',256)
        raw=encoded(size,night,face)
        t.update(m_Name='MWC_MinecraftSky_'+o.peek_name(),m_Width=size,m_Height=size,m_CompleteImageSize=size*size*4,m_TextureFormat=4,m_MipCount=1,m_StreamingMipmaps=False,m_ColorSpace=1)
        t['image data']=raw;t['m_StreamData']={'offset':0,'size':0,'path':''};t['m_TextureSettings']['m_FilterMode']=0;new.save_typetree(t)
        clones[(source_id,face,night)]=new.path_id
        reports[rel]['clones'].append({'source_id':source_id,'new_id':key(new.assets_file.name,new.path_id),'night':night,'face':face})
    grouped={}
    for rel,o,slot_name,request in bindings:
        oid=key(o.assets_file.name,o.path_id);grouped.setdefault(oid,[]).append((rel,o,slot_name,request))
    for oid,group in grouped.items():
        rel,o=group[0][:2];tree=o.read_typetree();edit={'id':oid,'name':o.peek_name(),'bindings':[]}
        for _,_,slot_name,request in group:
            slot=next(v for slot,v in tree['m_SavedProperties']['m_TexEnvs'] if slot==slot_name);old=copy.deepcopy(slot['m_Texture']);slot['m_Texture']['m_PathID']=clones[request]
            edit['bindings'].append({'slot':slot_name,'old_pointer':old,'new_pointer':copy.deepcopy(slot['m_Texture'])})
        o.save_typetree(tree);reports[rel]['changes'].append(edit)
    result={'files':[],'in_game_tested':False}
    for rel,env in envs.items():
        expected=copy.deepcopy(before[rel]);r=reports[rel]
        for o in env.objects:
            if o.data is not None:expected[(o.assets_file.name,o.path_id)]={'type':o.type.name,'sha256':hashlib.sha256(o.data).hexdigest()}
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='lz4'));check=UnityPy.load(str(target))
        if inventory(check)!=expected:raise ValueError('Sky serialized inventory mismatch')
        r.update(output=str(target.resolve()),source_sha256=digest(paths[rel]),output_sha256=digest(target));result['files'].append(r)
    dump(out/'manifest.json',result)
    for name,image in zip(NAMES,faces(settings.get('size',256))):image.save(out/(name+'.png'))
    del envs,object_index;gc.collect();return verify(settings)
