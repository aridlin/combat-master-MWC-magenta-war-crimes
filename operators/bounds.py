"""Skinned renderer bounds use root-bone space, not mesh vertex space."""
import numpy as np


def root_bounds(positions,inverse_bind,root_index,original):
    positions=np.asarray(positions,dtype=float);bind=np.asarray(inverse_bind,dtype=float)
    if positions.ndim!=2 or positions.shape[1]!=3 or not len(positions) or not np.isfinite(positions).all():raise ValueError('Invalid mesh positions for renderer bounds')
    if not 0<=root_index<len(bind) or bind.shape[1:]!=(4,4):raise ValueError('Invalid renderer root bone')
    local=(np.c_[positions,np.ones(len(positions))]@bind[root_index].T)[:,:3]
    center=np.array([original['m_Center'][k] for k in 'xyz']);extent=np.array([original['m_Extent'][k] for k in 'xyz']);low=np.minimum(local.min(0),center-extent);high=np.maximum(local.max(0),center+extent)
    # Keep the game's original animation envelope and add a small allowance for
    # the new shape. This is graphical culling only, never collider geometry.
    padding=max(float(np.max(high-low))*.02,1e-6);low-=padding;high+=padding
    # Unity serializes these fields as float32; retain exact field-whitelist
    # equality after save/reopen rather than comparing double intermediates.
    return {'m_Center':dict(zip('xyz',map(float,((low+high)/2).astype('<f4')))),'m_Extent':dict(zip('xyz',map(float,((high-low)/2).astype('<f4'))))}
