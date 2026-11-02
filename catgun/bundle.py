"""Build a visual-only cat child and non-destructive Lynx render bindings."""
import copy
import gc
import hashlib
import json
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from UnityPy.export.Texture2DConverter import image_to_texture2d
from halftone.assets import key,pointer,dump
from halftone.pipeline import build_id,safe_output
from bundle_utils import digest,inventory
from .geometry import make_cat,export,palette_image


def new_object(template,label,objects):
    clone=copy.copy(template);identifier=int.from_bytes(hashlib.sha256(label.encode()).digest()[:7],'little')+1
    while identifier in template.assets_file.objects: identifier+=1
    clone.path_id=identifier;clone.data=None
    template.assets_file.objects[identifier]=clone;template.assets_file.mark_changed()
    objects[key(clone.assets_file.name,identifier)]=clone
    return clone


def write(obj,tree):
    obj.save_typetree(tree)


def mesh_tree(template,mesh,name):
    d=copy.deepcopy(template);v,n,uv,f=mesh.arrays()
    interleaved=np.zeros((len(v),12),dtype='<f4');interleaved[:,:3]=v;interleaved[:,3:6]=n
    interleaved[:,6]=1;interleaved[:,9]=1;interleaved[:,10:12]=uv
    channels=[{'stream':0,'offset':0,'format':0,'dimension':0} for _ in range(14)]
    for i,offset,dim in [(0,0,3),(1,12,3),(2,24,4),(4,40,2)]: channels[i]={'stream':0,'offset':offset,'format':0,'dimension':dim}
    center=(v.min(axis=0)+v.max(axis=0))/2;extent=(v.max(axis=0)-v.min(axis=0))/2
    bounds={'m_Center':dict(zip('xyz',map(float,center))),'m_Extent':dict(zip('xyz',map(float,extent)))}
    d.update({'m_Name':name,'m_MeshCompression':0,'m_IsReadable':True,'m_IndexFormat':0,
        'm_IndexBuffer':f.astype('<u2').tobytes(),'m_LocalAABB':bounds,
        'm_VertexData':{'m_VertexCount':len(v),'m_Channels':channels,'m_DataSize':interleaved.tobytes()},
        'm_SubMeshes':[{'firstByte':0,'indexCount':int(f.size),'topology':0,'baseVertex':0,'firstVertex':0,'vertexCount':len(v),'localAABB':bounds}]})
    return d


def verify_geometry(obj,mesh):
    h=MeshHandler(obj.read());h.process();v,n,uv,f=mesh.arrays()
    if not np.array_equal(np.asarray(h.m_Vertices,dtype='<f4'),v): raise ValueError('Cat positions did not round-trip')
    if not np.array_equal(np.asarray(h.m_Normals,dtype='<f4'),n): raise ValueError('Cat normals did not round-trip')
    if not np.array_equal(np.asarray(h.m_UV0,dtype='<f4')[:,:2],uv): raise ValueError('Cat UVs did not round-trip')
    triangles=np.asarray(h.get_triangles()[0],dtype=np.uint32).reshape(-1,3)
    if not np.array_equal(triangles,f): raise ValueError('Cat triangle indices did not round-trip')


