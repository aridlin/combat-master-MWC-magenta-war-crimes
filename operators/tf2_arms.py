"""Fit landmarks for actual local TF2 arm sources, without adding geometry.

The shared fitter uses a torso distance to establish scale. Arm-only sources
lack those landmarks. Copy two unweighted reference nodes from the same
class's world rig after checking their common arm coordinate frame. Authored
arm bind rotations, geometry and every skin influence remain unchanged.
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
