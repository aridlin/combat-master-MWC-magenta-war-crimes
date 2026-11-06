"""Reduce first-person bulk without shortening native joint-to-joint reach."""
import json,re
from pathlib import Path
import numpy as np


def settings(model):
    spec=json.loads((Path(__file__).resolve().parents[1]/'config/operator-viewmodels.json').read_text());value={**spec['defaults'],**spec['models'].get(model,{})}
    if set(value)!={'arm_radius_scale','hand_radius_scale'} or any(type(v) not in (float,int) or not np.isfinite(v) or not .25<=v<=1.25 for v in value.values()):raise ValueError('Unsupported first-person radius scale')
    return value


def slim(positions,normals,indices,weights,native,arm_radius_scale,hand_radius_scale,*,leaf_endpoints=None):
    from .first_person import native_name
    names=[native_name(n) for n in native['bone_names']];byname={n:i for i,n in enumerate(names)};points=np.linalg.inv(native['inverse_bind'])[:,:3,3];v=np.asarray(positions,dtype=float);n=np.asarray(normals,dtype=float);bi=np.asarray(indices);bw=np.asarray(weights);matrices=np.repeat(np.eye(3)[None],len(names),axis=0);translations=np.zeros((len(names),3));used=set(map(int,bi[bw>0]));next_joint={'Scapula':'Shoulder','Shoulder':'Elbow','Elbow':'Wrist','Wrist':'MiddleFinger1'}
    leaf_axes={}
    for name,point in (leaf_endpoints or {}).items():
        if not isinstance(name,str) or not re.fullmatch(r'(Thumb|Index|Middle|Ring|Pinky)Finger3_[LR]',name) or name not in byname:
            raise ValueError('Unknown first-person leaf endpoint: '+str(name))
        point=np.asarray(point,dtype=float)
        if point.shape!=(3,) or not np.isfinite(point).all():raise ValueError('Invalid first-person leaf endpoint: '+name)
        axis=point-points[byname[name]]
        if np.linalg.norm(axis)<1e-7:raise ValueError('Degenerate first-person leaf endpoint: '+name)
        leaf_axes[name]=axis
    for bone in used:
        name=names[bone];base,side=name.rsplit('_',1);child=next_joint.get(base);child=child+'_'+side if child else None;finger=re.fullmatch(r'(.+Finger)([123])',base)
        if finger:child=finger[1]+str(int(finger[2])+1)+'_'+side
        if child in byname:axis=points[byname[child]]-points[bone]
        elif finger and finger[2]=='3':axis=points[bone]-points[byname[finger[1]+'2_'+side]]
        else:raise ValueError('Missing first-person radius axis: '+name)
        if np.linalg.norm(axis)<1e-7:raise ValueError('Degenerate first-person radius axis')
        axis/=np.linalg.norm(axis);scale=hand_radius_scale if base=='Wrist' or finger else arm_radius_scale;linear=scale*np.eye(3)+(1-scale)*np.outer(axis,axis);matrices[bone]=linear;translations[bone]=points[bone]-linear@points[bone]
    linear=np.zeros((len(v),3,3));translation=np.zeros_like(v)
    for k in range(4):linear+=matrices[bi[:,k]]*bw[:,k,None,None];translation+=translations[bi[:,k]]*bw[:,k,None]
    result=np.einsum('nij,nj->ni',linear,v)+translation
    for name,direction in leaf_axes.items():
        bone=byname[name]
        if bone not in used or hand_radius_scale==1:continue
        # Preserve the old radius frame at the base of a leaf, then converge
        # smoothly to its full 3D cap frame. An abrupt axis change can fold the
        # junction where authored weights blend with the previous finger bone.
        axis=direction/np.linalg.norm(direction)
        cap_matrix=hand_radius_scale*np.eye(3)+(1-hand_radius_scale)*np.outer(axis,axis)
        delta=cap_matrix-matrices[bone];offset=v-points[bone]
        t=(offset@direction)/(direction@direction);fraction=np.clip(t,0,1)
        blend=fraction*fraction*(3-2*fraction)
        derivative=6*fraction*(1-fraction);derivative[(t<=0)|(t>=1)]=0
        gradient=derivative[:,None]*direction/(direction@direction)
        displacement=offset@delta.T;mass=np.where(bi==bone,bw,0).sum(1)
        result+=mass[:,None]*blend[:,None]*displacement
        # Include the blend derivative in the normal transform. Applying only
        # the interpolated radius matrices would shade this nonlinear warp wrong.
        linear+=mass[:,None,None]*(blend[:,None,None]*delta+displacement[:,:,None]*gradient[:,None,:])
    if leaf_axes and np.any(np.linalg.det(linear)<=1e-8):raise ValueError('Folded first-person radius differential')
    normal=np.einsum('ni,nij->nj',n,np.linalg.inv(linear));normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    if not np.isfinite(result).all() or not np.isfinite(normal).all():raise ValueError('Non-finite slimmed viewmodel')
    return result.astype('<f4'),normal.astype('<f4'),{'arm_radius_scale':arm_radius_scale,'hand_radius_scale':hand_radius_scale,'leaf_cap_axes':[names[b] for b in sorted(used) if names[b] in leaf_axes],'leaf_cap_transition':'smoothstep along distal segment' if leaf_axes else None,'joint_positions_and_native_skeleton_unchanged':True,'third_person_geometry_changed':False,'in_game_tested':False}
