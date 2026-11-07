"""Build exact, isolated operator visual replacements into a private bundle.

Only owned SkinnedMeshRenderer mesh/material/bounds fields change. Skeletons,
Animator/LOD components, scripts, collision and all other operators stay exact.
"""
import copy,gc,hashlib,json,shutil
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest,inventory
from catgun.bundle import new_object,mesh_tree
from catgun.geometry import Mesh
from halftone.assets import key,dump
from halftone.pipeline import build_id,safe_output
from weapon_models.bundles import local_refs
from .assignments import validate
from .native import native_rig
from .profiles import profile
from .retarget import adapt,native_frame
from .skinning import skinned_tree,validate_weights
from .assets import load
from .bounds import root_bounds

ROOT=Path(__file__).resolve().parents[1]
BUNDLE='src/thrid_person'


def texture(template,objects,label,image,*,nearest=False):
    obj=new_object(template,label,objects);tex=obj.read();raw,_=image_to_texture2d(image,4)
    tex.m_Name=label;tex.m_Width,tex.m_Height=image.size;tex.image_data=raw;tex.m_TextureFormat=4;tex.m_CompleteImageSize=len(raw);tex.m_MipCount=1
    if tex.m_MipMap is not None:tex.m_MipMap=False
    tex.m_ColorSpace=1;tex.m_StreamData.path='';tex.m_StreamData.offset=tex.m_StreamData.size=0
    tex.m_TextureSettings.m_FilterMode=0 if nearest else 1;tex.m_TextureSettings.m_WrapU=tex.m_TextureSettings.m_WrapV=1;tex.save()
    return obj


def material(template,objects,label,texture,rgba=(1.,1.,1.,1.),alpha_clip=False,transparent=False,data_maps=None):
    obj=new_object(template,label,objects);m=obj.read();m.m_Name=label
    for slot,value in m.m_SavedProperties.m_TexEnvs:
        value.m_Texture.m_FileID=0;value.m_Texture.m_PathID=texture if slot in ('_BaseMap','_MainTex','Albedo') else data_maps['metallic'].path_id if data_maps and slot in ('_MetallicGlossMap','_SpecGlossMap','Metallic') else data_maps['normal'].path_id if data_maps and slot in ('_BumpMap','Normal') else 0;value.m_Scale.x=value.m_Scale.y=1;value.m_Offset.x=value.m_Offset.y=0
    if data_maps:
        present={slot for slot,value in m.m_SavedProperties.m_TexEnvs}
        for slot,role in [('_MetallicGlossMap','metallic'),('_BumpMap','normal')]:
            if slot in present:continue
            value=copy.copy(m.m_SavedProperties.m_TexEnvs[0][1]);value.m_Texture=copy.copy(value.m_Texture);value.m_Texture.m_FileID=0;value.m_Texture.m_PathID=data_maps[role].path_id;m.m_SavedProperties.m_TexEnvs.append((slot,value))
    values={'_Metallic':0.,'Smoothness':.45 if transparent else .12,'_Smoothness':.45 if transparent else .12,'_Glossiness':.45 if transparent else .12,'_BumpScale':0.,'_AlphaClip':float(alpha_clip),'_Alpha_Clip_Threshold':.35 if alpha_clip else 0.,'_Cutoff':.35,'_AlphaToMask':0.,'_Surface':float(transparent),'_Blend':0.,'_SrcBlend':5. if transparent else 1.,'_DstBlend':10. if transparent else 0.,'_SrcBlendAlpha':1.,'_DstBlendAlpha':10. if transparent else 0.,'_ZWrite':0. if transparent else 1.,'_Cull':0. if transparent else 2.,'EnableCamo':0.,'TintCamo':0.,'FlapEnable':0.}
    seen=set()
    for i,(slot,value) in enumerate(m.m_SavedProperties.m_Floats):
        if slot in values:m.m_SavedProperties.m_Floats[i]=(slot,values[slot]);seen.add(slot)
    for slot in sorted(values.keys()-seen):m.m_SavedProperties.m_Floats.append((slot,values[slot]))
    for slot,c in m.m_SavedProperties.m_Colors:
        if slot in ('_BaseColor','_Color','AlbedoColor'):c.r,c.g,c.b,c.a=rgba
        if slot=='_EmissionColor':c.r=c.g=c.b=0
    keywords=['_SURFACE_TYPE_TRANSPARENT'] if transparent else ['_ALPHATEST_ON'] if alpha_clip else []
    if getattr(m,'m_ShaderKeywords',None) is not None:m.m_ShaderKeywords=' '.join(keywords)
    if getattr(m,'m_ValidKeywords',None) is not None:m.m_ValidKeywords=keywords
    if getattr(m,'m_InvalidKeywords',None) is not None:m.m_InvalidKeywords=[]
    m.m_CustomRenderQueue=3000 if transparent else 2450 if alpha_clip else -1
    m.save();return obj


