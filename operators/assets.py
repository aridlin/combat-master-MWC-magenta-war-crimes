"""Pack reviewed character materials without changing fitted geometry or skin."""
import json,math
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from catgun.geometry import Mesh
from model_import.convert import linear,srgb

ATLAS_TILE=512
ATLAS_GUTTER=4


def load(source,style='original',pattern_config=None):
    source=Path(source);meta=json.loads((source/'source.json').read_text());a=np.load(source/'source.npz',allow_pickle=False)
    v,n,uv,faces,fm=[a[k] for k in ('positions','normals','uv','faces','face_materials')]
    if not 0<len(v)<=65535 or not np.isfinite(v).all() or faces.min()<0 or faces.max()>=len(v):raise ValueError('Invalid/oversize fitted character geometry')
    if meta.get('prepacked'):
        for filename,field in [('source.npz','mesh_sha256'),('albedo.png','albedo_sha256')]:
            if hashlib.sha256((source/filename).read_bytes()).hexdigest()!=meta[field]:raise ValueError('Packaged operator source hash mismatch: '+filename)
        with Image.open(source/'albedo.png') as image:atlas=image.convert('RGBA')
        if style=='magenta':
            if pattern_config is None:raise ValueError('Magenta style needs the existing halftone configuration')
            from halftone.patterns import pattern
            pixels=np.asarray(atlas).copy();dots,_=pattern(pattern_config['categories']['characters']['color'],pattern_config['generation'],atlas.width,atlas.height);detail=(pixels[:,:,:3].astype(float)@np.array([.2126,.7152,.0722]))/255;pixels[:,:,:3]=np.rint(dots*(.30+.70*detail[:,:,None])).astype(np.uint8);atlas=Image.fromarray(pixels)
        elif style!='original':raise ValueError('Unknown operator material style')
        mesh=Mesh();mesh.vertices=v.tolist();mesh.normals=n.tolist();mesh.uv=uv.tolist();mesh.faces=faces.tolist()
        return mesh,atlas,a['bone_indices'].copy() if 'bone_indices' in a else None,a['bone_weights'].copy() if 'bone_weights' in a else None,{**meta,'style':style}
    count=len(meta['materials']);cols=math.ceil(math.sqrt(count));rows=math.ceil(count/cols);tile=ATLAS_TILE;gutter=ATLAS_GUTTER;stride=tile+2*gutter;atlas=Image.new('RGBA',(cols*stride,rows*stride),(255,255,255,0));mapped=uv.copy();assigned=np.full(len(v),-1);alpha_used=False
    for mi,mat in enumerate(meta['materials']):
        ids=np.unique(faces[fm==mi].ravel())
        if not len(ids):continue
        if np.any(assigned[ids]>=0):raise ValueError('Character exporter must split material-boundary vertices')
        assigned[ids]=mi;color=np.asarray(mat['base_color_linear']);lower=np.floor(uv[ids].min(0));upper=np.maximum(np.ceil(uv[ids].max(0)),lower+1);repeat=(upper-lower).astype(int)
        if np.any(repeat>8):raise ValueError('Character UV repetition requires explicit review')
        if 'pixels' in mat:
            name=mat['pixels']
            if Path(name).name!=name:raise ValueError('Unsafe material pixel path')
            pixels=np.flipud(np.load(source/name,allow_pickle=False));rgb=np.clip(srgb(linear(pixels[:,:,:3])*color[:3]),0,1)
            alpha=pixels[:,:,3] if mat.get('alpha_mode')=='blend' and pixels.shape[2]>3 else np.ones(pixels.shape[:2])
            pixels=np.concatenate([rgb,alpha[:,:,None]*color[3]],axis=2);pixels=np.tile(np.rint(pixels*255).astype(np.uint8),(int(repeat[1]),int(repeat[0]),1));image=Image.fromarray(pixels).resize((tile,tile),Image.Resampling.NEAREST if meta.get('texture_filter')=='nearest' else Image.Resampling.LANCZOS);local=(uv[ids]-lower)/(upper-lower)
        else:
            rgba=tuple(np.rint(np.r_[srgb(color[:3]),color[3]]*255).astype(int));image=Image.new('RGBA',(tile,tile),rgba);local=np.full((len(ids),2),.5)
        pixels=np.asarray(image).copy();alpha_used|=bool(np.any(pixels[:,:,3]<255))
        if style=='magenta':
            if pattern_config is None:raise ValueError('Magenta style needs the existing halftone configuration')
            from halftone.patterns import pattern
            original=pattern_config['categories']['characters']['color'];dots,_=pattern(original,pattern_config['generation'],tile,tile);detail=(pixels[:,:,:3].astype(float)@np.array([.2126,.7152,.0722]))/255;pixels[:,:,:3]=np.rint(dots*(.30+.70*detail[:,:,None])).astype(np.uint8)
        elif style!='original':raise ValueError('Unknown operator material style')
        x,y=(mi%cols)*stride,(mi//cols)*stride;atlas.paste(Image.fromarray(np.pad(pixels,((gutter,gutter),(gutter,gutter),(0,0)),mode='edge')),(x,y));mapped[ids,0]=(x+gutter+local[:,0]*tile)/atlas.width;mapped[ids,1]=1-(y+gutter+(1-local[:,1])*tile)/atlas.height
    if np.any(assigned<0):raise ValueError('Unassigned character vertices')
    mesh=Mesh();mesh.vertices=v.tolist();mesh.normals=n.tolist();mesh.uv=mapped.tolist();mesh.faces=faces.tolist()
    return mesh,atlas,a['bone_indices'].copy() if 'bone_indices' in a else None,a['bone_weights'].copy() if 'bone_weights' in a else None,{**meta,'alpha_clip_required':alpha_used,'style':style}


def prepare(source,destination,provenance,profile):
    source,destination=Path(source),Path(destination)
    if destination.exists():raise ValueError('Use a new operator source package directory')
    mesh,image,bi,bw,meta=load(source);original=np.load(source/'source.npz',allow_pickle=False);v,n,uv,f=mesh.arrays();destination.mkdir(parents=True)
    np.savez_compressed(destination/'source.npz',positions=v,normals=n,uv=uv,faces=f,face_materials=np.zeros(len(f),dtype='<i4'),bone_indices=bi,bone_weights=bw,inverse_bind=original['inverse_bind'],bone_parents=original['bone_parents'])
    image.save(destination/'albedo.png')
    meta.update(prepacked=True,profile=profile,provenance=provenance,materials=[{'name':'Packed authored source','image':'albedo.png'}],source_geometry_sha256=hashlib.sha256((source/'source.npz').read_bytes()).hexdigest(),mesh_sha256=hashlib.sha256((destination/'source.npz').read_bytes()).hexdigest(),albedo_sha256=hashlib.sha256((destination/'albedo.png').read_bytes()).hexdigest(),in_game_tested=False)
    (destination/'source.json').write_text(json.dumps(meta,indent=2)+'\n');return meta


def prepare_static(source,destination,provenance):
    source,destination=Path(source),Path(destination)
    if destination.exists():raise ValueError('Use a fresh static character package')
    mesh,image,bi,bw,meta=load(source)
    if bi is not None or bw is not None:raise ValueError('Expected an unrigged source for local rig transfer')
    destination.mkdir(parents=True);v,n,uv,f=mesh.arrays();np.savez_compressed(destination/'source.npz',positions=v,normals=n,uv=uv,faces=f,face_materials=np.zeros(len(f),dtype='<i4'));image.save(destination/'albedo.png');meta.update(prepacked=True,rigless=True,provenance=provenance,materials=[{'name':'Packed authored source','image':'albedo.png'}],mesh_sha256=hashlib.sha256((destination/'source.npz').read_bytes()).hexdigest(),albedo_sha256=hashlib.sha256((destination/'albedo.png').read_bytes()).hexdigest(),in_game_tested=False);(destination/'source.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
