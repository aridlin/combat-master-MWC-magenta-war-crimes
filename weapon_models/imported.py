"""Verified authored assets; never silently fall back to primitive geometry."""
import hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from catgun.geometry import Mesh,export,render
ROOT=Path(__file__).resolve().parents[1]/'assets/authored-weapons'

def load(name,root=None):
    directory=Path(root or ROOT)/name;meta=json.loads((directory/'provenance.json').read_text())
    for filename,key in [('mesh.npz','mesh_sha256'),('albedo.png','albedo_sha256')]:
        if hashlib.sha256((directory/filename).read_bytes()).hexdigest()!=meta[key]:raise ValueError('Authored asset changed without updating provenance: '+name+'/'+filename)
    a=np.load(directory/'mesh.npz',allow_pickle=False);m=Mesh()
    for key,field in [('positions','vertices'),('normals','normals'),('uv','uv'),('faces','faces')]:setattr(m,field,a[key].tolist())
    if len(m.vertices)>65535:raise ValueError('Explicit mesh partitioning is required')
    with Image.open(directory/'albedo.png') as image:coat=image.convert('RGB')
    return m,coat,meta

def export_model(name,directory,root=None):
    mesh,image,meta=load(name,root);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    result=export(mesh,directory,texture=image,prefix=name,description='Authored source: '+meta['title']+' by '+meta['author']+'; '+meta['license'])
    render(mesh,directory/'preview.png',texture=image,label=name.replace('_',' ')+' | authored model | software preview, not in-game')
    (directory/'provenance.json').write_text(json.dumps(meta,indent=2)+'\n');return result