def combine(parts):
    result=Mesh();indices=[];weights=[];ranges=[]
    for mesh,bi,bw in parts:
        start=len(result.vertices);first=len(result.faces)*6;v,n,uv,f=mesh.arrays();result.vertices.extend(v.tolist());result.normals.extend(n.tolist());result.uv.extend(uv.tolist());result.faces.extend((f+start).tolist());indices.extend(bi.tolist());weights.extend(bw.tolist())
        center=(v.min(0)+v.max(0))/2;extent=(v.max(0)-v.min(0))/2
        ranges.append({'firstByte':first,'indexCount':int(f.size),'topology':0,'baseVertex':0,'firstVertex':start,'vertexCount':len(v),'localAABB':{'m_Center':dict(zip('xyz',map(float,center))),'m_Extent':dict(zip('xyz',map(float,extent)))}})
    if len(result.vertices)>65535:raise ValueError('Combined operator exceeds uint16 mesh writer; partition explicitly')
    return result,np.asarray(indices,dtype='u1'),np.asarray(weights,dtype='<f4'),ranges


def empty_visual(template):
    m=Mesh();m.vertices=[[0.,0.,0.]];m.normals=[[0.,0.,1.]];m.uv=[[.5,.5]]
    d=mesh_tree(template,m,'MWC_OperatorMask_'+template['m_Name']);d['m_VertexData']['m_VertexCount']=0;d['m_VertexData']['m_DataSize']=b''
    d['m_SubMeshes']=[{**copy.deepcopy(d['m_SubMeshes'][0]),'vertexCount':0} for _ in template['m_SubMeshes']]
    return d


def geometry_check(obj,mesh,indices,weights):
    h=MeshHandler(obj.read());h.process();v,n,uv,f=mesh.arrays()
    for actual,expected,label in [(h.m_Vertices,v,'positions'),(h.m_Normals,n,'normals'),(np.asarray(h.m_UV0)[:,:2],uv,'UV'),(h.m_BoneIndices,indices,'skin indices'),(h.m_BoneWeights,weights,'skin weights')]:
        if not np.array_equal(np.asarray(actual,dtype=np.asarray(expected).dtype),expected):raise ValueError('Operator '+label+' did not round-trip')
    actual=np.concatenate([np.asarray(x,dtype='<u4').reshape(-1,3) for x in h.get_triangles()])
    if not np.array_equal(actual,f):raise ValueError('Operator submesh triangles did not round-trip')


