"""Export a built operator's *serialized* mesh for private visual review.

The output contains local game rig data and must not be redistributed. Optional
poses are synthetic articulation checks, never a substitute for game testing.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from .skinning import cpu_skin
from .retarget import native_frame


def material_appearance(tree):
    props=tree['m_SavedProperties'];colors=dict(props['m_Colors']);floats=dict(props['m_Floats'])
    color=next((colors[k] for k in ('_BaseColor','_Color','AlbedoColor') if k in colors),dict(r=1,g=1,b=1,a=1))
    result={'name':tree['m_Name'],'base_color_linear':[color[k] for k in 'rgba'],'shader_pointer':tree['m_Shader']}
    if floats.get('_Surface')==1:
        shader=tree['m_Shader']['m_PathID']
        if shader in (-1264317247848577453,4545324427977414316):
            if floats.get('_SrcBlend')!=5 or floats.get('_DstBlend')!=10 or floats.get('_ZWrite')!=0:raise ValueError('Unreviewed lens alpha blend state')
            result.update(transparent=True,alpha_mode='blend',cull_backfaces=floats.get('_Cull')==2,roughness=1-floats.get('_Smoothness',.5),casts_shadow='shadowcaster' not in {p.lower() for p in tree.get('disabledShaderPasses',[])})
        elif shader==9216735585210638481:
            # The native body graph has fixed opaque state, regardless of floats.
            result['base_color_linear'][3]=1.;result['declared_transparent_but_shader_opaque']=True
        else:raise ValueError('Unknown transparent shader needs explicit preview support')
    return result


def articulated_pose(bind,parents,names,rotations):
    rest=np.linalg.inv(bind);pose=np.zeros_like(rest);done=set()
    clean=[n.split(':')[-1] for n in names]
    def visit(i):
        if i in done:return
        parent=int(parents[i])
        if parent>=0:visit(parent)
        local=np.linalg.inv(rest[parent])@rest[i] if parent>=0 else rest[i].copy()
        if clean[i] in rotations:
            axis,angle=rotations[clean[i]];axis=np.asarray(axis,float);axis/=np.linalg.norm(axis);x,y,z=axis;c=np.cos(np.deg2rad(angle));s=np.sin(np.deg2rad(angle));k=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
            r=np.eye(4);r[:3,:3]=np.eye(3)+s*k+(1-c)*(k@k);local=local@r
        pose[i]=(pose[parent]@local) if parent>=0 else local;done.add(i)
    for i in range(len(names)):visit(i)
    return pose


def export(stage,output,pose_name='bind',*,clip_pose=None):
    stage,output=Path(stage),Path(output);manifest=json.loads((stage/'manifest.json').read_text());row=manifest['files'][0];bundle=Path(row['output'])
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=row['output_sha256']:raise ValueError('Review input changed after verification')
    if pose_name not in ('bind','articulated','clip') or (pose_name=='clip')!=(clip_pose is not None):
        raise ValueError('Use --pose clip with --clip-pose, or choose bind/articulated without a clip')
    records=manifest['operators']
    if clip_pose is not None:
        if manifest.get('first_person'):raise ValueError('Clip input currently supports world operators only')
        from halftone.pipeline import safe_output
        output=safe_output(output,{'bundle_root':str(bundle.parent)})
        project=Path(__file__).resolve().parents[1]
        if output==project or project in output.parents:raise ValueError('Native pose review must stay outside public source/package files')
        if output.exists():raise ValueError('Choose a fresh private clip review directory')
        clip_report=json.loads((Path(clip_pose)/'review.json').read_text())
        records=[record for record in records if record['operator']==clip_report.get('operator')]
        if len(records)!=1:raise ValueError('Clip operator is absent or ambiguous in the staged build')
    env=UnityPy.load(str(bundle));objects={o.path_id:o for o in env.objects};reports=[]
    transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    for record in records:
        if clip_pose is None:rid=int(record['renderers'][0]['renderer'])
        else:
            from .pose_input import main_world_renderer
            targets=json.loads((Path(__file__).resolve().parents[1]/'config/operator-targets.json').read_text())['operators']
            rid=main_world_renderer(record,targets)
        renderer=objects[rid].read_typetree();obj=objects[renderer['m_Mesh']['m_PathID']];tree=obj.read_typetree();h=MeshHandler(obj.read());h.process();triangles=h.get_triangles();faces=np.concatenate([np.asarray(t,dtype='<u4').reshape(-1,3) for t in triangles])
        # MeshHandler returns triangle lists, whose shape can be either (n,3) or flat.
        fm=np.concatenate([np.full(np.asarray(t).size//3,i,dtype='<i4') for i,t in enumerate(triangles)])
        ids=[p['m_PathID'] for p in renderer['m_Bones']];index={pid:i for i,pid in enumerate(ids)};names=[objects[transforms[pid]['m_GameObject']['m_PathID']].peek_name() for pid in ids];parents=[]
        for pid in ids:
            parent=transforms[pid]['m_Father']['m_PathID']
            while parent and parent not in index:parent=transforms[parent]['m_Father']['m_PathID']
            parents.append(index.get(parent,-1))
        bind=np.asarray([[[p['e'+str(i)+str(j)] for j in range(4)] for i in range(4)] for p in tree['m_BindPose']],dtype='<f4');v=np.asarray(h.m_Vertices,dtype='<f4');n=np.asarray(h.m_Normals,dtype='<f4');bi=np.asarray(h.m_BoneIndices,dtype='u1');bw=np.asarray(h.m_BoneWeights,dtype='<f4')
        # A deterministic head turn and bent limbs expose detached accessories,
        # inverted skinning and gross weight leakage without running game code.
        rotations={} if pose_name=='bind' else {'Head_M':([0,1,0],35),'Elbow_L':([1,0,0],55),'Elbow_R':([1,0,0],-35),'Knee_L':([1,0,0],45),'Shoulder_L':([0,0,1],20)}
        if manifest.get('first_person') and pose_name!='bind':rotations={'j_elbow_L':([1,0,0],35),'j_elbow_R':([1,0,0],-25),'j_hand_L':([0,0,1],15)}
        clip_info=None
        if clip_pose is None:pose=articulated_pose(bind,parents,names,rotations)
        else:
            from .pose_input import read_world_pose
            pose,renderer_world,clip_info=read_world_pose(clip_pose,row['source_sha256'],record['operator'],rid,names,bind)
        original=v.copy();v=cpu_skin(v,bi,bw,pose,bind).astype('<f4');deformation=pose@bind;normal_transforms=np.linalg.inv(deformation[:,:3,:3]).transpose(0,2,1);result=np.zeros_like(n)
        for k in range(4):result+=np.einsum('nij,nj->ni',normal_transforms[bi[:,k]],n)*bw[:,k,None]
        n=result/np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-12)
        if not np.isfinite(v).all():raise ValueError('Non-finite articulated geometry')
        if pose_name=='bind' and not np.allclose(v,original,atol=2e-5):raise ValueError('Serialized native bind pose does not reproduce the mesh')
        if clip_pose is not None:
            from .pose_space import transform_pose
            v,n,review_bind=transform_pose(v,n,np.linalg.inv(pose),renderer_world)
        elif manifest.get('first_person'):
            rest=np.linalg.inv(bind);up=rest[names.index('tag_camera'),:3,3]-rest[names.index('tag_torso'),:3,3];axis=up/np.linalg.norm(up)
            if axis[2]>.95:frame=np.eye(3)
            elif axis[1]>.95:frame=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
            else:raise ValueError('Unreviewed first-person mesh frame')
            units=100. if np.linalg.norm(up)>10 else 1.
        else:frame,units=native_frame(names,bind)
        if clip_pose is None:
            v=(v@frame/units).astype('<f4');n=(n@frame).astype('<f4')
            # Keep the displayed skeleton in the same canonical review frame.
            to_native=np.eye(4);to_native[:3,:3]=frame*units;review_bind=bind@to_native
        out=output/record['model'];out.mkdir(parents=True,exist_ok=True);materials=[]
        for mi,ptr in enumerate(renderer['m_Materials']):
            mat=objects[ptr['m_PathID']].read_typetree();props=mat['m_SavedProperties'];m=material_appearance(mat);texture=next((slot['m_Texture']['m_PathID'] for key,slot in props['m_TexEnvs'] if key in ('_BaseMap','_MainTex','Albedo') and slot['m_Texture']['m_PathID']),0)
            if texture:
                filename=f'material-{mi}.png';objects[texture].read().image.save(out/filename);m['image']=filename
            materials.append(m)
        np.savez_compressed(out/'source.npz',positions=v,normals=n,uv=np.asarray(h.m_UV0,dtype='<f4')[:,:2],faces=faces,face_materials=fm,bone_indices=bi,bone_weights=bw,inverse_bind=review_bind)
        meta={'id':record['model'],'coordinate_system':'z_up','materials':materials,'bone_names':names,'bone_parents':parents,'review_pose':pose_name,'source_bundle_sha256':row['output_sha256'],'private_native_rig_data':True,'in_game_tested':False}
        if clip_info is not None:meta.update(original_clip=clip_info,review_renderer=str(rid),review_LOD=0)
        (out/'source.json').write_text(json.dumps(meta,indent=2)+'\n');reports.append({'model':record['model'],'operator':record['operator'],'vertices':len(v),'pose':pose_name,'finite':True,'bind_identity_checked':pose_name=='bind',**({'original_clip':clip_info} if clip_info is not None else {})})
    (output/'review.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('output');p.add_argument('--pose',choices=['bind','articulated','clip'],default='bind');p.add_argument('--clip-pose',help='Private operators.clip_review world export; selects its exact staged operator');a=p.parse_args();print(json.dumps(export(a.stage,a.output,a.pose,clip_pose=a.clip_pose),indent=2))
