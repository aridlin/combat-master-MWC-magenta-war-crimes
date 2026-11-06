"""Experimental variable-weight codec checked against Unity-authored reference data.

Not enabled by any installer module. A native-player import is insufficient to
prove that the renderer consumes every influence or produces an acceptable grip.
The production four-weight writer remains the default.
"""
import numpy as np

TOTAL=65535


def _count(value,low,high,label):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,np.integer)) or not low<=value<=high:
        raise ValueError('Invalid '+label)
    return int(value)


def _integers(values,label):
    values=np.asarray(values)
    if values.dtype.kind not in 'iuf' or not np.isfinite(values).all() or not np.equal(values,np.floor(values)).all():
        raise ValueError('Expected finite integer '+label)
    return values


def quantize(values):
    values=np.asarray(values,float)
    if values.ndim!=1 or not len(values) or not np.isfinite(values).all() or np.any(values<=0) or abs(values.sum()-1)>2e-5:
        raise ValueError('Expected finite positive normalized weights')
    scaled=values/values.sum()*TOTAL
    result=np.floor(scaled).astype(np.int64)
    remainder=TOTAL-int(result.sum())
    order=np.argsort(-(scaled-result),kind='stable')
    result[order[:remainder]]+=1
    if result.sum()!=TOTAL or np.any(result<0):raise ValueError('Invalid quantized weight mass')
    return result


def encode(indices,weights,bone_count):
    indices=_integers(indices,'bone indices');weights=np.asarray(weights,float)
    bone_count=_count(bone_count,1,65536,'bone count')
    if indices.shape!=weights.shape or indices.ndim!=2 or not len(indices) or not 1<=indices.shape[1]<=255 or not 1<=bone_count<=65536:
        raise ValueError('Invalid variable skin dimensions')
    if not np.isfinite(indices).all() or not np.equal(indices,np.floor(indices)).all() or np.any(indices<0) or np.any(indices>=bone_count):
        raise ValueError('Variable skin bone outside rig')
    if not np.isfinite(weights).all() or np.any(weights<0) or not np.allclose(weights.sum(1),1,atol=2e-5,rtol=0):
        raise ValueError('Invalid variable skin weights')
    offsets=[len(indices)+1];packed=[]
    for vi,vw in zip(indices,weights):
        keep=np.flatnonzero(vw>0);keep=keep[np.argsort(-vw[keep],kind='stable')]
        bones=vi[keep].astype(np.uint32)
        if len(set(map(int,bones)))!=len(bones):raise ValueError('Duplicate positive bone influence')
        q=quantize(vw[keep]);nonzero=q>0;bones=bones[nonzero];q=q[nonzero]
        order=np.argsort(-q,kind='stable');bones=bones[order];q=q[order]
        packed.extend(map(int,(q.astype(np.uint32)<<16)|bones));offsets.append(len(indices)+1+len(packed))
    return offsets+packed


def decode(data,vertices,bone_count):
    vertices=_count(vertices,1,0xfffffffd,'vertex count')
    bone_count=_count(bone_count,1,65536,'bone count')
    data=_integers(data,'packed data')
    if vertices<1 or not 1<=bone_count<=65536 or data.ndim!=1 or len(data)<vertices+2 or not np.isfinite(data).all() or not np.equal(data,np.floor(data)).all() or np.any(data<0) or np.any(data>0xffffffff):
        raise ValueError('Invalid variable skin data')
    data=data.astype(np.uint32);offsets=data[:vertices+1].astype(np.int64)
    if offsets[0]!=vertices+1 or offsets[-1]!=len(data) or np.any(np.diff(offsets)<1) or np.any(np.diff(offsets)>255):
        raise ValueError('Invalid variable skin offsets or influence counts')
    count=int(np.diff(offsets).max());indices=np.zeros((vertices,count),dtype=np.uint16);weights=np.zeros((vertices,count),float)
    for v,(start,end) in enumerate(zip(offsets[:-1],offsets[1:])):
        words=data[start:end];bones=words&65535;q=words>>16
        if np.any(bones>=bone_count) or np.any(q==0) or q.sum()!=TOTAL or np.any(q[1:]>q[:-1]) or len(set(map(int,bones)))!=len(bones):
            raise ValueError('Invalid variable skin indices, order or weight mass')
        indices[v,:len(words)]=bones;weights[v,:len(words)]=q/TOTAL
    return indices,weights


def fallback(indices,weights):
    indices=_integers(indices,'bone indices');weights=np.asarray(weights,float)
    if indices.ndim!=2 or indices.shape!=weights.shape or not len(indices) or not 1<=indices.shape[1]<=255:
        raise ValueError('Invalid fallback skin dimensions')
    if np.any(indices<0) or not np.isfinite(weights).all() or np.any(weights<0) or not np.allclose(weights.sum(1),1,atol=2e-5,rtol=0):
        raise ValueError('Invalid fallback skin field')
    result_i=np.zeros((len(indices),4),np.uint8);result_w=np.zeros((len(indices),4),np.float32)
    if np.max(indices)>255:raise ValueError('Current mesh writer supports at most 256 bones')
    for v,(vi,vw) in enumerate(zip(indices,weights)):
        if len(set(map(int,vi[vw>0])))!=np.count_nonzero(vw):raise ValueError('Duplicate positive bone influence')
        take=np.flatnonzero(vw>0);take=take[np.argsort(-vw[take],kind='stable')][:4]
        q=quantize(vw[take]/vw[take].sum());result_i[v,:len(take)]=vi[take];result_w[v,:len(take)]=q/TOTAL
    return result_i,result_w


def skinned_tree_variable(template,mesh,name,indices,weights,bone_count):
    from .skinning import skinned_tree
    data=encode(indices,weights,bone_count);indices,weights=decode(data,len(mesh.vertices),bone_count)
    fi,fw=fallback(indices,weights)
    result=skinned_tree(template,mesh,name,fi,fw,bone_count)
    if 'm_VariableBoneCountWeights' not in result:raise ValueError('Target mesh has no variable-weight field')
    result['m_VariableBoneCountWeights']={'m_Data':data}
    # Full skin data, not just the four-weight fallback, defines bone bounds.
    if 'm_BonesAABB' in result:
        bind=np.array([[[p['e'+str(a)+str(b)] for b in range(4)] for a in range(4)] for p in result['m_BindPose']]);points=np.c_[mesh.vertices,np.ones(len(mesh.vertices))];bounds=[]
        for bone in range(bone_count):
            keep=np.any((indices==bone)&(weights>0),axis=1)
            if keep.any():
                p=(points[keep]@bind[bone].T)[:,:3];low=p.min(0)-.002;high=p.max(0)+.002
            else:low=np.full(3,np.inf);high=np.full(3,-np.inf)
            bounds.append({'m_Min':dict(zip('xyz',map(float,low))),'m_Max':dict(zip('xyz',map(float,high)))})
        result['m_BonesAABB']=bounds
    return result,fi,fw
