"""Clone sky-only cubemaps and rebind only explicitly named sky materials.

Original cubemaps stay byte-exact so existing reflection/lighting references do
not acquire the replacement image. Scene RenderSettings and lights are untouched.
"""
import copy,gc,hashlib,json,shutil
from pathlib import Path
import UnityPy
from UnityPy.export.Texture2DConverter import image_to_texture2d,parse_image_data
from bundle_utils import digest,inventory
from halftone.assets import key,pointer,dump
from halftone.pipeline import build_id
from catgun.bundle import new_object
from .pixels import faces,NAMES
TARGETS={
 'src/maps/maps':['Skybox_v2_BR','Skybox'],
 'src/maps/brmap_oilplatforms_s':['Mat_Skybox_Sunset_BR','skybox_day_BR'],
 'src/maps/map_depot_s':['Skybox_Depot'],
 'src/maps/map_drains_s':['Skybox_drains'],
 'src/maps/map_warehouse_s':['skybox_day']}

def verify(settings):
    manifest=json.loads((Path(settings['output'])/'manifest.json').read_text());declared={x['new_id'] for b in manifest['files'] for x in b['clones']};count=0
    for b in manifest['files']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:raise ValueError('Sky artifact hash mismatch')
        A=UnityPy.load(b['backup']);B=UnityPy.load(b['output']);old={key(o.assets_file.name,o.path_id):o for o in A.objects};new={key(o.assets_file.name,o.path_id):o for o in B.objects};clones={r['new_id']:r for r in b['clones']};edits={r['id']:r for r in b['changes']}
        if set(new)!=set(old)|set(clones):raise ValueError('Unexpected sky object set')
        for oid,o in old.items():
            if oid not in edits:
                if o.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Unrelated lighting/environment object changed: '+oid)
            else:
                want=o.read_typetree();matches=[v for slot,v in want['m_SavedProperties']['m_TexEnvs'] if slot=='_Tex']
                if len(matches)!=1:raise ValueError('Ambiguous sky texture binding')
                matches[0]['m_Texture']=edits[oid]['new_pointer']
                if want!=new[oid].read_typetree():raise ValueError('Sky change outside texture pointer')
                if pointer(new[oid].read().m_SavedProperties.m_TexEnvs[0][1].m_Texture,new[oid].assets_file) not in declared:raise ValueError('Sky binding does not resolve to declared cloned texture')
        for oid,r in clones.items():
            t=new[oid].read_typetree();size=settings.get('size',256);raw=t['image data'];stride=size*size*4
            if len(raw)!=stride*6 or t['m_ImageCount']!=6 or t['m_TextureFormat']!=4:raise ValueError('Invalid sky cubemap layout')
            for i,image in enumerate(faces(size,r['night'])):
                expected,_=image_to_texture2d(image,4)
                if bytes(raw[i*stride:(i+1)*stride])!=expected:raise ValueError('Sky face bytes mismatch')
            original=old[r['source_id']]
            if original.get_raw_data()!=new[r['source_id']].get_raw_data():raise ValueError('Original lighting cubemap was edited')
        count+=len(edits);del A,B,old,new;gc.collect()
    return {'sky_materials':count,'original_cubemaps_lights_scene_settings_geometry_and_non_sky_objects_byte_exact':True,'in_game_tested':False,'lighting_runtime_behavior_tested':False}

def build(config,settings):
    build_id(config);out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh sky output directory')
    root=Path(config['bundle_root']);envs={};object_index={};before={};paths={};clone_requests={};bindings=[]
    for rel in TARGETS:
        source=root/rel
        if digest(source)!=settings['sources'][rel]:raise ValueError('Sky source changed: '+rel)
        backup=Path(settings['backups'])/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():raise ValueError('Sky backup already exists')
        shutil.copyfile(source,backup);env=UnityPy.load(str(backup));envs[rel]=env;before[rel]=inventory(env);paths[rel]=backup
        for o in env.objects:object_index[key(o.assets_file.name,o.path_id)]=(rel,o)
    for rel,names in TARGETS.items():
        for name in names:
            found=[o for o in envs[rel].objects if o.type.name=='Material' and o.peek_name()==name]
            if len(found)!=1:raise ValueError('Sky material missing or ambiguous: '+rel+'/'+name)
            o=found[0];textures=[value for slot,value in o.read().m_SavedProperties.m_TexEnvs if slot=='_Tex']
            if len(textures)!=1:raise ValueError('Unsupported sky shader: '+name)
            reference=pointer(textures[0].m_Texture,o.assets_file)
            if reference not in object_index or object_index[reference][1].type.name!='Cubemap':raise ValueError('Unresolved sky cubemap: '+str(reference))
            clone_requests[reference]='night' in name.lower();bindings.append((rel,o,reference))
    clones={};reports={rel:{'bundle':rel,'backup':str(paths[rel].resolve()),'changes':[],'clones':[]} for rel in TARGETS}
    for source_id,night in clone_requests.items():
        rel,o=object_index[source_id];objects={key(x.assets_file.name,x.path_id):x for x in envs[rel].objects};new=new_object(o,'MWC-minecraft-sky-'+source_id,objects);t=copy.deepcopy(o.read_typetree());size=settings.get('size',256)
        raw=b''.join(image_to_texture2d(image,4)[0] for image in faces(size,night))
        t.update(m_Name='MWC_MinecraftSky_'+o.peek_name(),m_Width=size,m_Height=size,m_CompleteImageSize=size*size*4,m_TextureFormat=4,m_MipCount=1,m_StreamingMipmaps=False,m_ColorSpace=1)
        t['image data']=raw;t['m_StreamData']={'offset':0,'size':0,'path':''};t['m_TextureSettings']['m_FilterMode']=0;new.save_typetree(t);clones[source_id]=new.path_id
        reports[rel]['clones'].append({'source_id':source_id,'new_id':key(new.assets_file.name,new.path_id),'night':night})
    for rel,o,source_id in bindings:
        tree=o.read_typetree();slot=next(v for slot,v in tree['m_SavedProperties']['m_TexEnvs'] if slot=='_Tex');old=copy.deepcopy(slot['m_Texture']);slot['m_Texture']['m_PathID']=clones[source_id];o.save_typetree(tree)
        reports[rel]['changes'].append({'id':key(o.assets_file.name,o.path_id),'name':o.peek_name(),'old_pointer':old,'new_pointer':copy.deepcopy(slot['m_Texture'])})
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
