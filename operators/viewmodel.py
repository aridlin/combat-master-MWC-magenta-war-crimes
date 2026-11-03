"""Reduce first-person bulk without shortening native joint-to-joint reach."""
import json,re
from pathlib import Path
import numpy as np


def settings(model):
    spec=json.loads((Path(__file__).resolve().parents[1]/'config/operator-viewmodels.json').read_text());value={**spec['defaults'],**spec['models'].get(model,{})}
    if set(value)!={'arm_radius_scale','hand_radius_scale'} or any(type(v) not in (float,int) or not np.isfinite(v) or not .25<=v<=1.25 for v in value.values()):raise ValueError('Unsupported first-person radius scale')
    return value


def slim(positions,normals,indices,weights,native,arm_radius_scale,hand_radius_scale):
    from .first_person import native_name
    names=[native_name(n) for n in native['bone_names']];byname={n:i for i,n in enumerate(names)};points=np.linalg.inv(native['inverse_bind'])[:,:3,3];v=np.asarray(positions,dtype=float);n=np.asarray(normals,dtype=float);bi=np.asarray(indices);bw=np.asarray(weights);matrices=np.repeat(np.eye(3)[None],len(names),axis=0);translations=np.zeros((len(names),3));used=set(map(int,bi[bw>0]));next_joint={'Scapula':'Shoulder','Shoulder':'Elbow','Elbow':'Wrist','Wrist':'MiddleFinger1'}
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
    result=np.einsum('nij,nj->ni',linear,v)+translation;normal=np.einsum('ni,nij->nj',n,np.linalg.inv(linear));normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    if not np.isfinite(result).all() or not np.isfinite(normal).all():raise ValueError('Non-finite slimmed viewmodel')
    return result.astype('<f4'),normal.astype('<f4'),{'arm_radius_scale':arm_radius_scale,'hand_radius_scale':hand_radius_scale,'joint_positions_and_native_skeleton_unchanged':True,'third_person_geometry_changed':False,'in_game_tested':False}