def build(config,cat_config):
    version=build_id(config);out=safe_output(cat_config['output'],config);report=out/'manifest.json'
    if report.exists(): raise ValueError('Existing cat build: choose a new output directory for a new variant')
    mesh=make_cat(cat_config['scale']);export(mesh,Path(cat_config['asset_output']))
    full_path=Path(config['paths']['reports'])/'modifications.json'
    baseline={b['bundle']:b for b in json.loads(full_path.read_text())['bundles']} if full_path.exists() else {}
    result={'build_id':version,'name':'MWC Lynx cat prototype','files':[],'geometry':{'vertices':len(mesh.vertices),'triangles':len(mesh.faces)},
            'in_game_tested':False,'notes':['Rigid decorative cat; original rig, animation, collision, sounds and scripts preserved.',
             'Lynx-specific render meshes hidden by separate empty render copies; original meshes retained.',
             'Shared optics remain available; muzzle/effect origins are not moved. Mouth alignment is provisional.']}
    out.mkdir(parents=True,exist_ok=True)
    weapons_cache=None
    for relative in ('src/weapons/weapons','src/weapons/attachments'):
        b=baseline.get(relative)
        source=Path(b['output']) if b else Path(config['bundle_root'])/relative
        if b and digest(source)!=b['output_sha256']: raise ValueError('Halftone baseline mismatch')
        backup=safe_output(Path(cat_config['backups'])/relative,config);backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():
            if digest(backup)!=digest(source): raise ValueError('Cat backup belongs to another baseline')
        else:
            with source.open('rb') as incoming,backup.open('xb') as stream:
                import shutil
                shutil.copyfileobj(incoming,stream)
        env=UnityPy.load(str(backup));before=inventory(env)
        objects={key(o.assets_file.name,o.path_id):o for o in env.objects}
        names={oid:o.peek_name() for oid,o in objects.items() if o.type.name=='GameObject'}
        original_objects=list(objects.values());allowed={};added=[];empties={}
        if any(o.type.name=='GameObject' and o.peek_name()=='MWC_CatVisual' for o in original_objects):
            raise ValueError('Source already contains the cat prototype; restore the non-cat baseline first')
        if relative.endswith('/weapons'):
            empty_obj=next(o for o in original_objects if o.type.name=='Mesh' and o.peek_name()=='GM6_Lynx_Empty')
            empty_tree=empty_obj.read_typetree();weapons_cache=copy.deepcopy(empty_tree)
        else:
            empty_tree=copy.deepcopy(weapons_cache)
        # Only change the renderer/filter mesh pointer. MeshCollider pointers,
        # the actual original meshes, bones, poses and script data are untouched.
        hidden=[]
        for obj in original_objects:
            if obj.type.name not in ('MeshFilter','SkinnedMeshRenderer'): continue
            tree=obj.read_typetree();go=pointer(obj.read().m_GameObject,obj.assets_file);name=names.get(go,'')
            if not name.startswith('GM6_Lynx_') or name=='GM6_Lynx_Empty': continue
            p=tree.get('m_Mesh')
            if not p or not p['m_PathID']: continue
            if p['m_FileID']!=0: raise ValueError('Unexpected external Lynx mesh; inspect before editing')
            source_id=key(obj.assets_file.name,p['m_PathID']);source_mesh=objects[source_id]
            if source_id not in empties:
                clone=new_object(source_mesh,'MWC-empty-'+source_id,objects)
                d=copy.deepcopy(empty_tree);d['m_Name']='MWC_EmptyRender_'+source_mesh.peek_name()
                original_mesh=source_mesh.read_typetree()
                for field in ('m_BindPose','m_BoneNameHashes','m_RootBoneNameHash','m_BonesAABB','m_LocalAABB'):
                    d[field]=copy.deepcopy(original_mesh[field])
                # Keep one empty submesh per material slot; preserve bone layout.
                sub=copy.deepcopy(d['m_SubMeshes'][0]);d['m_SubMeshes']=[copy.deepcopy(sub) for _ in original_mesh['m_SubMeshes']]
                write(clone,d);added.append(key(clone.assets_file.name,clone.path_id));empties[source_id]=clone
            clone=empties[source_id];old=copy.deepcopy(p);tree['m_Mesh']={'m_FileID':0,'m_PathID':clone.path_id}
            write(obj,tree);oid=key(obj.assets_file.name,obj.path_id)
            allowed[oid]={'kind':'visual_mesh_binding','old':old,'new':tree['m_Mesh']}
            hidden.append({'name':name,'object':oid,'original_mesh':source_id})
        # Runtime assembly can populate initially empty skinned renderers.
        # Disable every Lynx-specific renderer, including those with null meshes;
        # leave transforms, bones and original mesh assets intact.
        disabled=[]
        for obj in original_objects:
            if obj.type.name not in ('MeshRenderer','SkinnedMeshRenderer'):continue
            tree=copy.deepcopy(obj.read_typetree())
            go=pointer(obj.read().m_GameObject,obj.assets_file);name=names.get(go,'')
            if not name.startswith('GM6_Lynx_') or name=='GM6_Lynx_Empty':continue
            oid=key(obj.assets_file.name,obj.path_id)
            if oid in allowed:tree['m_Mesh']=allowed[oid]['new']
            tree['m_Enabled']=False;write(obj,tree)
            if oid in allowed:allowed[oid]['disabled']=True
            else:allowed[oid]={'kind':'visual_renderer_disabled'}
            disabled.append({'name':name,'object':oid})
        cat_mesh_id=None
        if relative.endswith('/weapons'):
            cat_mesh=new_object(empty_obj,'MWC-cat-mesh',objects);write(cat_mesh,mesh_tree(empty_tree,mesh,'MWC_CatMesh'))
            # ObjectReader.read() still reads its original backing bytes after
            # save_typetree(); verify the new geometry after bundle reopening.
            cat_mesh_id=key(cat_mesh.assets_file.name,cat_mesh.path_id);added.append(cat_mesh_id)
            texture_template=next(o for o in original_objects if o.type.name=='Texture2D')
            texture_obj=new_object(texture_template,'MWC-cat-palette',objects);texture=texture_obj.read()
            image=palette_image();image_data,_=image_to_texture2d(image,4)
            texture.m_Name='MWC_CatPalette';texture.m_Width,texture.m_Height=image.size
            texture.image_data=image_data;texture.m_TextureFormat=4;texture.m_CompleteImageSize=len(image_data);texture.m_MipCount=1
            if texture.m_MipMap is not None: texture.m_MipMap=False
            texture.m_ColorSpace=1;texture.m_StreamData.path='';texture.m_StreamData.offset=0;texture.m_StreamData.size=0
            texture.m_TextureSettings.m_FilterMode=1;texture.m_TextureSettings.m_WrapU=texture.m_TextureSettings.m_WrapV=1
            texture.save();added.append(key(texture_obj.assets_file.name,texture_obj.path_id))
            material_template=next(o for o in original_objects if o.type.name=='Material' and o.peek_name()=='Cheek')
            material_obj=new_object(material_template,'MWC-cat-material',objects);mat=material_obj.read();mat.m_Name='MWC_CatCoat'
            for slot,entry in mat.m_SavedProperties.m_TexEnvs:
                entry.m_Texture.m_FileID=0
                entry.m_Texture.m_PathID=texture_obj.path_id if slot in ('_BaseMap','_MainTex') else 0
            values={'_Metallic':0,'_Smoothness':.25,'_Glossiness':.25,'_AlphaClip':0,'_Surface':0,'_Cull':2,'_ZWrite':1,'EnableCamo':0,'FlapEnable':0}
            for i,(name,value) in enumerate(mat.m_SavedProperties.m_Floats):
                if name in values: mat.m_SavedProperties.m_Floats[i]=(name,float(values[name]))
            for name,color in mat.m_SavedProperties.m_Colors:
                if name in ('_BaseColor','_Color'):color.r=color.g=color.b=color.a=1
                elif name=='_EmissionColor':color.r=color.g=color.b=0
            if getattr(mat,'m_ShaderKeywords',None) is not None:mat.m_ShaderKeywords=''
            if getattr(mat,'m_ValidKeywords',None) is not None:mat.m_ValidKeywords=[]
            if getattr(mat,'m_InvalidKeywords',None) is not None:mat.m_InvalidKeywords=[]
            mat.save();added.append(key(material_obj.assets_file.name,material_obj.path_id))
            # Add sibling visual nodes using existing plain Transform/Renderer/
            # MeshFilter serialization templates. Do not modify weapon scripts.
            count=0
            for go_obj in original_objects:
                if go_obj.type.name!='GameObject' or go_obj.peek_name()!='GM6_Lynx_Empty':continue
                go_tree=go_obj.read_typetree();parts={objects[key(go_obj.assets_file.name,p['component']['m_PathID'])].type.name:objects[key(go_obj.assets_file.name,p['component']['m_PathID'])] for p in go_tree['m_Component']}
                old_t=parts['Transform'].read_typetree();parent_id=key(go_obj.assets_file.name,old_t['m_Father']['m_PathID']);parent=objects[parent_id]
                new_go=new_object(go_obj,f'MWC-cat-go-{count}',objects)
                new_t=new_object(parts['Transform'],f'MWC-cat-transform-{count}',objects)
                new_r=new_object(parts['MeshRenderer'],f'MWC-cat-renderer-{count}',objects)
                new_f=new_object(parts['MeshFilter'],f'MWC-cat-filter-{count}',objects)
                go_tree['m_Name']='MWC_CatVisual';go_tree['m_IsActive']=True
                go_tree['m_Component']=[{'component':{'m_FileID':0,'m_PathID':o.path_id}} for o in (new_t,new_r,new_f)]
                write(new_go,go_tree)
                td=old_t;td['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};td['m_Children']=[]
                td['m_LocalPosition']=dict(zip('xyz',map(float,cat_config['position'])))
                td['m_LocalRotation']=dict(zip('xyzw',map(float,cat_config.get('rotation',[0,2**-.5,2**-.5,0]))));td['m_LocalScale']={'x':1.,'y':1.,'z':1.};write(new_t,td)
                rd=parts['MeshRenderer'].read_typetree();rd['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};rd['m_Enabled']=True
                rd['m_Materials']=[{'m_FileID':0,'m_PathID':material_obj.path_id}];write(new_r,rd)
                fd=parts['MeshFilter'].read_typetree();fd['m_GameObject']={'m_FileID':0,'m_PathID':new_go.path_id};fd['m_Mesh']={'m_FileID':0,'m_PathID':cat_mesh.path_id};write(new_f,fd)
                pd=parent.read_typetree();pd['m_Children'].append({'m_FileID':0,'m_PathID':new_t.path_id});write(parent,pd)
                allowed[parent_id]={'kind':'cat_child_link','child':new_t.path_id}
                added.extend(key(o.assets_file.name,o.path_id) for o in (new_go,new_t,new_r,new_f));count+=1
            if count!=2:raise ValueError('Unexpected Lynx visual-root layout')
        expected=inventory(env)
        for oid,obj in objects.items():
            k=(obj.assets_file.name,obj.path_id)
            if oid in allowed or oid in added:expected[k]['sha256']=hashlib.sha256(obj.data).hexdigest()
            elif before[k]!=expected[k]:raise ValueError('Unexpected original object modification')
        path=out/relative;path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.partial')
        with temp.open('wb') as stream:stream.write(env.file.save(packer='lz4'))
        del env,objects,original_objects;gc.collect()
        checked=UnityPy.load(str(temp));actual=inventory(checked)
        if actual!=expected:raise ValueError('Cat bundle serialization mismatch')
        checked_objects={key(o.assets_file.name,o.path_id):o for o in checked.objects}
        if cat_mesh_id:verify_geometry(checked_objects[cat_mesh_id],mesh)
        original_env=UnityPy.load(str(backup));original_objects={key(o.assets_file.name,o.path_id):o for o in original_env.objects}
        for oid,change in allowed.items():
            a=original_objects[oid].read_typetree();b=checked_objects[oid].read_typetree()
            if change['kind']=='visual_mesh_binding':
                a['m_Mesh']=change['new']
                if change.get('disabled'):a['m_Enabled']=False
            elif change['kind']=='visual_renderer_disabled':a['m_Enabled']=False
            else:a['m_Children'].append({'m_FileID':0,'m_PathID':change['child']})
            if a!=b:raise ValueError('Nonvisual fields changed on an existing object')
        for oid in added:
            obj=checked_objects[oid]
            if obj.type.name=='Mesh' and oid!=cat_mesh_id:
                if obj.read().m_VertexData.m_VertexCount!=0:raise ValueError('Hidden renderer copy is not empty')
        del checked,checked_objects,original_env,original_objects;gc.collect()
        temp.replace(path)
        result['files'].append({'bundle':relative,'source':str(source.resolve()),'backup':str(backup.resolve()),
            'source_sha256':digest(backup),'output':str(path.resolve()),'output_sha256':digest(path),
            'hidden_render_bindings':hidden,'disabled_renderers':disabled,'existing_object_changes':allowed,'added_objects':added,
            'checks':{'reopened':True,'all_other_original_objects_byte_exact':True,'only_render_bindings_and_child_links_changed':True,
                      'original_meshes_colliders_scripts_animations_audio_unchanged':True,'cat_geometry_exact_roundtrip':bool(cat_mesh_id)}})
        dump(report,result);print('Cat visual bundle verified:',relative,'render bindings',len(hidden),flush=True)
    return result
