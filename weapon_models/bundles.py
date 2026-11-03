"""Add independent visual children and mask only owned weapon renderers."""
import copy,gc,hashlib,json,re,shutil
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from halftone.pipeline import build_id
from catgun.bundle import new_object,mesh_tree,verify_geometry
from deploy_halftone import close_game,replace_verified
from .geometry import make_model as legacy_model,palette as legacy_palette,export_model as legacy_export
from .imported import load as load_authored,export_model as export_authored

def asset_kind(settings,name):
    defaults=json.loads((Path(__file__).resolve().parents[1]/'config/weapon-asset-selections.json').read_text())
    return settings.get('models',{}).get(name,{}).get('asset',defaults[name])

def model_asset(settings,name):
    kind=asset_kind(settings,name)
    if kind=="authored":return load_authored(name)
    if kind=="legacy_procedural":return legacy_model(name),legacy_palette(name),{"title":"Legacy procedural prototype","license":"MIT","author":"MWC"}
    raise ValueError("Unknown model asset source: "+str(kind))

SPECS={
 'scorpion':{'prefix':r'(?i)^cz_scorpion_','roots':['CZ_Scorpion_Base'],'root_count':2},
 'fishing_rod':{'prefix':r'(?i)^kar98k(?:_cm)?_','roots':['Kar98K_CM_Base','Kar98K_Base'],'root_count':3},
 'nail_gun':{'prefix':r'(?i)^mp7_','roots':['MP7_Base'],'root_count':2},
 'toaster':{'prefix':r'(?i)^p90_','roots':['P90_Base'],'root_count':2}}
BUNDLES=('src/weapons/weapons','src/weapons/attachments')


def enabled(settings):
    names=[n for n,v in settings['models'].items() if v.get('enabled',False)]
    if not names or any(n not in SPECS for n in names):raise ValueError('Select at least one known weapon model')
    return names


def local_refs(tree):
    if isinstance(tree,dict):
        if set(tree)>={'m_FileID','m_PathID'} and tree['m_FileID']==0 and tree['m_PathID']:yield tree['m_PathID']
        else:
            for v in tree.values():yield from local_refs(v)
    elif isinstance(tree,(list,tuple)):
        for v in tree:yield from local_refs(v)


def expected_tree(original,change):
    d=copy.deepcopy(original)
    for field,value in change.get('fields',{}).items():d[field]=value
    for child in change.get('children',[]):d['m_Children'].append({'m_FileID':0,'m_PathID':child})
    return d


def verify(settings):
    manifest=json.loads((Path(settings['output'])/'manifest.json').read_text());results=[]
    settings=copy.deepcopy(settings)
    for name,record in manifest['models'].items():
        if 'asset' not in record:settings.setdefault('models',{}).setdefault(name,{})['asset']='legacy_procedural'
    for b in manifest['files']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:raise ValueError('Model artifact/backup hash mismatch')
        A=UnityPy.load(b['backup']);B=UnityPy.load(b['output']);old={key(o.assets_file.name,o.path_id):o for o in A.objects};new={key(o.assets_file.name,o.path_id):o for o in B.objects}
        if set(new)!=set(old)|set(b['added']):raise ValueError('Unexpected model object IDs')
        for oid,obj in old.items():
            if oid in b['changes']:
                if expected_tree(obj.read_typetree(),b['changes'][oid])!=new[oid].read_typetree():raise ValueError('Fields changed outside visual whitelist')
            elif obj.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Unrelated original data changed: '+oid)
        for oid in b['added']:
            obj=new[oid];tree=obj.read_typetree()
            for pid in local_refs(tree):
                if key(obj.assets_file.name,pid) not in new:raise ValueError('Dangling new local reference')
            if oid in b['geometry']:
                name=b['geometry'][oid];verify_geometry(obj,model_asset(settings,name)[0])
            elif obj.type.name=='Mesh' and tree['m_VertexData']['m_VertexCount']!=0:raise ValueError('Masking mesh has visible geometry')
            if obj.type.name=='Texture2D':
                name=b['textures'][oid]
                if not np.array_equal(np.array(obj.read().image.convert('RGB')),np.array(model_asset(settings,name)[1])):raise ValueError('Model palette pixel mismatch')
        results.append({'bundle':b['bundle'],'masked_visual_objects':b['masked'],'new_objects':len(b['added']),
                        'geometry_and_palette_exact_roundtrip':True,'all_new_local_references_resolve':True,'all_other_original_objects_byte_exact':True})
        del A,B,old,new;gc.collect()
    return {'models':manifest['models'],'files':results,'in_game_tested':False}


