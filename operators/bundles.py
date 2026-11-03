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

ROOT=Path(__file__).resolve().parents[1]
BUNDLE='src/thrid_person'


def material(template,objects,label,texture,rgba=(1.,1.,1.,1.),alpha_clip=False,transparent=False):
    obj=new_object(template,label,objects);m=obj.read();m.m_Name=label
    for slot,value in m.m_SavedProperties.m_TexEnvs:
        value.m_Texture.m_FileID=0;value.m_Texture.m_PathID=texture if slot in ('_BaseMap','_MainTex') else 0;value.m_Scale.x=value.m_Scale.y=1;value.m_Offset.x=value.m_Offset.y=0
    values={'_Metallic':0.,'_Smoothness':.18 if transparent else .35,'_Glossiness':.18 if transparent else .35,'_AlphaClip':float(alpha_clip),'_Cutoff':.35,'_AlphaToMask':0.,'_Surface':float(transparent),'_Blend':0.,'_SrcBlend':5. if transparent else 1.,'_DstBlend':10. if transparent else 0.,'_SrcBlendAlpha':1.,'_DstBlendAlpha':10. if transparent else 0.,'_ZWrite':0. if transparent else 1.,'_Cull':0. if transparent else 2.,'EnableCamo':0.,'FlapEnable':0.}
    seen=set()
    for i,(slot,value) in enumerate(m.m_SavedProperties.m_Floats):
        if slot in values:m.m_SavedProperties.m_Floats[i]=(slot,values[slot]);seen.add(slot)
    for slot in values.keys()-seen:m.m_SavedProperties.m_Floats.append((slot,values[slot]))
    for slot,c in m.m_SavedProperties.m_Colors:
        if slot in ('_BaseColor','_Color'):c.r,c.g,c.b,c.a=rgba
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
    source=Path(config['bundle_root'])/BUNDLE
    if digest(source)!=settings['source_sha256']:raise ValueError('Operator baseline changed')
    output=safe_output(settings['output'],config);backup=safe_output(settings['backups'],config)/BUNDLE
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh operator build directory')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        if digest(backup)!=settings['source_sha256']:raise ValueError('Operator backup belongs to another baseline')
    else:shutil.copyfile(source,backup)
    env=UnityPy.load(str(backup));original=list(env.objects);before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in original};allowed={};added=[];expected_geometry={};records=[];cached={}
    targets={t['id']:t for t in json.loads((ROOT/'config/operator-targets.json').read_text())['operators']}
    texture_template=next(o for o in original if o.type.name=='Texture2D')
    for identifier,model in assignments.items():
        if model not in settings['library']:raise ValueError('Model source is not available locally: '+model)
        spec=settings['library'][model];directory=Path(spec['source']);target=targets[identifier];rig=native_rig(env,target);model_key=(model,spec.get('style','original'))
        if model_key not in cached:
            base,image,si,sw,meta=load(directory,spec.get('style','original'),config);data=np.load(directory/'source.npz',allow_pickle=False);options=profile(spec['profile'],meta);cached[model_key]=(base,image,si,sw,meta,data,options)
        base,image,si,sw,meta,data,options=cached[model_key]
        tex_obj=new_object(texture_template,'MWC_OperatorTexture_'+identifier,objects);tex=tex_obj.read();raw,_=image_to_texture2d(image,4);tex.m_Name='MWC_OperatorTexture_'+identifier;tex.m_Width,tex.m_Height=image.size;tex.image_data=raw;tex.m_TextureFormat=4;tex.m_CompleteImageSize=len(raw);tex.m_MipCount=1
        if tex.m_MipMap is not None:tex.m_MipMap=False
        tex.m_ColorSpace=1;tex.m_StreamData.path='';tex.m_StreamData.offset=tex.m_StreamData.size=0;tex.m_TextureSettings.m_FilterMode=0 if meta.get('texture_filter')=='nearest' else 1;tex.m_TextureSettings.m_WrapU=tex.m_TextureSettings.m_WrapV=1;tex.save();added.append(key(tex_obj.assets_file.name,tex_obj.path_id))
        primary=set(rig['primary'].values());donor=rig['snapshots'][rig['primary'][min(rig['primary'])]];pointer=donor['renderer']['m_Materials'][0]
        if pointer['m_FileID']!=0:raise ValueError('External operator material needs explicit handling')
        material_template=objects[key(donor['mesh_object'].assets_file.name,pointer['m_PathID'])];body_mat=material(material_template,objects,'MWC_OperatorMaterial_'+identifier,tex_obj.path_id,alpha_clip=meta['alpha_clip_required']);added.append(key(body_mat.assets_file.name,body_mat.path_id));frame_mat=lens_mat=None
        if spec.get('glasses'):
            frame_mat=material(material_template,objects,'MWC_OperatorFrame_'+identifier,0,(.012,.016,.020,1.));lens_mat=material(material_template,objects,'MWC_OperatorRustShield_'+identifier,0,(.32,.095,.035,.40),transparent=True);added.extend(key(o.assets_file.name,o.path_id) for o in (frame_mat,lens_mat))
        model_records=[]
        for rid,tree in rig['renderers'].items():
            template=rig['meshes'][rid];new_mesh=new_object(template,'MWC_OperatorMesh_'+identifier+'_'+str(rid),objects)
            fields={}
            if rid in primary:
                native=rig['snapshots'][rid];v,n,bi,bw,fit_report=adapt(np.asarray(base.vertices),np.asarray(base.normals),meta['bone_names'],data['inverse_bind'],si,sw,native['bone_names'],native['inverse_bind'],**options);mesh=copy.deepcopy(base);mesh.vertices=v.tolist();mesh.normals=n.tolist()
                if np.linalg.det(options.get('source_basis',[[-1,0,0],[0,0,-1],[0,1,0]]))<0:mesh.faces=np.asarray(mesh.faces)[:,[0,2,1]].tolist()
                parts=[(mesh,bi,bw)];mats=[body_mat.path_id]
                if spec.get('glasses'):
                    from .glasses import create
                    head_index=next(i for i,k in enumerate(native['bone_names']) if k.endswith('Head_M'));head=np.linalg.inv(native['inverse_bind'])[head_index,:3,3];coordinate_frame,units=native_frame(native['bone_names'],native['inverse_bind']);frame,shield,glass_meta=create(coordinate_frame.T@head/units)
                    for part in (frame,shield):
                        part.vertices=(np.asarray(part.vertices)@coordinate_frame.T*units).tolist();part.normals=(np.asarray(part.normals)@coordinate_frame.T).tolist()
                        idx=np.zeros((len(part.vertices),4),dtype='u1');idx[:,0]=head_index;weight=np.zeros((len(part.vertices),4),dtype='<f4');weight[:,0]=1;parts.append((part,idx,weight))
                    mats.extend([frame_mat.path_id,lens_mat.path_id])
                combined,bi,bw,submeshes=combine(parts);validate_weights(bi,bw,len(combined.vertices),len(native['bone_names']));md=skinned_tree(native['mesh_tree'],combined,'MWC_OperatorMesh_'+identifier,bi,bw,len(native['bone_names']));md['m_SubMeshes']=submeshes;new_mesh.save_typetree(md);fields.update(m_Materials=[{'m_FileID':0,'m_PathID':i} for i in mats],m_AABB=md['m_LocalAABB']);expected_geometry[new_mesh.path_id]=(combined,bi,bw)
                model_records.append({'renderer':str(rid),'vertices':len(combined.vertices),'triangles':len(combined.faces),'submeshes':len(submeshes),'bones':len(native['bone_names']),'fit':fit_report})
            else:new_mesh.save_typetree(empty_visual(template.read_typetree()))
            fields['m_Mesh']={'m_FileID':0,'m_PathID':new_mesh.path_id};changed=copy.deepcopy(tree);changed.update(fields);obj=rig['objects'][rid];obj.save_typetree(changed);allowed[key(obj.assets_file.name,rid)]=fields;added.append(key(new_mesh.assets_file.name,new_mesh.path_id))
        records.append({'operator':identifier,'name':target['name'],'model':model,'prefab_guid':target['prefab_guid'],'source_geometry_sha256':digest(directory/'source.npz'),'style':spec.get('style','original'),'glasses':bool(spec.get('glasses')),'renderers':model_records,'original_renderers_changed':len(rig['renderers']),'skeleton_changed':False,'in_game_tested':False})
    expected=copy.deepcopy(before)
    for oid in list(allowed)+added:
        o=objects[oid];expected[(o.assets_file.name,o.path_id)]={'type':o.type.name,'sha256':hashlib.sha256(o.data if o.data is not None else o.get_raw_data()).hexdigest()}
    target_path=output/BUNDLE;target_path.parent.mkdir(parents=True,exist_ok=True);target_path.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(target_path));new={key(o.assets_file.name,o.path_id):o for o in checked.objects}
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
    report={'build_id':version,'operators':records,'files':[{'bundle':BUNDLE,'backup':str(backup.resolve()),'output':str(target_path.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target_path),'changes':allowed,'added':added}],'verification':{'all_other_original_objects_byte_exact':untouched,'renderer_field_whitelist':['m_Mesh','m_Materials','m_AABB'],'geometry_uv_skin_exact_roundtrip':True,'original_meshes_materials_skeletons_animations_scripts_collision_retained':True,'all_new_local_references_resolve':True},'in_game_tested':False,'lens_transparency_in_game_tested':False};dump(output/'manifest.json',report);return report
