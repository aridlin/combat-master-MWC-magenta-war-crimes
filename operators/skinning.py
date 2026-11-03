"""Skinned-mesh writer for existing Combat Master rigs; no animator replacement.

Infrastructure only: does not choose an operator, transfer arbitrary weights,
install assets, or claim that a character's deformations look correct in-game.
"""
import copy
import numpy as np
from catgun.bundle import mesh_tree

def validate_weights(indices,weights,vertices,bones):
    i=np.asarray(indices);w=np.asarray(weights,dtype='<f4')
    if i.shape!=(vertices,4) or w.shape!=(vertices,4):raise ValueError('Exactly four bone influences are required per exported vertex')
    if not 1<=bones<=256 or not np.isfinite(i).all() or not np.isfinite(w).all():raise ValueError('Unsupported bone count or non-finite skin data')
    if not np.equal(i,np.floor(i)).all() or np.any(i<0) or np.any(i>=bones):raise ValueError('Skin refers to a bone outside the target renderer')
    if np.any(w<0) or not np.allclose(w.sum(axis=1),1,atol=2e-5):raise ValueError('Bone weights must be nonnegative and normalized')
    return i.astype('u1'),w

def skinned_tree(template,mesh,name,indices,weights,bone_count):
    if len(template['m_BindPose'])!=bone_count:raise ValueError('Bind-pose and target renderer bone counts disagree')
    i,w=validate_weights(indices,weights,len(mesh.vertices),bone_count);d=mesh_tree(template,mesh,name)
    v,n,uv,f=mesh.arrays();packed=np.zeros(len(v),dtype=[('position','<f4',3),('normal','<f4',3),('tangent','<f4',4),('uv','<f4',2),('weights','<f4',4),('indices','u1',4)])
    packed['position']=v;packed['normal']=n;packed['tangent'][:,0]=1;packed['tangent'][:,3]=1;packed['uv']=uv;packed['weights']=w;packed['indices']=i
    assert packed.dtype.itemsize==68
    channels=d['m_VertexData']['m_Channels'];channels[12]={'stream':0,'offset':48,'format':0,'dimension':4};channels[13]={'stream':0,'offset':64,'format':6,'dimension':4};d['m_VertexData']['m_DataSize']=packed.tobytes()
    if 'm_Skin' in d:d['m_Skin']=[]
    # Preserve the exact target skeleton's inverse bind matrices and hashes.
    d['m_BindPose']=copy.deepcopy(template['m_BindPose']);d['m_BoneNameHashes']=copy.deepcopy(template['m_BoneNameHashes']);d['m_RootBoneNameHash']=template['m_RootBoneNameHash']
    return d

def cpu_skin(positions,indices,weights,pose_matrices,inverse_bind_matrices):
    """Independent deformation oracle for bind-pose and articulated-pose tests."""
    p=np.asarray(positions,dtype=float);i,w=validate_weights(indices,weights,len(p),len(pose_matrices));pose=np.asarray(pose_matrices);bind=np.asarray(inverse_bind_matrices)
    if pose.shape!=bind.shape or pose.shape[1:]!=(4,4):raise ValueError('Expected one 4x4 pose and inverse bind matrix per bone')
    transform=pose@bind;homogeneous=np.c_[p,np.ones(len(p))];result=np.zeros((len(p),4))
    for k in range(4):result+=np.einsum('nij,nj->ni',transform[i[:,k]],homogeneous)*w[:,k,None]
    return result[:,:3]
