"""Rest-pose adaptation to an existing skeleton, retaining source skin weights.

Uses joint positions rather than assuming matching bone-axis conventions.
Does not change the target skeleton or any animation/controller.
"""
import re
import numpy as np

CENTRAL={'bip_pelvis':'Root_M','bip_spine_0':'Spine1_M','bip_spine_1':'Spine2_M','bip_spine_2':'Chest_M','bip_spine_3':'Chest_M','bip_neck':'Neck_M','bip_head':'Head_M','bip_jaw':'Jaw_M'}
LIMBS={'collar':'Scapula','upperArm':'Shoulder','lowerArm':'Elbow','hand':'Wrist','hip':'Hip','knee':'Knee','foot':'Ankle','toe':'Toes','hlp_forearm':'ElbowPart2'}
NEXT={'Root_M':'Spine1_M','Spine1_M':'Spine2_M','Spine2_M':'Chest_M','Chest_M':'Neck_M','Neck_M':'Head_M','Head_M':'HeadEnd_M','Scapula':'Shoulder','Shoulder':'Elbow','Elbow':'Wrist','Wrist':'MiddleFinger1','Hip':'Knee','Knee':'Ankle','Ankle':'Toes','Toes':'ToesEnd'}


def native_frame(names,inverse_bind):
    """Known shipped mesh frames: metres/Z-up or centimetres/Y-up.

    Bone names alone do not imply a common mesh coordinate system. Skeletons
    and renderer transforms stay untouched; source geometry follows each mesh.
    """
    names=[n.split(':')[-1].removeprefix('soldier_') for n in names];p=np.linalg.inv(inverse_bind)[:,:3,3];up=p[names.index('Head_M')]-p[names.index('Root_M')];length=np.linalg.norm(up)
    if length<1e-6:raise ValueError('Degenerate native torso')
    axis=up/length
    if axis[2]>.95:frame=np.eye(3)
    elif axis[1]>.95:frame=np.array([[1.,0,0],[0,0,1],[0,-1,0]])
    else:raise ValueError('Unreviewed native mesh coordinate frame')
    return frame,100. if length>10 else 1.


def target_name(source):
    if source in CENTRAL:return CENTRAL[source]
    m=re.fullmatch(r'bip_(collar|upperArm|lowerArm|hand|hip|knee|foot|toe)_([LR])',source)
    if m:return LIMBS[m[1]]+'_'+m[2]
    m=re.fullmatch(r'hlp_forearm_([LR])',source)
    if m:return 'ElbowPart2_'+m[1]
    m=re.fullmatch(r'bip_(thumb|index|middle|ring|pinky)_([012])_([LR])',source)
    if m:return m[1].title()+'Finger'+str(int(m[2])+1)+'_'+m[3]
    if source.startswith(('bip_grenade','bip_jacketcollar','bip_stomachpouch')):return 'Chest_M'
    if source.startswith(('bip_crotchflap','bip_hippouch')):return 'Root_M'
    m=re.fullmatch(r'hlp_(suitArmTop|suitArmpitBack|thigh)_([LR])',source)
    if m:return ('Shoulder' if m[1]!='thigh' else 'Hip')+'_'+m[2]
    # Loose secondary accessories follow their actual anatomical region.
    if source.startswith(('bip_pack','bip_dogtag','medal_bone','prp_','prp_buckle','bip_tie','bip_cig','bip_hat')):return 'Chest_M' if not source.startswith(('bip_cig','bip_hat')) else 'Head_M'
    return None


def rotation_between(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float);a/=np.linalg.norm(a);b/=np.linalg.norm(b);c=np.clip(a@b,-1,1);v=np.cross(a,b)
    if c<-.999999:
        axis=np.cross(a,[1.,0.,0.] if abs(a[0])<.9 else [0.,1.,0.]);axis/=np.linalg.norm(axis)
        return 2*np.outer(axis,axis)-np.eye(3)
    k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+k+k@k/(1+c)