def build(config,settings):
    build_id(config);names=enabled(settings);out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh model output directory')
    if set(settings.get('sources',{}))!=set(BUNDLES):raise ValueError('Run prepare to record the intended installed baseline first')
    for name in names:
        exporter=legacy_export if asset_kind(settings,name)=='legacy_procedural' else export_authored
        exporter(name,Path(settings['asset_output'])/name)
    result={'models':{n:{'vertices':len(model_asset(settings,n)[0].vertices),'triangles':len(model_asset(settings,n)[0].faces),'enabled':True,'asset':asset_kind(settings,n),'provenance':model_asset(settings,n)[2]} for n in names},'files':[],'in_game_tested':False}
    empty_tree=None
    for relative in BUNDLES:
        source=Path(config['bundle_root'])/relative
        if digest(source)!=settings['sources'][relative]:raise ValueError('Installed baseline changed: '+relative)
        backup=Path(settings['backups'])/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():
            if digest(backup)!=settings['sources'][relative]:raise ValueError('Model backup belongs to another baseline')
        else:shutil.copyfile(source,backup)
        env=UnityPy.load(str(backup));before=inventory(env);expected=copy.deepcopy(before)
        objects={key(o.assets_file.name,o.path_id):o for o in env.objects};original=list(env.objects)
        gos={o.path_id:o.read_typetree() for o in original if o.type.name=='GameObject'}
        if any(g['m_Name'].startswith('MWC_Model_') for g in gos.values()):raise ValueError('Models already present in baseline; restore that layer first')
        changes={};added=[];empties={};geometry={};textures={};masked={n:0 for n in names}
        if relative.endswith('/weapons'):
            empty_obj=next(o for o in original if o.type.name=='Mesh' and o.peek_name()=='GM6_Lynx_Empty');empty_tree=copy.deepcopy(empty_obj.read_typetree())
        for obj in original:
            if obj.type.name not in ('MeshFilter','MeshRenderer','SkinnedMeshRenderer'):continue
            tree=obj.read_typetree();go_name=gos.get(tree['m_GameObject']['m_PathID'],{}).get('m_Name','')
            owner=next((n for n in names if re.match(SPECS[n]['prefix'],go_name)),None)
            if owner is None or re.search(r'(?i)scope|sight|optic|connector',go_name):continue
            fields={}
            if 'm_Mesh' in tree and tree['m_Mesh']['m_PathID']:
                ref=tree['m_Mesh']
                if ref['m_FileID']!=0:raise ValueError('Unexpected external private mesh')
                source_id=key(obj.assets_file.name,ref['m_PathID']);source_mesh=objects[source_id]
                if source_id not in empties:
                    clone=new_object(source_mesh,'MWC-model-mask-'+source_id,objects);d=copy.deepcopy(empty_tree);original_mesh=source_mesh.read_typetree();d['m_Name']='MWC_ModelMask_'+source_mesh.peek_name()
                    for field in ('m_BindPose','m_BoneNameHashes','m_RootBoneNameHash','m_BonesAABB','m_LocalAABB'):d[field]=copy.deepcopy(original_mesh[field])
                    d['m_SubMeshes']=[copy.deepcopy(d['m_SubMeshes'][0]) for _ in original_mesh['m_SubMeshes']]
                    clone.save_typetree(d);empties[source_id]=clone;added.append(key(clone.assets_file.name,clone.path_id))
                fields['m_Mesh']={'m_FileID':0,'m_PathID':empties[source_id].path_id}
            if 'm_Enabled' in tree:fields['m_Enabled']=False
            if fields:
                oid=key(obj.assets_file.name,obj.path_id);changes[oid]={'fields':fields};obj.save_typetree(expected_tree(tree,changes[oid]));masked[owner]+=1
        if relative.endswith('/weapons'):
            # The previously verified Lynx empty-visual node supplies serialization
            # layout only. Each new visual has separate mesh/material/texture IDs.
            go_template=next(o for o in original if o.type.name=='GameObject' and o.peek_name()=='GM6_Lynx_Empty')
            template_go=go_template.read_typetree();parts={objects[key(go_template.assets_file.name,p['component']['m_PathID'])].type.name:objects[key(go_template.assets_file.name,p['component']['m_PathID'])] for p in template_go['m_Component']}
            material_template=next(o for o in original if o.type.name=='Material' and o.peek_name()=='Cheek')
            texture_template=next(o for o in original if o.type.name=='Texture2D')
            transforms=[o for o in original if o.type.name=='Transform']
            for name in names:
                mesh=new_object(empty_obj,'MWC-model-mesh-'+name,objects);mesh.save_typetree(mesh_tree(empty_tree,model_asset(settings,name)[0],'MWC_ModelMesh_'+name));oid=key(mesh.assets_file.name,mesh.path_id);added.append(oid);geometry[oid]=name
                tex_obj=new_object(texture_template,'MWC-model-texture-'+name,objects);tex=tex_obj.read();image=model_asset(settings,name)[1];raw,_=image_to_texture2d(image,4)
                tex.m_Name='MWC_ModelPalette_'+name;tex.m_Width,tex.m_Height=image.size;tex.image_data=raw;tex.m_TextureFormat=4;tex.m_CompleteImageSize=len(raw);tex.m_MipCount=1
                if tex.m_MipMap is not None:tex.m_MipMap=False
                tex.m_ColorSpace=1;tex.m_StreamData.path='';tex.m_StreamData.offset=tex.m_StreamData.size=0;tex.m_TextureSettings.m_FilterMode=1;tex.m_TextureSettings.m_WrapU=tex.m_TextureSettings.m_WrapV=1;tex.save();oid=key(tex_obj.assets_file.name,tex_obj.path_id);added.append(oid);textures[oid]=name
                mat_obj=new_object(material_template,'MWC-model-material-'+name,objects);mat=mat_obj.read();mat.m_Name='MWC_ModelMaterial_'+name
                for slot,entry in mat.m_SavedProperties.m_TexEnvs:entry.m_Texture.m_FileID=0;entry.m_Texture.m_PathID=tex_obj.path_id if slot in ('_BaseMap','_MainTex') else 0
                values={'_Metallic':0,'_Smoothness':.24,'_Glossiness':.24,'_AlphaClip':0,'_Surface':0,'_Cull':2,'_ZWrite':1,'EnableCamo':0,'FlapEnable':0}
                for i,(slot,value) in enumerate(mat.m_SavedProperties.m_Floats):
                    if slot in values:mat.m_SavedProperties.m_Floats[i]=(slot,float(values[slot]))
                for slot,color in mat.m_SavedProperties.m_Colors:
                    if slot in ('_BaseColor','_Color'):color.r=color.g=color.b=color.a=1
                    elif slot=='_EmissionColor':color.r=color.g=color.b=0
                if getattr(mat,'m_ShaderKeywords',None) is not None:mat.m_ShaderKeywords=''
                if getattr(mat,'m_ValidKeywords',None) is not None:mat.m_ValidKeywords=[]
                if getattr(mat,'m_InvalidKeywords',None) is not None:mat.m_InvalidKeywords=[]
                mat.save();added.append(key(mat_obj.assets_file.name,mat_obj.path_id))
                roots=[o for o in transforms if gos[o.read_typetree()['m_GameObject']['m_PathID']]['m_Name'] in SPECS[name]['roots']]
                if len(roots)!=SPECS[name]['root_count']:raise ValueError('Unexpected '+name+' visual-root layout')
                for i,parent in enumerate(roots):
                    label=name+'-'+str(i);new_go=new_object(go_template,'MWC-model-go-'+label,objects);new_t=new_object(parts['Transform'],'MWC-model-transform-'+label,objects);new_r=new_object(parts['MeshRenderer'],'MWC-model-renderer-'+label,objects);new_f=new_object(parts['MeshFilter'],'MWC-model-filter-'+label,objects)
                    gd=copy.deepcopy(template_go);gd['m_Name']='MWC_Model_'+name;gd['m_IsActive']=True;gd['m_Component']=[{'component':{'m_FileID':0,'m_PathID':o.path_id}} for o in [new_t,new_r,new_f]];new_go.save_typetree(gd)
                    td=parts['Transform'].read_typetree();td['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};td['m_Father']={'m_FileID':0,'m_PathID':parent.path_id};td['m_Children']=[];td['m_LocalPosition']={'x':0.,'y':0.,'z':0.};td['m_LocalRotation']={'x':0.,'y':2**-.5,'z':2**-.5,'w':0.};td['m_LocalScale']={'x':1.,'y':1.,'z':1.};new_t.save_typetree(td)
                    rd=parts['MeshRenderer'].read_typetree();rd['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};rd['m_Enabled']=True;rd['m_Materials']=[{'m_FileID':0,'m_PathID':mat_obj.path_id}];new_r.save_typetree(rd)
                    fd=parts['MeshFilter'].read_typetree();fd['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};fd['m_Mesh']={'m_FileID':0,'m_PathID':mesh.path_id};new_f.save_typetree(fd)
                    parent_id=key(parent.assets_file.name,parent.path_id);changes.setdefault(parent_id,{}).setdefault('children',[]).append(new_t.path_id);parent.save_typetree(expected_tree(parent.read_typetree(),{'children':[new_t.path_id]}))
                    added.extend(key(o.assets_file.name,o.path_id) for o in [new_go,new_t,new_r,new_f])
        if any(n==0 for n in masked.values()):raise ValueError('No private renderers found for a selected model')
        for oid in list(changes)+added:
            o=objects[oid];expected[(o.assets_file.name,o.path_id)]={'type':o.type.name,'sha256':hashlib.sha256(o.data).hexdigest()}
        output=out/relative;output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_name(output.name+'.partial');temp.write_bytes(env.file.save(packer='lz4'));del env,objects,original;gc.collect()
        checked=UnityPy.load(str(temp))
        if inventory(checked)!=expected:raise ValueError('Model bundle serialization mismatch')
        del checked;gc.collect();temp.replace(output)
        result['files'].append({'bundle':relative,'backup':str(backup.resolve()),'output':str(output.resolve()),'source_sha256':digest(backup),'output_sha256':digest(output),'changes':changes,'added':added,'masked':masked,'geometry':geometry,'textures':textures});dump(out/'manifest.json',result)
    return verify(settings)


def deploy(config,settings,action,dry_run=False):
    build_id(config);r=json.loads((Path(settings['output'])/'manifest.json').read_text());plan=[]
    for b in r['files']:
        target=Path(config['bundle_root'])/b['bundle'];current=digest(target)
        if current not in (b['source_sha256'],b['output_sha256']):raise ValueError('Unknown installed weapon-model layer; refusing overwrite')
        source=Path(b['output'] if action=='install' else b['backup']);wanted=b['output_sha256'] if action=='install' else b['source_sha256']
        if digest(source)!=wanted:raise ValueError('Model deployment source mismatch')
        plan.append((b,target,source,current,wanted))
    if dry_run:return {'action':action,'dry_run':True,'bundles':[b['bundle'] for b,*_ in plan]}
    if action=='install':verify(settings)
    from installer.mwc_installer.engine import game_running
    if game_running(Path(config['bundle_root']).parents[2]):raise ValueError('Close Combat Master before changing model bundles')
    completed=[]
    try:
        for b,target,source,current,wanted in plan:
            if current!=wanted:replace_verified(source,target,current,wanted)
            completed.append((b,target,current,wanted))
    except Exception:
        for b,target,current,wanted in reversed(completed):
            if current!=wanted:replace_verified(Path(b['backup'] if action=='install' else b['output']),target,wanted,current)
        raise
    result={'action':action,'files':[{'bundle':b['bundle'],'sha256':digest(target)} for b,target,*_ in plan],'in_game_tested':False};dump(Path(settings['output'])/'deployment.json',result);return result
