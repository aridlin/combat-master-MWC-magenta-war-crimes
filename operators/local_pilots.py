"""Verified private source cache for locally imported Titanfall 2 pilots.

Three data files per model; no executable plugins, downloads or bundled EA data.
"""
import hashlib,json,shutil,tempfile,uuid,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from model_import.titanfall2 import MODELS
from .assets import load
from .profiles import profile
from .skinning import validate_weights

FILES={'source.json','source.npz','albedo.png'}


def verify(source,model):
    source=Path(source)
    if model not in MODELS:raise ValueError('Unknown native Titanfall pilot')
    if not source.is_dir() or {p.name for p in source.iterdir()}!=FILES:raise ValueError('Local pilot package must contain exactly source.json, source.npz and albedo.png')
    for name in FILES:
        p=source/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>32*1024*1024:raise ValueError('Unsupported local pilot package file: '+name)
    if (source/'source.json').stat().st_size>1024*1024:raise ValueError('Local pilot metadata exceeds limit')
    header=json.loads((source/'source.json').read_text())
    for filename,field in (('source.npz','mesh_sha256'),('albedo.png','albedo_sha256')):
        if hashlib.sha256((source/filename).read_bytes()).hexdigest()!=header.get(field):
            raise ValueError('Packaged operator source hash mismatch: '+filename)
    expected_arrays={name+'.npy' for name in ('positions','normals','uv','faces','face_materials','bone_indices','bone_weights','inverse_bind','bone_parents')}
    with zipfile.ZipFile(source/'source.npz') as archive:
        entries=archive.infolist()
        if len(entries)!=len(expected_arrays) or {row.filename for row in entries}!=expected_arrays or sum(row.file_size for row in entries)>64*1024*1024:
            raise ValueError('Local pilot array archive exceeds supported layout/size')
    with Image.open(source/'albedo.png') as image:
        if not 0<image.width<=4096 or not 0<image.height<=4096:raise ValueError('Local pilot atlas exceeds size limit')
    mesh,image,indices,weights,meta=load(source)
    if meta.get('id')!=model or meta.get('source_model')!=MODELS[model][0] or meta.get('profile')!='titanfall2_native' or not meta.get('prepacked'):raise ValueError('Local pilot identity/profile does not match selected model')
    profile('titanfall2_native',meta)
    if indices is None or weights is None or indices.shape!=weights.shape or indices.ndim!=2 or not 1<=indices.shape[1]<=4:
        raise ValueError('Invalid local pilot source influences')
    # Source VVD has three influence slots; the Unity export has four. Pad
    # only this validation view, preserving the authored package unchanged.
    padding=((0,0),(0,4-indices.shape[1]))
    validate_weights(np.pad(indices,padding),np.pad(weights,padding),len(mesh.vertices),len(meta['bone_names']))
    with np.load(source/'source.npz',allow_pickle=False) as data:
        if data['inverse_bind'].shape!=(len(meta['bone_names']),4,4) or not np.isfinite(data['inverse_bind']).all():raise ValueError('Invalid local pilot bind matrices')
    return {name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in sorted(FILES)}


def sources(config,required):
    requested=set(required)&MODELS.keys();result={}
    if not requested:return result
    root=config.get('titanfall2_source_root')
    if not root:raise ValueError('Import native Titanfall 2 pilot sources before selecting these models')
    for model in sorted(requested):
        path=Path(root)/model;verify(path,model)
        result[model]={'source':str(path),'profile':'titanfall2_native','style':'magenta'}
    return result


def register(state,import_root):
    """Register prepared local packages under the installer lock; retain revisions."""
    from installer.mwc_installer.engine import locked
    state,import_root=Path(state),Path(import_root)
    available=[model for model in MODELS if (import_root/model).is_dir()]
    if not available:raise ValueError('No prepared native pilot packages found in the selected folder')
    expected={model:verify(import_root/model,model) for model in available}
    results=[]
    with locked(state):
        root=state/'operator-imports';root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.pilot-import-',dir=root) as staging:
            staging=Path(staging)
            for model in available:
                target=staging/model;target.mkdir()
                for name in FILES:shutil.copyfile(import_root/model/name,target/name)
                if verify(target,model)!=expected[model]:raise ValueError('Local pilot changed while copying')
            for model in available:
                target=root/model;backup=None
                if target.exists():
                    if verify(target,model)==expected[model]:
                        results.append({'model':model,'reused':True,'game_files_modified':False});continue
                    backup=root/'history'/(model+'-'+uuid.uuid4().hex);backup.parent.mkdir(exist_ok=True);target.rename(backup)
                try:(staging/model).rename(target)
                except BaseException:
                    if backup is not None:backup.rename(target)
                    raise
                results.append({'model':model,'reused':False,'previous_source_backup':str(backup) if backup else None,'sha256':expected[model],'game_files_modified':False})
    return results
