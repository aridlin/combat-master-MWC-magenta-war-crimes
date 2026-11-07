"""Coordinate conversion for private *evaluated* world-pose previews only.

Bind-mesh axes do not describe the axes of an animated renderer. Use its
evaluated local-to-world matrix, then convert Unity world Y-up to studio Z-up.
This module is not used by replacement fitting or game asset builders.
"""
import numpy as np


def preview_transform(renderer_to_world, units_per_m=1.):
    matrix=np.asarray(renderer_to_world,dtype=float)
    if matrix.shape!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3],[0,0,0,1],atol=1e-8,rtol=0):
        raise ValueError('Expected an affine renderer-to-world matrix')
    if not np.isfinite(units_per_m) or units_per_m<=0 or abs(np.linalg.det(matrix[:3,:3]))<1e-12:
        raise ValueError('Expected positive units and a nonsingular renderer frame')
    # Proper rotation: world +Y becomes studio +Z, world +Z becomes studio -Y.
    world_to_studio=np.array([[1.,0,0,0],[0,0,-1.,0],[0,1.,0,0],[0,0,0,1.]])
    world_to_studio[:3]/=units_per_m
    return world_to_studio@matrix


def transform_pose(positions,normals,posed_inverse_bind,renderer_to_world,units_per_m=1.):
    """Move posed mesh, normals and posed bone frames into one preview space.

    ``posed_inverse_bind`` is the inverse of the evaluated bone matrices in
    renderer space, not the mesh's original inverse bind pose. Arrays are copied.
    """
    p=np.asarray(positions,dtype=float);n=np.asarray(normals,dtype=float);bind=np.asarray(posed_inverse_bind,dtype=float)
    if p.ndim!=2 or p.shape[1]!=3 or n.shape!=p.shape or not np.isfinite(p).all() or not np.isfinite(n).all():
        raise ValueError('Expected finite posed positions and matching normals')
    if bind.ndim!=3 or bind.shape[1:]!=(4,4) or not np.isfinite(bind).all() or not np.allclose(bind[:,3],[0,0,0,1],atol=1e-7,rtol=0):
        raise ValueError('Expected finite affine posed inverse bone frames')
    matrix=preview_transform(renderer_to_world,units_per_m)
    vertices=(np.c_[p,np.ones(len(p))]@matrix.T)[:,:3]
    normal=n@np.linalg.inv(matrix[:3,:3]);length=np.linalg.norm(normal,axis=1,keepdims=True)
    if np.any(length<1e-12):raise ValueError('Posed normal has zero length')
    return vertices,normal/length,bind@np.linalg.inv(matrix)
