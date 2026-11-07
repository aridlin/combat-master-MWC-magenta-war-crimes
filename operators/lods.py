"""Authored world LODs: share LOD0's atlas when its UV coverage permits it."""
from pathlib import Path
import json,math
import numpy as np
from bundle_utils import digest
from .assets import load,ATLAS_TILE,ATLAS_GUTTER


def repair_missing_normals(mesh):
    """Fill only absent authored shading vectors from incident face winding.

    Compiled lower LODs can contain zero vectors (Demoman's mouth does). Keep
    valid authored normals verbatim, and reject geometry without a usable face.
    This changes shading data only, never vertices, topology, UVs or weights.
    """
    normals=np.asarray(mesh.normals,dtype=float)
    if not np.isfinite(normals).all():raise ValueError('Non-finite authored LOD normals')
    missing=np.linalg.norm(normals,axis=1)<1e-12
    if not missing.any():return 0
    vertices=np.asarray(mesh.vertices,dtype=float);faces=np.asarray(mesh.faces)
    area=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    accumulated=np.zeros_like(normals)
    for corner in range(3):np.add.at(accumulated,faces[:,corner],area)
    length=np.linalg.norm(accumulated[missing],axis=1)
    if np.any(length<1e-12):raise ValueError('Missing authored LOD normal has no usable incident face')
    normals[missing]=accumulated[missing]/length[:,None]
    mesh.normals=normals.tolist();return int(missing.sum())


def select_source(spec,native_levels,*,first_person=False):
    if first_person:return Path(spec.get('first_person_source',spec['source'])),0,None
    if not native_levels or any(type(level) is not int or level<0 for level in native_levels):
        raise ValueError('World LOD renderer has no valid native levels')
    sources=spec.get('lod_sources',{})
    if not isinstance(sources,dict) or any(not isinstance(k,str) or not k.isdigit() or str(int(k))!=k or not 1<=int(k)<8 for k in sources):
        raise ValueError('Authored LOD source keys must be consecutive integers starting at 1')
    if not sources:return Path(spec['source']),0,None
    levels=sorted(map(int,sources))
    if levels!=list(range(1,max(levels)+1)):raise ValueError('Authored LOD source sequence has gaps')
    # A shared renderer must retain the most detailed level that references it.
    # Beyond the available sources, keep the last authored source explicitly.
    chosen=min(min(native_levels),max(levels))
    return (Path(sources[str(chosen)]),chosen,Path(spec['source'])) if chosen else (Path(spec['source']),0,None)


def load_lod(source,reference,style='original',pattern_config=None):
    """Use authored reduced geometry and preserve the material's UV coverage.

    A lower LOD can omit materials. Packing it into a smaller atlas would make
    its UVs sample the wrong pixels on the renderer's shared body material.
    Broader authored UV coverage keeps that LOD's own correctly tiled atlas.
    The builder gives it a separate visual material; no UVs are clamped.
    """
    source,reference=Path(source),Path(reference)
    mesh,own_image,bi,bw,meta=load(source,style,pattern_config)
    _,image,_,_,ref=load(reference,style,pattern_config)
    if meta.get('prepacked') or ref.get('prepacked') or meta.get('id')!=ref.get('id') or meta.get('source_variant')!='world' or ref.get('source_variant')!='world':
        raise ValueError('Authored world LOD requires matching unpacked local model sources')
    if type(meta.get('source_lod')) is not int or not 1<=meta['source_lod']<8:
        raise ValueError('Reduced source lacks an explicit authored LOD identity')
    meta={**meta,'missing_authored_normals_reconstructed':repair_missing_normals(mesh)}
    with np.load(source/'source.npz',allow_pickle=False) as d,np.load(reference/'source.npz',allow_pickle=False) as rd:
        if meta['bone_names']!=ref['bone_names'] or not np.array_equal(d['inverse_bind'],rd['inverse_bind']) or not np.array_equal(d['bone_parents'],rd['bone_parents']):
            raise ValueError('Authored LOD skeleton differs from the LOD0 source')
        uv=d['uv'].copy();faces=d['faces'];fm=d['face_materials'];refuv=rd['uv'];reffaces=rd['faces'];reffm=rd['face_materials']
        names=[m['name'] for m in ref['materials']]
        if len(set(names))!=len(names) or len({m['name'] for m in meta['materials']})!=len(meta['materials']):raise ValueError('LOD materials are ambiguous')
        cols=math.ceil(math.sqrt(len(names)));rows=math.ceil(len(names)/cols);stride=ATLAS_TILE+2*ATLAS_GUTTER;mapped=uv.copy();assigned=np.zeros(len(uv),bool);own_atlas=False
        for mi,material in enumerate(meta['materials']):
            ids=np.unique(faces[fm==mi].ravel())
            if not len(ids):continue
            if material['name'] not in names:raise ValueError('Authored LOD uses a material absent from LOD0')
            slot=names.index(material['name']);original=ref['materials'][slot]
            if material.get('base_color_linear')!=original.get('base_color_linear') or material.get('alpha_mode')!=original.get('alpha_mode') or 'pixels' not in material or 'pixels' not in original or digest(source/material['pixels'])!=digest(reference/original['pixels']):
                raise ValueError('Authored LOD material differs from the LOD0 palette')
            reference_ids=np.unique(reffaces[reffm==slot].ravel())
            if not len(reference_ids):raise ValueError('Authored LOD material has no LOD0 UV reference')
            lower=np.floor(refuv[reference_ids].min(0));upper=np.maximum(np.ceil(refuv[reference_ids].max(0)),lower+1)
            if np.any(uv[ids]<lower-1e-6) or np.any(uv[ids]>upper+1e-6):own_atlas=True
            if assigned[ids].any():raise ValueError('Authored LOD must split material-boundary vertices')
            local=(uv[ids]-lower)/(upper-lower);x,y=(slot%cols)*stride,(slot//cols)*stride
            mapped[ids,0]=(x+ATLAS_GUTTER+local[:,0]*ATLAS_TILE)/image.width
            mapped[ids,1]=1-(y+ATLAS_GUTTER+(1-local[:,1])*ATLAS_TILE)/image.height;assigned[ids]=True
        if not assigned.all():raise ValueError('Authored LOD has unassigned material vertices')
    if image.size!=(cols*stride,rows*stride):raise ValueError('Unexpected LOD0 atlas dimensions')
    if own_atlas:return mesh,own_image,bi,bw,{**meta,'shared_lod0_atlas':False,'independent_lod_atlas_reason':'authored_uv_extent'}
    mesh.uv=mapped.tolist();return mesh,image,bi,bw,{**meta,'shared_lod0_atlas':True}
