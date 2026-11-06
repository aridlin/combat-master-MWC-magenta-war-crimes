"""Extract authored character arms and fit them to the native weapon arm rig.

Only mesh skin data is adapted. The game's camera, IK targets, weapon sockets,
80-bone skeleton and animation controllers remain untouched.
"""
import copy,re
import numpy as np
from .retarget import adapt,target_name,CENTRAL
from .skinning import validate_weights


def validate_assignments(assignments,targets):
    owners={}
    for target in targets:
        for renderer in target['renderers']:owners.setdefault(renderer['path_id'],[]).append(target['id'])
    for identifiers in owners.values():
        choices={assignments.get(i,'original') for i in identifiers}
        if len(choices)>1:raise ValueError('Shared first-person arms conflict: '+', '.join(identifiers)+'. Choose the same model for these operators or disable matching first-person arms.')


def arm_name(name):
    if not name:return None
    if re.fullmatch(r'(Scapula|Shoulder|Elbow|Wrist)_[LR]',name):return name
    match=re.fullmatch(r'(Shoulder|Elbow)Part[12]_([LR])',name)
    if match:return match[1]+'_'+match[2]
    match=re.fullmatch(r'((?:Thumb|Index|Middle|Ring|Pinky)Finger)([1234])_([LR])',name)
    if match:return match[1]+str(min(3,int(match[2])))+'_'+match[3]
    return None


def native_name(name):
    match=re.fullmatch(r'j_(clavicle|shoulder|elbow|hand)_([LR])',name)
    if match:return {'clavicle':'Scapula','shoulder':'Shoulder','elbow':'Elbow','hand':'Wrist'}[match[1]]+'_'+match[2]
    match=re.fullmatch(r'j_(thumb|index|mid|ring|pinky)_([123])_([LR])',name)
    if match:return {'thumb':'Thumb','index':'Index','mid':'Middle','ring':'Ring','pinky':'Pinky'}[match[1]]+'Finger'+match[2]+'_'+match[3]
    return 'unused_'+name


def fit(base,source_indices,source_weights,meta,source_bind,native,options,model=''):
    names=meta['bone_names'];semantics=options.get('source_targets')
    semantics={i:(semantics.get(i) if semantics is not None else target_name(name)) for i,name in enumerate(names)}
    arms={i:arm_name(name) for i,name in semantics.items()};bi=np.asarray(source_indices);bw=np.asarray(source_weights).copy()
    valid=np.array([arms[int(i)] is not None for i in range(len(names))]);bw*=valid[bi]
    coverage=bw.sum(1);faces=np.asarray(base.faces);selected=faces[np.all(coverage[faces]>=.85,axis=1)]
    if len(selected)<12:raise ValueError('Source has insufficient authored arm geometry')
    ids=np.unique(selected);remap=np.full(len(base.vertices),-1);remap[ids]=np.arange(len(ids));mesh=copy.deepcopy(base)
    mesh.vertices=np.asarray(base.vertices)[ids].tolist();mesh.normals=np.asarray(base.normals)[ids].tolist();mesh.uv=np.asarray(base.uv)[ids].tolist();mesh.faces=remap[selected].tolist();bi=bi[ids];bw=bw[ids]/coverage[ids,None]
    target_names=[native_name(n) for n in native['bone_names']];bind=native['inverse_bind'];rest=np.linalg.inv(bind);native_index={n:i for i,n in enumerate(target_names)}
    basis=np.asarray(options.get('source_basis',[[-1,0,0],[0,0,-1],[0,1,0]]),float);source_rest=np.linalg.inv(source_bind);sp=source_rest[:,:3,3]@basis.T
    primary=options.get('primary_sources') or {target_name(n):i for i,n in enumerate(names) if n in CENTRAL or re.fullmatch(r'bip_(collar|upperArm|lowerArm|hand|hip|knee|foot|toe)_[LR]',n)}
    ratios=[]
    for side in ('L','R'):
        for a,b in [('Shoulder','Elbow'),('Elbow','Wrist')]:
            a,b=a+'_'+side,b+'_'+side
            ratios.append(np.linalg.norm(rest[native_index[b],:3,3]-rest[native_index[a],:3,3])/np.linalg.norm(sp[primary[b]]-sp[primary[a]]))
    scale=float(np.median(ratios));head=rest[native['bone_names'].index('tag_camera'),:3,3];torso=rest[native['bone_names'].index('tag_torso'),:3,3];up=head-torso;up/=np.linalg.norm(up)
    source_root=options.get('source_root',names.index('bip_pelvis') if 'bip_pelvis' in names else None);source_head=options.get('source_head',names.index('bip_head') if 'bip_head' in names else None)
    if source_root is None or source_head is None:raise ValueError('Source torso landmarks missing')
    root=head-up*np.linalg.norm(sp[source_head]-sp[source_root])*scale
    virtual=np.repeat(np.eye(4)[None],2,axis=0);virtual[0,:3,3]=root;virtual[1,:3,3]=head
    extended=np.concatenate([bind,np.linalg.inv(virtual)]);target_names+=['Root_M','Head_M']
    mapping={i:arms[i] for i in range(len(names))};mapping[source_root]='Root_M';mapping[source_head]='Head_M'
    anchors={name:i for name,i in primary.items() if arms.get(i)==name};anchors.update(Root_M=source_root,Head_M=source_head)
    from .leaf_tips import REVIEWED_MODELS,tips
    leaf=tips(base,source_indices,source_weights,source_bind,native,options) if model in REVIEWED_MODELS else {}
    v,n,indices,weights,report=adapt(mesh.vertices,mesh.normals,names,source_bind,bi,bw,target_names,extended,source_targets=mapping,source_basis=options.get('source_basis'),primary_sources=anchors,source_root=source_root,source_head=source_head,fit_hands=options.get('fit_hands',False),wrist_transition=options.get('wrist_transition',False),source_faces=mesh.faces,leaf_tips=leaf)
    if leaf:report['finger_tip_fit']={'tips':list(leaf.values()),'native_skeleton_animations_unchanged':True,'source_skin_weights_unchanged':True,'method':'full 3D native distal mesh caps'}
    if np.any(indices>=len(bind)):raise ValueError('Virtual torso landmarks leaked into serialized arm weights')
    from .viewmodel import slim,settings
    v,n,volume=slim(v,n,indices,weights,native,**settings(model));report['viewmodel_volume']=volume
    mesh.vertices=v.tolist();mesh.normals=n.tolist()
    if np.linalg.det(basis)<0:mesh.faces=np.asarray(mesh.faces)[:,[0,2,1]].tolist()
    validate_weights(indices,weights,len(v),len(bind));report.update(authored_arm_triangles=len(selected),source_triangles=len(faces),native_bones_preserved=len(bind),virtual_landmarks_not_serialized=True,in_game_tested=False)
    return mesh,indices,weights,report
