"""Original pixel-style Overworld sky; continuous directional cube sampling.

Not extracted Mojang artwork. No environmental textures or scene lights changed.
Unity cubemap order is +X,-X,+Y,-Y,+Z,-Z. Encode each face via UnityPy.
"""
import numpy as np
from PIL import Image
NAMES=['positive-x','negative-x','positive-y','negative-y','positive-z','negative-z']
def colors(directions,night=False,assets=None):
    if assets is not None:
        from .minecraft import colors as vanilla_colors
        return vanilla_colors(directions,night,assets)
    d=np.asarray(directions,dtype=float);d=d/np.linalg.norm(d,axis=-1,keepdims=True)
    height=np.clip(d[...,1],0,1)[...,None]
    top=np.array([12,20,48] if night else [115,164,255]);horizon=np.array([39,47,72] if night else [190,218,255]);rgb=horizon*(1-height)+top*height
    sun=np.array([.45,.72,.35]);sun/=np.linalg.norm(sun);right=np.cross(sun,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,sun)
    front=d@sun;u=d@right;v=d@up;mask=(front>.99)&(np.abs(u)<.065)&(np.abs(v)<.065)
    if not night:rgb=np.where(mask[...,None],[255,255,225],rgb)
    else:
        moon=(front>.99)&(np.abs(u)<.065)&(np.abs(v)<.065);rgb=np.where(moon[...,None],[213,221,229],rgb)
    # Clouds lie on a distant horizontal plane, so neighboring cubemap faces
    # share exactly the same shape at their common viewing direction.
    safe=np.maximum(d[...,1],.04);x=np.floor(d[...,0]/safe*24).astype(np.int64);z=np.floor(d[...,2]/safe*24).astype(np.int64)
    # Large grouped rectangular cells with smaller internal square cut-outs.
    h=(np.floor_divide(x,4)*374761393+np.floor_divide(z,4)*668265263)&0xffffffff
    h=((h^(h>>13))*1274126177)&0xffffffff;h=h^(h>>16)
    notch=(x%4==0)&(z%4==0)&(((h>>8)&1)==1)
    cloud=(d[...,1]>.10)&(h%17<4)&~notch
    rgb=np.where(cloud[...,None],[60,66,85] if night else [247,249,255],rgb)
    # Keep the square celestial disc readable in the presence of cloud cells.
    rgb=np.where((moon if night else mask)[...,None],[213,221,229] if night else [255,255,225],rgb)
    return np.rint(np.clip(rgb,0,255)).astype(np.uint8)
def face_directions(face,u,v):
    one=np.ones_like(u)
    return np.stack([(one,-v,-u),(-one,-v,u),(u,one,v),(u,-one,-v),(u,-v,one),(-u,-v,-one)][face],axis=-1)
def faces(size=256,night=False,assets=None):
    if not 32<=size<=1024:raise ValueError('Skybox face size out of supported range')
    q=(np.arange(size)+.5)/size*2-1;u,v=np.meshgrid(q,q)
    return [Image.fromarray(colors(face_directions(i,u,v),night,assets)).convert('RGBA') for i in range(6)]