def build(config,settings):
    version=build_id(config);assignments=validate(settings['assignments'])
    if not assignments:raise ValueError('Choose at least one operator replacement')
    first_person=bool(settings.get('first_person',False));bundle='src/first_person' if first_person else BUNDLE
    source=Path(config['bundle_root'])/bundle
    if digest(source)!=settings['source_sha256']:raise ValueError('Operator baseline changed')
    output=safe_output(settings['output'],config);backup=safe_output(settings['backups'],config)/bundle
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh operator build directory')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        if digest(backup)!=settings['source_sha256']:raise ValueError('Operator backup belongs to another baseline')
    else:
        from installer.mwc_installer.engine import copy_private
        copy_private(source,backup)
    env=UnityPy.load(str(backup));original=list(env.objects);before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in original};allowed={};added=[];expected_geometry={};records=[];cached={};completed_prefabs={}
    targets={t['id']:t for t in json.loads((ROOT/('config/operator-first-person-targets.json' if first_person else 'config/operator-targets.json')).read_text())['operators']}
    if first_person:
        from .first_person import validate_assignments
        validate_assignments(assignments,list(targets.values()))
    texture_template=next(o for o in original if o.type.name=='Texture2D')
    from .material_data import create as neutral_maps
    data_maps=neutral_maps(texture_template,objects);added.extend(key(o.assets_file.name,o.path_id) for o in data_maps.values())
    from .lods import select_source,load_lod
    def prepared(model,spec,directory,reference=None):
        model_key=(model,spec['profile'],spec.get('style','original'),str(directory.resolve()),str(reference.resolve()) if reference else None)
        if model_key not in cached:
            base,image,si,sw,meta=(load_lod(directory,reference,spec.get('style','original'),config) if reference else load(directory,spec.get('style','original'),config))
            data=np.load(directory/'source.npz',allow_pickle=False);options=profile(spec['profile'],meta);cached[model_key]=(base,image,si,sw,meta,data,options)
        return cached[model_key]
    for identifier,model in assignments.items():
        if model not in settings['library']:raise ValueError('Model source is not available locally: '+model)
        spec=settings['library'][model];directory=Path(spec.get('first_person_source',spec['source']) if first_person else spec['source']);target=targets[identifier]
        if first_person and target['prefab_guid'] in completed_prefabs:
            record=copy.deepcopy(completed_prefabs[target['prefab_guid']]);record.update(operator=identifier,name=target['name'],shared_prefab=True);records.append(record);continue
        rig=native_rig(env,target,first_person=first_person)
        base,image,si,sw,meta,data,options=prepared(model,spec,directory)
        tex_obj=texture(texture_template,objects,'MWC_OperatorTexture_'+identifier,image,nearest=meta.get('texture_filter')=='nearest');added.append(key(tex_obj.assets_file.name,tex_obj.path_id))
        primary=set(rig['primary'].values());donor=rig['snapshots'][rig['primary'][min(rig['primary'])]];pointer=donor['renderer']['m_Materials'][0]
        from .body_material import template as body_template
        material_template,material_record=body_template(rig['objects'],pointer,first_person=first_person)
        body_mat=material(material_template,objects,'MWC_OperatorMaterial_'+identifier,tex_obj.path_id,alpha_clip=meta['alpha_clip_required'],data_maps=data_maps);added.append(key(body_mat.assets_file.name,body_mat.path_id));frame_mat=lens_mat=None
        if spec.get('glasses') and not first_person:
            from .lenses import template as lens_template,configure as configure_lens
            frame_mat=material(material_template,objects,'MWC_OperatorFrame_'+identifier,0,(.012,.016,.020,1.),data_maps=data_maps);lens_mat=configure_lens(material(lens_template(rig['objects']),objects,'MWC_OperatorRustShield_'+identifier,0,(.32,.095,.035,.40),transparent=True,data_maps=data_maps));added.extend(key(o.assets_file.name,o.path_id) for o in (frame_mat,lens_mat))
        model_records=[];lod_materials={}
        for rid,tree in rig['renderers'].items():
            template=rig['meshes'][rid];new_mesh=new_object(template,'MWC_OperatorMesh_'+identifier+'_'+str(rid),objects)
            fields={}
            if rid in primary:
                native=rig['snapshots'][rid];lod_record={};part_material=body_mat.path_id
                if first_person:
                    from .first_person import fit as fit_arms
                    mesh,bi,bw,fit_report=fit_arms(base,si,sw,meta,data['inverse_bind'],native,options,model=model)
                else:
                    levels=sorted(level for level,renderer in rig['primary'].items() if renderer==rid)
                    part_directory,source_lod,reference=select_source(spec,levels)
                    part,part_image,psi,psw,pm,pd,po=prepared(model,spec,part_directory,reference)
                    if reference and pm.get('source_lod')!=source_lod:raise ValueError('Authored LOD identity does not match the selected level')
                    shared=part_image.size==image.size and part_image.tobytes()==image.tobytes()
                    if not shared:
                        if not reference or pm.get('shared_lod0_atlas') is not False or pm.get('independent_lod_atlas_reason')!='authored_uv_extent':raise ValueError('Unexpected operator LOD material atlas difference')
                        if source_lod not in lod_materials:
                            lod_tex_obj=texture(texture_template,objects,'MWC_OperatorLODTexture_'+identifier+'_'+str(source_lod),part_image,nearest=pm.get('texture_filter')=='nearest');added.append(key(lod_tex_obj.assets_file.name,lod_tex_obj.path_id))
                            lod_mat=material(material_template,objects,'MWC_OperatorMaterial_'+identifier+'_LOD'+str(source_lod),lod_tex_obj.path_id,alpha_clip=pm['alpha_clip_required'],data_maps=data_maps);added.append(key(lod_mat.assets_file.name,lod_mat.path_id));lod_materials[source_lod]=lod_mat.path_id
                        part_material=lod_materials[source_lod]
                    v,n,bi,bw,fit_report=adapt(np.asarray(part.vertices),np.asarray(part.normals),pm['bone_names'],pd['inverse_bind'],psi,psw,native['bone_names'],native['inverse_bind'],source_faces=part.faces,**po);mesh=copy.deepcopy(part);mesh.vertices=v.tolist();mesh.normals=n.tolist()
                    if np.linalg.det(po.get('source_basis',[[-1,0,0],[0,0,-1],[0,1,0]]))<0:mesh.faces=np.asarray(mesh.faces)[:,[0,2,1]].tolist()
                    if spec.get('lod_sources'):lod_record={'native_lod_levels':levels,'source_lod':source_lod,'source_geometry_sha256':digest(part_directory/'source.npz'),'shared_lod0_material_atlas':shared,'material_atlas':'shared_lod0' if shared else 'independent_authored_lod','missing_authored_normals_reconstructed':pm.get('missing_authored_normals_reconstructed',0)}
                parts=[(mesh,bi,bw)];mats=[part_material]
                if spec.get('glasses') and not first_person:
                    from .glasses import create
                    head_index=next(i for i,k in enumerate(native['bone_names']) if k.endswith('Head_M'));head=np.linalg.inv(native['inverse_bind'])[head_index,:3,3];coordinate_frame,units=native_frame(native['bone_names'],native['inverse_bind']);frame,shield,glass_meta=create(coordinate_frame.T@head/units)
                    for part in (frame,shield):
                        part.vertices=(np.asarray(part.vertices)@coordinate_frame.T*units).tolist();part.normals=(np.asarray(part.normals)@coordinate_frame.T).tolist()
                        idx=np.zeros((len(part.vertices),4),dtype='u1');idx[:,0]=head_index;weight=np.zeros((len(part.vertices),4),dtype='<f4');weight[:,0]=1;parts.append((part,idx,weight))
                    mats.extend([frame_mat.path_id,lens_mat.path_id])
                combined,bi,bw,submeshes=combine(parts);validate_weights(bi,bw,len(combined.vertices),len(native['bone_names']));md=skinned_tree(native['mesh_tree'],combined,'MWC_OperatorMesh_'+identifier,bi,bw,len(native['bone_names']));md['m_SubMeshes']=submeshes;new_mesh.save_typetree(md);fields.update(m_Materials=[{'m_FileID':0,'m_PathID':i} for i in mats],m_AABB=root_bounds(combined.vertices,native['inverse_bind'],native['root_bone_index'],tree['m_AABB']));expected_geometry[new_mesh.path_id]=(combined,bi,bw)
                model_records.append({'renderer':str(rid),'vertices':len(combined.vertices),'triangles':len(combined.faces),'submeshes':len(submeshes),'bones':len(native['bone_names']),'fit':fit_report,**lod_record})
            else:new_mesh.save_typetree(empty_visual(template.read_typetree()))
            fields['m_Mesh']={'m_FileID':0,'m_PathID':new_mesh.path_id};changed=copy.deepcopy(tree);changed.update(fields);obj=rig['objects'][rid];obj.save_typetree(changed);allowed[key(obj.assets_file.name,rid)]=fields;added.append(key(new_mesh.assets_file.name,new_mesh.path_id))
        records.append({'operator':identifier,'name':target['name'],'model':model,'prefab_guid':target['prefab_guid'],'source_geometry_sha256':digest(directory/'source.npz'),'source_variant':meta.get('source_variant','packaged_or_world'),'first_person_source_override':bool(first_person and spec.get('first_person_source')),'style':spec.get('style','original'),'glasses':bool(spec.get('glasses')),'material_template':material_record,'renderers':model_records,'original_renderers_changed':len(rig['renderers']),'skeleton_changed':False,'in_game_tested':False})
        completed_prefabs[target['prefab_guid']]=records[-1]
    expected=copy.deepcopy(before)
    for oid in list(allowed)+added:
        o=objects[oid];expected[(o.assets_file.name,o.path_id)]={'type':o.type.name,'sha256':hashlib.sha256(o.data if o.data is not None else o.get_raw_data()).hexdigest()}
    target_path=output/bundle;target_path.parent.mkdir(parents=True,exist_ok=True);target_path.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(target_path));new={key(o.assets_file.name,o.path_id):o for o in checked.objects}
    actual_inventory=inventory(checked)
    if actual_inventory!=expected:
        mismatch=[{'asset':str(oid),'expected':expected.get(oid),'actual':actual_inventory.get(oid)} for oid in expected.keys()|actual_inventory.keys() if expected.get(oid)!=actual_inventory.get(oid)];dump(output/'serialization-mismatch.json',mismatch)
        raise ValueError('Operator bundle serialization mismatch: '+str(len(mismatch))+' objects; see serialization-mismatch.json')
    old={key(o.assets_file.name,o.path_id):o for o in original}
    for oid,obj in old.items():
        if oid in allowed:
            tree=obj.read_typetree()
            # obj was edited in memory, so compare with a newly opened backup below.
        elif obj.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Unrelated operator object changed')
    backup_env=UnityPy.load(str(backup));untouched=0
    for obj in backup_env.objects:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid in allowed:
            tree=obj.read_typetree();tree.update(allowed[oid])
            if new[oid].read_typetree()!=tree:raise ValueError('Operator edit exceeded renderer field whitelist')
        else:
            if obj.get_raw_data()!=new[oid].get_raw_data():raise ValueError('Original operator asset changed: '+oid)
            untouched+=1
    for oid in added:
        obj=new[oid]
        for pid in local_refs(obj.read_typetree()):
            if key(obj.assets_file.name,pid) not in new:raise ValueError('New operator reference does not resolve')
    for pid,(mesh,bi,bw) in expected_geometry.items():geometry_check(next(o for o in checked.objects if o.path_id==pid),mesh,bi,bw)
    from .material_data import verify as verify_material_data
    local_objects={obj.path_id:obj for obj in checked.objects}
    for oid in added:
        obj=new[oid]
        if obj.type.name=='Material':
            verify_material_data(obj,local_objects,require_albedo=obj.peek_name().startswith('MWC_OperatorMaterial_'))
            if obj.peek_name().startswith('MWC_OperatorRustShield_'):
                from .lenses import verify as verify_lens
                verify_lens(obj)
    report={'build_id':version,'first_person':first_person,'operators':records,'files':[{'bundle':bundle,'backup':str(backup.resolve()),'output':str(target_path.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target_path),'changes':allowed,'added':added}],'verification':{'all_other_original_objects_byte_exact':untouched,'renderer_field_whitelist':['m_Mesh','m_Materials','m_AABB'],'geometry_uv_skin_exact_roundtrip':True,'original_meshes_materials_skeletons_animations_scripts_collision_retained':True,'all_new_local_references_resolve':True},'in_game_tested':False,'lens_transparency_in_game_tested':False};dump(output/'manifest.json',report);return report