def adapt(positions,normals,source_names,source_inverse_bind,source_indices,source_weights,target_names,target_inverse_bind,*,source_targets=None,source_basis=None,primary_sources=None,source_root=None,source_head=None):
    # Compiled TF2 reference pose: +Y up, +X character-left. Combat Master's
    # renderer-local bind pose: +Z up, -X character-left, -Y forward.
    basis=np.asarray(source_basis if source_basis is not None else [[-1.,0.,0.],[0.,0.,-1.],[0.,1.,0.]])
    if basis.shape!=(3,3) or not np.allclose(basis.T@basis,np.eye(3),atol=1e-6):raise ValueError('Expected an orthogonal source coordinate basis')
    frame,native_units=native_frame(target_names,target_inverse_bind);basis=frame@basis
    p=np.asarray(positions)@basis.T;n=np.asarray(normals)@basis.T
    source_indices=np.asarray(source_indices);source_weights=np.asarray(source_weights)
    if source_indices.shape!=source_weights.shape or source_indices.ndim!=2 or source_indices.shape[0]!=len(p) or not 1<=source_indices.shape[1]<=4:raise ValueError('Invalid source skin dimensions')
    if not np.isfinite(source_indices).all() or not np.isfinite(source_weights).all() or np.any(source_weights<0) or not np.allclose(source_weights.sum(1),1,atol=1e-4):raise ValueError('Invalid source weights')
    if np.any(source_indices<0) or np.any(source_indices>=len(source_names)) or not np.equal(source_indices,np.floor(source_indices)).all():raise ValueError('Source skin index outside skeleton')
    source_rest=np.linalg.inv(source_inverse_bind);sp=source_rest[:,:3,3]@basis.T
    target_rest=np.linalg.inv(target_inverse_bind);tp=target_rest[:,:3,3]
    clean=[name.split(':')[-1].removeprefix('soldier_') for name in target_names]
    target={name:i for i,name in enumerate(clean)}
    semantics=[source_targets.get(i) if source_targets is not None else target_name(name) for i,name in enumerate(source_names)]
    mapped=[target.get(name,-1) for name in semantics]
    used=set(map(int,np.asarray(source_indices)[np.asarray(source_weights)>0]))
    missing=[source_names[i] for i in used if mapped[i]<0]
    if missing:raise ValueError('Unmapped weighted source bones: '+', '.join(missing))
    source_by_name={name:i for i,name in enumerate(source_names)}
    source_head=source_by_name['bip_head'] if source_head is None else source_head;source_root=source_by_name['bip_pelvis'] if source_root is None else source_root
    scale=np.linalg.norm(tp[target['Head_M']]-tp[target['Root_M']])/np.linalg.norm(sp[source_head]-sp[source_root])
    if not 1e-5<scale/native_units<100:raise ValueError('Unexpected source-to-Combat-Master scale')
    torso_linear=rotation_between(sp[source_head]-sp[source_root],tp[target['Head_M']]-tp[target['Root_M']])*scale
    torso_offset=tp[target['Root_M']]-torso_linear@sp[source_root]
    transformed=np.zeros_like(p,dtype=float);transformed_n=np.zeros_like(n,dtype=float)
    matrices=[]
    for i,name in enumerate(source_names):
        ti=mapped[i]
        if ti<0:matrices.append(None);continue
        tn=clean[ti];split=tn.rsplit('_',1);base=split[0] if len(split)==2 and split[1] in ('L','R') else tn
        # Preserve authored torso/head proportions as one continuous region.
        # Source rigs have different numbers of spine helpers; collapsing two
        # weighted spine joints onto a single native anchor tears coats/vests.
        if tn in ('Root_M','Spine1_M','Spine2_M','Chest_M','Neck_M','Head_M','Jaw_M'):
            matrices.append((torso_linear,torso_offset));continue
        child_name=NEXT.get(base)
        # Some rigs have a nearly zero-length pelvis/lower-spine helper. Never
        # use that tiny segment to stretch an entire tunic or belt vertically.
        if tn in ('Root_M','Spine1_M','Spine2_M'):child_name='Chest_M'
        if child_name and len(split)==2 and split[1] in ('L','R'):child_name+='_'+split[1]
        finger=re.fullmatch(r'(.+Finger)([123])_([LR])',tn)
        if finger:child_name=finger[1]+str(int(finger[2])+1)+'_'+finger[3]
        # Find the source joint representing that child's target joint.
        candidates=[j for j,tj in enumerate(mapped) if child_name and tj==target.get(child_name,-2) and np.linalg.norm(sp[j]-sp[i])>1e-5]
        linear=np.eye(3)*scale
        if candidates:
            child=min(candidates,key=lambda j:np.linalg.norm(sp[j]-sp[i]));a=sp[child]-sp[i];b=tp[target[child_name]]-tp[ti]
            if np.linalg.norm(b)>1e-6:
                direction=a/np.linalg.norm(a);ratio=np.clip(np.linalg.norm(b)/(np.linalg.norm(a)*scale),.4,2.5)
                if tn.endswith('_M'):ratio=1.
                linear=rotation_between(a,b)@(np.eye(3)+(ratio-1)*np.outer(direction,direction))*scale
        matrices.append((linear,tp[ti]-linear@sp[i]))
    # Accessory roots keep their offset from the torso/limb instead of collapsing
    # each pouch, grenade and collar onto the same target joint.
    primary=primary_sources if primary_sources is not None else {target_name(name):i for i,name in enumerate(source_names) if name in CENTRAL or re.fullmatch(r'bip_(collar|upperArm|lowerArm|hand|hip|knee|foot|toe)_[LR]',name)}
    for i,name in enumerate(source_names):
        semantic=semantics[i]
        if semantic in primary and i!=primary[semantic] and (source_targets is not None or name not in CENTRAL):
            anchor=primary[semantic];linear,_=matrices[anchor]
            u,_,vt=np.linalg.svd(linear);rigid=(u@vt)*scale
            matrices[i]=(rigid,tp[mapped[anchor]]-rigid@sp[anchor])
    indices=np.asarray(source_indices);weights=np.asarray(source_weights)
    for k in range(indices.shape[1]):
        for i in used:
            mask=(indices[:,k]==i)&(weights[:,k]>0)
            if not mask.any():continue
            linear,offset=matrices[i];w=weights[mask,k,None]
            transformed[mask]+=(p[mask]@linear.T+offset)*w
            transformed_n[mask]+=(n[mask]@np.linalg.inv(linear))*w
    transformed_n/=np.maximum(np.linalg.norm(transformed_n,axis=1,keepdims=True),1e-12)
    out_indices=np.zeros((len(p),4),dtype=np.uint8);out_weights=np.zeros((len(p),4),dtype=np.float32)
    for v,(vi,vw) in enumerate(zip(indices,weights)):
        merged={}
        for bi,w in zip(vi,vw):
            if w>0:merged[mapped[int(bi)]]=merged.get(mapped[int(bi)],0)+float(w)
        for k,(bi,w) in enumerate(sorted(merged.items(),key=lambda x:-x[1])):out_indices[v,k]=bi;out_weights[v,k]=w
    if not np.isfinite(transformed).all() or not np.allclose(out_weights.sum(1),1,atol=1e-4):raise ValueError('Invalid adapted geometry or skin')
    return transformed.astype('<f4'),transformed_n.astype('<f4'),out_indices,out_weights,{'scale':float(scale),'mapped_weighted_bones':len(used),'target_bones':len(target_names),'native_frame':frame.tolist(),'method':'joint-based rest-pose fitting in exact native mesh frame; visual and animation acceptance required'}
