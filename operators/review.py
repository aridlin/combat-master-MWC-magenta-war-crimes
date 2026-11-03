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


def export(stage,output,pose_name='bind'):
    stage,output=Path(stage),Path(output);manifest=json.loads((stage/'manifest.json').read_text());row=manifest['files'][0];bundle=Path(row['output'])
    if hashlib.sha256(bundle.read_bytes()).hexdigest()!=row['output_sha256']:raise ValueError('Review input changed after verification')
    env=UnityPy.load(str(bundle));objects={o.path_id:o for o in env.objects};reports=[]
    transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    for record in manifest['operators']:
        rid=int(record['renderers'][0]['renderer']);renderer=objects[rid].read_typetree();obj=objects[renderer['m_Mesh']['m_PathID']];tree=obj.read_typetree();h=MeshHandler(obj.read());h.process();triangles=h.get_triangles();faces=np.concatenate([np.asarray(t,dtype='<u4').reshape(-1,3) for t in triangles])
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
        pose=articulated_pose(bind,parents,names,rotations);original=v.copy();v=cpu_skin(v,bi,bw,pose,bind).astype('<f4');deformation=pose@bind;normal_transforms=np.linalg.inv(deformation[:,:3,:3]).transpose(0,2,1);result=np.zeros_like(n)
        for k in range(4):result+=np.einsum('nij,nj->ni',normal_transforms[bi[:,k]],n)*bw[:,k,None]
        n=result/np.maximum(np.linalg.norm(result,axis=1,keepdims=True),1e-12)
        if not np.isfinite(v).all():raise ValueError('Non-finite articulated geometry')
        if pose_name=='bind' and not np.allclose(v,original,atol=2e-5):raise ValueError('Serialized native bind pose does not reproduce the mesh')
        frame,units=native_frame(names,bind);v=(v@frame/units).astype('<f4');n=(n@frame).astype('<f4')
        # Keep the displayed skeleton in the same canonical review frame.
        to_native=np.eye(4);to_native[:3,:3]=frame*units;review_bind=bind@to_native
        out=output/record['model'];out.mkdir(parents=True,exist_ok=True);materials=[]
        for mi,ptr in enumerate(renderer['m_Materials']):
            mat=objects[ptr['m_PathID']].read_typetree();props=mat['m_SavedProperties'];color=next((c for key,c in props['m_Colors'] if key in ('_BaseColor','_Color')),dict(r=1,g=1,b=1,a=1));m={'name':mat['m_Name'],'base_color_linear':[color[k] for k in 'rgba']};texture=next((slot['m_Texture']['m_PathID'] for key,slot in props['m_TexEnvs'] if key in ('_BaseMap','_MainTex') and slot['m_Texture']['m_PathID']),0)
            if texture:
                filename=f'material-{mi}.png';objects[texture].read().image.save(out/filename);m['image']=filename
            if any(key=='_Surface' and value==1 for key,value in props['m_Floats']):m['transparent']=True
            materials.append(m)
        np.savez_compressed(out/'source.npz',positions=v,normals=n,uv=np.asarray(h.m_UV0,dtype='<f4')[:,:2],faces=faces,face_materials=fm,bone_indices=bi,bone_weights=bw,inverse_bind=review_bind)
        meta={'id':record['model'],'coordinate_system':'z_up','materials':materials,'bone_names':names,'bone_parents':parents,'review_pose':pose_name,'source_bundle_sha256':row['output_sha256'],'private_native_rig_data':True,'in_game_tested':False};(out/'source.json').write_text(json.dumps(meta,indent=2)+'\n');reports.append({'model':record['model'],'operator':record['operator'],'vertices':len(v),'pose':pose_name,'finite':True,'bind_identity_checked':pose_name=='bind'})
    (output/'review.json').write_text(json.dumps(reports,indent=2)+'\n');return reports


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('output');p.add_argument('--pose',choices=['bind','articulated'],default='bind');a=p.parse_args();print(json.dumps(export(a.stage,a.output,a.pose),indent=2))
