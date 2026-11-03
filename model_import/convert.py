"""Validate and fit authored arrays; atlas material images without replacing geometry."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image

def linear(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
def srgb(v):return np.where(v<=.0031308,v*12.92,1.055*np.maximum(v,0)**(1/2.4)-.055)
def convert(source,destination,rotation,length,forward_min,vertical_center,provenance):
    source=Path(source);dest=Path(destination);dest.mkdir(parents=True,exist_ok=True);meta=json.loads((source/'source.json').read_text());a=np.load(source/'source.npz',allow_pickle=False)
    v=a['positions'].astype(np.float64);n=a['normals'].astype(np.float64);uv=a['uv'].copy();faces=a['faces'];fm=a['face_materials'];R=np.asarray(rotation,dtype=float)
    if R.shape!=(3,3) or not np.allclose(R.T@R,np.eye(3),atol=1e-7) or not np.isclose(np.linalg.det(R),1):raise ValueError('Expected a proper orthogonal rotation')
    if len(v)>65535 or not len(v) or not len(faces):raise ValueError('Mesh exceeds the existing uint16 writer or is empty; explicit partitioning required')
    if not all(np.isfinite(x).all() for x in (v,n,uv)):raise ValueError('Non-finite source attributes')
    if faces.min()<0 or faces.max()>=len(v):raise ValueError('Invalid triangle indices')
    v=v@R.T;n=n@R.T;n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    scale=float(length)/np.ptp(v[:,1]);v*=scale;v[:,0]-=(v[:,0].min()+v[:,0].max())/2;v[:,1]+=forward_min-v[:,1].min();v[:,2]+=vertical_center-(v[:,2].min()+v[:,2].max())/2
    count=len(meta['materials']);cols=math.ceil(math.sqrt(count));rows=math.ceil(count/cols);tile=512;gutter=4;stride=tile+2*gutter
    atlas=Image.new('RGB',(cols*stride,rows*stride));mapped=uv.copy();assigned=np.full(len(v),-1)
    for mi,mat in enumerate(meta['materials']):
        color=srgb(np.clip(np.asarray(mat['base_color_linear'][:3]),0,1))
        if 'pixels' in mat:
            pixels=np.load(source/mat['pixels'],allow_pickle=False)
            if pixels.shape[2]>3 and np.any(pixels[:,:,3]<.999):raise ValueError('Transparent authored material requires a dedicated alpha-capable renderer')
            rgb=np.flipud(pixels[:,:,:3]);rgb=np.clip(srgb(linear(rgb)*np.asarray(mat['base_color_linear'][:3])),0,1)
            ids=np.unique(faces[fm==mi].ravel());lower=np.floor(uv[ids].min(axis=0));upper=np.ceil(uv[ids].max(axis=0));upper=np.maximum(upper,lower+1);repeat=(upper-lower).astype(int)
            if np.any(repeat>8):raise ValueError('Excessive UV repetition; explicit material-specific layout required')
            tiled=np.tile(np.rint(rgb*255).astype(np.uint8),(int(repeat[1]),int(repeat[0]),1));image=Image.fromarray(tiled).resize((tile,tile),Image.Resampling.LANCZOS)
        else:image=Image.new('RGB',(tile,tile),tuple(np.rint(color*255).astype(int)))
        x,y=(mi%cols)*stride,(mi//cols)*stride
        # Extrude border pixels to prevent neighboring material colors bleeding.
        tex=np.asarray(image);padded=np.pad(tex,((gutter,gutter),(gutter,gutter),(0,0)),mode='edge');atlas.paste(Image.fromarray(padded),(x,y))
        indices=np.unique(faces[fm==mi].ravel())
        if np.any(assigned[indices]>=0):raise ValueError('Source exporter must split vertices at material boundaries')
        assigned[indices]=mi
        if 'pixels' in mat:
            local=(uv[indices]-lower)/(upper-lower)
        else:local=np.full((len(indices),2),.5)
        mapped[indices,0]=(x+gutter+local[:,0]*tile)/atlas.width
        mapped[indices,1]=1-(y+gutter+(1-local[:,1])*tile)/atlas.height
    if np.any(assigned<0):raise ValueError('Unassigned vertices')
    np.savez_compressed(dest/'mesh.npz',positions=v.astype('<f4'),normals=n.astype('<f4'),uv=mapped.astype('<f4'),faces=faces.astype('<u2'))
    atlas.save(dest/'albedo.png');record={**provenance,'source_vertices':len(v),'triangles':len(faces),'rotation':R.tolist(),'uniform_scale':scale,'target_forward_length_m':length,'bounds':[v.min(0).tolist(),v.max(0).tolist()],'source_objects':meta['objects'],'mesh_sha256':hashlib.sha256((dest/'mesh.npz').read_bytes()).hexdigest(),'albedo_sha256':hashlib.sha256((dest/'albedo.png').read_bytes()).hexdigest(),'geometry_created':False,'animation_claim':'Rigid weapon visual follows existing root animation; in-game alignment untested'}
    (dest/'provenance.json').write_text(json.dumps(record,indent=2)+'\n');return record
