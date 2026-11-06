"""Fit landmarks for actual local TF2 arm sources, without adding geometry.

Arm-only sources lack the shared fitter's two bookkeeping references. These
can come from a verified common world frame or be constructed from the actual
arm segments. Authored bind rotations, geometry and skin remain unchanged.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from .skinning import validate_weights


def add_landmarks(source,world):
    source,world=Path(source),Path(world)
    meta=json.loads((source/'source.json').read_text())
    reference=json.loads((world/'source.json').read_text())
    if meta.get('source_variant')!='first_person_arms' or meta['id']!=reference['id']:
        raise ValueError('TF2 arm landmarks require the same class and an explicit arm source')
    with np.load(source/'source.npz',allow_pickle=False) as data:
        arrays={k:data[k].copy() for k in data.files}
    with np.load(world/'source.npz',allow_pickle=False) as data:
        world_bind=data['inverse_bind'].copy()
    names=meta['bone_names'];world_names=reference['bone_names']
    if len(set(names))!=len(names) or len(set(world_names))!=len(world_names):
        raise ValueError('Ambiguous TF2 arm landmark names')
    bind=arrays['inverse_bind'];parents=arrays['bone_parents']
    if bind.shape!=(len(names),4,4) or world_bind.shape!=(len(world_names),4,4) or not np.isfinite(bind).all() or not np.isfinite(world_bind).all():
        raise ValueError('Invalid TF2 arm landmark matrices')
    if parents.shape!=(len(names),) or not np.array_equal(parents,meta['bone_parents']):
        raise ValueError('TF2 arm source hierarchy mismatch')
    indices,weights=arrays['bone_indices'],arrays['bone_weights']
    if indices.ndim!=2 or indices.shape!=weights.shape or not 1<=indices.shape[1]<=4:
        raise ValueError('Invalid TF2 source skin dimensions')
    # Source VVD has three slots; the native mesh writer requires four. Pad
    # only the validation copies, retaining the authored source arrays exactly.
    pad=((0,0),(0,4-indices.shape[1]))
    validate_weights(np.pad(indices,pad),np.pad(weights,pad),len(arrays['positions']),len(names))
    anchors=['bip_pelvis','bip_head']
    required=['bip_'+joint+'_'+side for side in ('L','R') for joint in ('upperArm','lowerArm','hand')]
    if set(anchors)&set(names) or not set(anchors+required)<=set(world_names) or not set(required)<=set(names):
        raise ValueError('Missing or already-added TF2 arm landmarks')
    arm_rest=np.linalg.inv(bind);world_rest=np.linalg.inv(world_bind)
    error=max(float(np.abs(arm_rest[names.index(n),:3,3]-world_rest[world_names.index(n),:3,3]).max()) for n in required)
    if error>1e-3:raise ValueError('Unreviewed TF2 arm/world coordinate mismatch')
    original_hash=hashlib.sha256((source/'source.npz').read_bytes()).hexdigest()
    arrays['inverse_bind']=np.concatenate([bind,np.stack([world_bind[world_names.index(n)] for n in anchors])])
    arrays['bone_parents']=np.r_[parents,[-1,-1]].astype('<i4')
    meta['bone_names']=names+anchors;meta['bone_parents']=arrays['bone_parents'].tolist()
    meta['fit_landmarks']={'names':anchors,'unweighted_only':True,
        'arm_landmark_position_error':error,'authored_bind_rotations_preserved':True,
        'authored_geometry_and_skin_preserved':True,'source_mesh_sha256':original_hash,
        'world_reference_sha256':hashlib.sha256((world/'source.npz').read_bytes()).hexdigest()}
    np.savez_compressed(source/'source.npz',**arrays)
    (source/'source.json').write_text(json.dumps(meta,indent=2)+'\n')
    return source


def add_virtual_landmarks(source,*,expected_model=None):
    """Add unweighted fit references for arm-only rigs with their own bind pose.

    first_person.fit derives scale from the real arm segments. Its auxiliary
    torso distance cancels in that calculation; it is not a body-pose match.
    These two references never become native skin bones or visible geometry.
    """
    source=Path(source);meta=json.loads((source/'source.json').read_text())
    allowed={'tf2_'+n for n in ('scout','soldier','pyro','demoman','heavy','engineer','medic','sniper','spy')}
    if meta.get('source_variant')!='first_person_arms' or meta.get('id') not in allowed:
        raise ValueError('Virtual arm references require a reviewed TF2 first-person source')
    if expected_model is not None and meta['id']!=expected_model:
        raise ValueError('TF2 first-person source does not match the selected class')
    with np.load(source/'source.npz',allow_pickle=False) as data:arrays={k:data[k].copy() for k in data.files}
    names=meta['bone_names'];bind=arrays['inverse_bind'];parents=arrays['bone_parents'];anchors=['bip_pelvis','bip_head']
    required=['bip_'+joint+'_'+side for side in ('L','R') for joint in ('upperArm','lowerArm','hand')]
    if len(set(names))!=len(names) or set(anchors)&set(names) or not set(required)<=set(names):
        raise ValueError('Missing, ambiguous or already-added virtual arm references')
    if bind.shape!=(len(names),4,4) or not np.isfinite(bind).all() or parents.shape!=(len(names),) or not np.array_equal(parents,meta['bone_parents']) or np.any(parents < -1) or np.any(parents>=len(names)):
        raise ValueError('Invalid arm reference hierarchy or bind matrices')
    for index in range(len(names)):
        seen=set()
        while index>=0:
            if index in seen:raise ValueError('Cyclic arm reference hierarchy')
            seen.add(index);index=int(parents[index])
    indices,weights=arrays['bone_indices'],arrays['bone_weights']
    if indices.ndim!=2 or indices.shape!=weights.shape or not 1<=indices.shape[1]<=4:raise ValueError('Invalid arm source skin dimensions')
    pad=((0,0),(0,4-indices.shape[1]));validate_weights(np.pad(indices,pad),np.pad(weights,pad),len(arrays['positions']),len(names))
    rest=np.linalg.inv(bind);segments=[]
    for side in ('L','R'):
        points=[rest[names.index('bip_'+joint+'_'+side),:3,3] for joint in ('upperArm','lowerArm','hand')]
        segments.extend(float(np.linalg.norm(b-a)) for a,b in zip(points,points[1:]))
    if not np.isfinite(segments).all() or min(segments)<1e-5:raise ValueError('Degenerate authored arm reference segments')
    origin=np.mean([rest[names.index('bip_upperArm_'+side),:3,3] for side in ('L','R')],axis=0)
    reference_length=2*float(np.median(segments));virtual=np.repeat(np.eye(4,dtype='<f4')[None],2,axis=0)
    virtual[0,:3,3]=-origin;virtual[1,:3,3]=-(origin+[0,reference_length,0])
    source_hash=hashlib.sha256((source/'source.npz').read_bytes()).hexdigest()
    arrays['inverse_bind']=np.concatenate([bind,virtual]);arrays['bone_parents']=np.r_[parents,[-1,-1]].astype('<i4')
    meta['bone_names']=names+anchors;meta['bone_parents']=arrays['bone_parents'].tolist()
    meta['fit_landmarks']={'names':anchors,'kind':'virtual_arm_fit_references','unweighted_only':True,
        'authored_bind_rotations_preserved':True,'authored_geometry_and_skin_preserved':True,
        'source_mesh_sha256':source_hash,'reference_length':reference_length,
        'actual_scale_from_authored_arm_segments':True,'world_pose_assumed':False}
    np.savez_compressed(source/'source.npz',**arrays);(source/'source.json').write_text(json.dumps(meta,indent=2)+'\n')
    return source
