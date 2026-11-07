"""Replace only the resolved impact grenade's held/thrown visual bindings.

Its thrown mesh is shared with a launcher, so the original mesh is never edited.
No collider, projectile component, weapon stats, transform or animation changes.
"""
import copy,gc,hashlib,json
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from halftone.pipeline import build_id,safe_output
from catgun.bundle import new_object,mesh_tree,verify_geometry
from operators.bundles import material,geometry_check
from operators.bounds import root_bounds
from operators.material_data import create as neutral_maps,verify as verify_material
from operators.skinning import skinned_tree
from weapon_models.bundles import local_refs
from weapon_models.imported import load

ROOT=Path(__file__).resolve().parent
BUNDLE='src/weapons/weapons'


def translated(mesh,center):
    result=copy.deepcopy(mesh);result.vertices=(np.asarray(mesh.vertices)+np.asarray(center)).astype('<f4').tolist();return result


def build(config,settings):
    targets=json.loads((ROOT/'config/sonic-impact-targets.json').read_text())
    if str(build_id(config))!=targets['build_id']:raise ValueError('Impact target index belongs to a different game build')
    source=Path(config['bundle_root'])/BUNDLE
    if digest(source)!=settings['source_sha256']:raise ValueError('Impact grenade baseline changed')
    output=safe_output(settings['output'],config);backup=safe_output(settings['backups'],config)/BUNDLE
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh Sonic build directory')
    from installer.mwc_installer.engine import copy_private
    if backup.exists():
        if digest(backup)!=settings['source_sha256']:raise ValueError('Sonic backup belongs to another baseline')
    else:copy_private(source,backup)
    mesh,image,provenance=load('sonic_impact');env=UnityPy.load(str(backup));original=list(env.objects);before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in original};byid={o.path_id:o for o in original};changes={};added=[];geometry={}
    for row in targets['targets']:
        obj=byid[int(row['path_id'])]
        if obj.type.name!=row['type'] or digest_bytes(obj.get_raw_data())!=row['sha256'] or str(obj.read_typetree()['m_GameObject']['m_PathID'])!=row['game_object']:raise ValueError('Impact visual target changed: '+row['path_id'])
    donor=byid[3810939752448050823].read_typetree();material_template=byid[donor['m_Materials'][0]['m_PathID']];texture_template=next(o for o in original if o.type.name=='Texture2D' and o.assets_file is material_template.assets_file);data_maps=neutral_maps(texture_template,objects,weapon_mode=True)
    added.extend(key(o.assets_file.name,o.path_id) for o in data_maps.values());tex_obj=new_object(texture_template,'MWC_SonicImpactAlbedo',objects);tex=tex_obj.read();raw,_=image_to_texture2d(image.convert('RGBA'),4);tex.m_Name='MWC_SonicImpactAlbedo';tex.m_Width,tex.m_Height=image.size;tex.m_TextureFormat=4;tex.image_data=raw;tex.m_CompleteImageSize=len(raw);tex.m_MipCount=1
    if tex.m_MipMap is not None:tex.m_MipMap=False
    tex.m_ColorSpace=1;tex.m_StreamData.path='';tex.m_StreamData.offset=tex.m_StreamData.size=0;tex.m_TextureSettings.m_FilterMode=1;tex.m_TextureSettings.m_WrapU=tex.m_TextureSettings.m_WrapV=1;tex.save();added.append(key(tex_obj.assets_file.name,tex_obj.path_id));mat=material(material_template,objects,'MWC_SonicImpactMaterial',tex_obj.path_id,data_maps=data_maps);added.append(key(mat.assets_file.name,mat.path_id))
    for row in targets['targets']:
        obj=byid[int(row['path_id'])];tree=obj.read_typetree();fields={}
        if obj.assets_file is not material_template.assets_file:raise ValueError('Impact visual needs an explicit external asset reference')
        if obj.type.name in ('SkinnedMeshRenderer','MeshFilter'):
            pointer=tree['m_Mesh']
            if pointer['m_FileID']:raise ValueError('Expected a local impact visual mesh')
            template=byid[pointer['m_PathID']];native=template.read_typetree();fitted=translated(mesh,targets['held_center' if row['role']=='held' else 'thrown_center']);new=new_object(template,'MWC_SonicImpactMesh_'+row['path_id'],objects)
            if obj.type.name=='SkinnedMeshRenderer':
                if len(tree['m_Bones'])!=1 or len(native['m_BindPose'])!=1 or tree['m_RootBone']!=tree['m_Bones'][0]:raise ValueError('Unreviewed held impact rig')
                bi=np.zeros((len(fitted.vertices),4),dtype='u1');bw=np.zeros((len(fitted.vertices),4),dtype='<f4');bw[:,0]=1;md=skinned_tree(native,fitted,'MWC_SonicImpactHeld',bi,bw,1);bind=np.asarray([[[p['e'+str(i)+str(j)] for j in range(4)] for i in range(4)] for p in native['m_BindPose']]);fields.update(m_Materials=[{'m_FileID':0,'m_PathID':mat.path_id}],m_AABB=root_bounds(fitted.vertices,bind,0,tree['m_AABB']));geometry[new.path_id]=(fitted,bi,bw)
            else:
                md=mesh_tree(native,fitted,'MWC_SonicImpactThrown');md['m_BindPose']=[];md['m_BoneNameHashes']=[];md['m_RootBoneNameHash']=0;md['m_BonesAABB']=[];geometry[new.path_id]=(fitted,None,None)
                if 'm_Skin' in md:md['m_Skin']=[]
                if 'm_VariableBoneCountWeights' in md:md['m_VariableBoneCountWeights']={k:([] if isinstance(v,list) else b'' if isinstance(v,bytes) else v) for k,v in md['m_VariableBoneCountWeights'].items()}
            new.save_typetree(md);added.append(key(new.assets_file.name,new.path_id));fields['m_Mesh']={'m_FileID':0,'m_PathID':new.path_id}
        else:fields['m_Materials']=[{'m_FileID':0,'m_PathID':mat.path_id}]
        changed=copy.deepcopy(tree);changed.update(fields);obj.save_typetree(changed);changes[key(obj.assets_file.name,obj.path_id)]=fields
    expected=copy.deepcopy(before)
    for oid in list(changes)+added:
        obj=objects[oid];expected[(obj.assets_file.name,obj.path_id)]={'type':obj.type.name,'sha256':digest_bytes(obj.data if obj.data is not None else obj.get_raw_data())}
    target=output/BUNDLE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(target));new={key(o.assets_file.name,o.path_id):o for o in checked.objects};local={o.path_id:o for o in checked.objects}
    if inventory(checked)!=expected:raise ValueError('Sonic serialized inventory exceeded the visual whitelist')
    old=UnityPy.load(str(backup));untouched=0
    for obj in old.objects:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid in changes:
            tree=obj.read_typetree();tree.update(changes[oid])
            if tree!=new[oid].read_typetree():raise ValueError('Sonic changed fields outside its visual whitelist')
        else:
            if obj.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Sonic changed an unrelated original asset')
            untouched+=1
    for oid in added:
        obj=new[oid]
        for pid in local_refs(obj.read_typetree()):
            if key(obj.assets_file.name,pid) not in new:raise ValueError('Sonic has an unresolved local reference')
    for pid,(fitted,bi,bw) in geometry.items():
        if bi is None:verify_geometry(local[pid],fitted)
        else:geometry_check(local[pid],fitted,bi,bw)
    if not np.array_equal(np.asarray(local[tex_obj.path_id].read().image.convert('RGB')),np.asarray(image)):raise ValueError('Sonic albedo did not roundtrip')
    verify_material(local[mat.path_id],local,require_albedo=True,weapon_mode=True)
    report={'build_id':targets['build_id'],'model':'sonic_impact','source':provenance,'files':[{'bundle':BUNDLE,'backup':str(backup.resolve()),'output':str(target.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target),'changes':changes,'added':added}],'verification':{'exact_visual_objects_changed':len(changes),'all_other_original_objects_byte_exact':untouched,'geometry_skin_material_texture_roundtrip':True,'shared_launcher_mesh_unchanged':True,'all_new_local_references_resolve':True,'transforms_scripts_collision_physics_animation_stats_unchanged':True},'in_game_tested':False,'sounds_replaced':False};dump(output/'manifest.json',report);return report


def digest_bytes(data):return hashlib.sha256(data).hexdigest()
