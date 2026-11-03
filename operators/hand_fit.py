"""Anatomical palm frames for authored meshes with unusual hand proportions.

The native skeleton is unchanged. Fit palm length and roll from independent
middle/index/pinky landmarks instead of using torso scale for hand thickness.
"""
import numpy as np


def frame(wrist,middle,index,pinky):
    forward=np.asarray(middle,dtype=float)-wrist
    length=float(np.linalg.norm(forward))
    if length<1e-7:raise ValueError('Degenerate palm forward axis')
    forward/=length
    across=np.asarray(index,dtype=float)-pinky
    across-=forward*(across@forward)
    width=float(np.linalg.norm(across))
    if width<1e-7:raise ValueError('Degenerate palm lateral axis')
    across/=width;normal=np.cross(forward,across)
    return np.column_stack((forward,across,normal)),length,width


def fits(source_points,target_points,source_primary,target_index):
    result={}
    for side in ('L','R'):
        names=[n+'_'+side for n in ('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1')]
        if any(n not in source_primary or n not in target_index for n in names):
            raise ValueError('Hand fitting needs explicit palm landmarks: '+side)
        source,sl,sw=frame(*(source_points[source_primary[n]] for n in names))
        target,tl,tw=frame(*(target_points[target_index[n]] for n in names))
        rotation=target@source.T;scale=tl/sl
        if not np.isfinite(rotation).all() or not np.isfinite(scale) or not .01<scale<1000 or not np.isclose(np.linalg.det(rotation),1,atol=1e-6):
            raise ValueError('Invalid anatomical palm fit')
        result[side]={'rotation':rotation,'scale':scale,'source_length':sl,'target_length':tl,'source_width':sw,'target_width':tw}
    return result
