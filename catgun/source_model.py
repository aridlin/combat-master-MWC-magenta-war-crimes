"""Read the locally owned M1A0 Source assets; never execute addon Lua.

Disk layouts follow ValveSoftware/source-sdk-2013 src/public/studio.h and
optimize.h. This deliberately supports only the inspected v48/v4/v7 layout.
The third-party model and textures are not part of this repository's license.
"""
from pathlib import Path
import struct
import numpy as np
from PIL import Image
import texture2ddecoder
from .geometry import Mesh,make_cat,palette_image

VERTEX=np.dtype([('weights','<f4',3),('bones','u1',3),('numbones','u1'),
                 ('pos','<f4',3),('normal','<f4',3),('uv','<f4',2)])


def load_cat(settings):
    if settings.get('model','procedural')=='procedural':
        return make_cat(settings['scale']),palette_image()
    if settings['model']!='m1a0':raise ValueError('Unknown cat model')
    root=Path(settings['source_assets']);base=root/'models/weapons/w_catgun'
    mdl=base.with_suffix('.mdl').read_bytes();vvd=base.with_suffix('.vvd').read_bytes()
    vtx=base.with_suffix('.dx90.vtx').read_bytes()
    def ints(data,offset,count):return struct.unpack_from('<'+'i'*count,data,offset)
    if mdl[:4]!=b'IDST' or ints(mdl,4,1)!=(48,):raise ValueError('Only inspected Source MDL v48 is supported')
    if vvd[:4]!=b'IDSV' or ints(vvd,4,1)!=(4,) or ints(vtx,0,1)!=(7,):raise ValueError('Unsupported VVD/VTX format')
    checksum=ints(mdl,8,1)
    if ints(vvd,8,1)!=checksum or ints(vtx,16,1)!=checksum:raise ValueError('Source model checksum mismatch')
    lods=ints(vvd,12,1)[0];count=ints(vvd,16,1)[0]
    fixups,_,vertex_offset,_=ints(vvd,48,4)
    if lods!=1 or fixups or not 0<count<65536:raise ValueError('Only the inspected one-LOD, no-fixup model is supported')
    vertices=np.frombuffer(vvd,dtype=VERTEX,count=count,offset=vertex_offset)
    body_count,body_offset=ints(mdl,232,2)
    if body_count!=1:raise ValueError('Unexpected Source body count')
    _,model_count,_,model_offset=ints(mdl,body_offset,4)
    if model_count!=1:raise ValueError('Unexpected Source model count')
    model=body_offset+model_offset
    mesh_count,mesh_offset,nverts,vertex_index,_=ints(mdl,model+72,5)
    if mesh_count!=1 or nverts!=count or vertex_index:raise ValueError('Unexpected Source mesh layout')
    material,_,mesh_vertices,mesh_vertex_offset=ints(mdl,model+mesh_offset,4)
    if material or mesh_vertices!=count or mesh_vertex_offset:raise ValueError('Unexpected Source material/vertex layout')
    xb_count,xb_offset=ints(vtx,28,2)
    if xb_count!=1:raise ValueError('Unexpected VTX body count')
    xm_count,xm_offset=ints(vtx,xb_offset,2);xm=xb_offset+xm_offset
    xl_count,xl_offset=ints(vtx,xm,2);xl=xm+xl_offset
    xmesh_count,xmesh_offset=ints(vtx,xl,2);xmesh=xl+xmesh_offset
    group_count,group_offset=ints(vtx,xmesh,2);group=xmesh+group_offset
    if (xm_count,xl_count,xmesh_count,group_count)!=(1,1,1,1):raise ValueError('Unexpected VTX hierarchy')
    nv,vo,ni,io,ns,so=ints(vtx,group,6)
    if nv!=count or ns!=1 or ni%3:raise ValueError('Unexpected VTX strip group')
    strip=group+so;sn,si,sv,_,_,flags,_,_=struct.unpack_from('<4ihB2i',vtx,strip)
    if flags!=1 or sn!=ni or si or sv!=nv:raise ValueError('Only inspected triangle lists are supported')
    mapping=np.ndarray((nv,),dtype='<u2',buffer=vtx,offset=group+vo+4,strides=(9,))
    indices=np.frombuffer(vtx,dtype='<u2',count=ni,offset=group+io)
    if indices.max()>=nv or mapping.max()>=count:raise ValueError('Invalid Source vertex index')
    faces=mapping[indices].reshape(-1,3)
    # Source cat faces -Y, Z up. Our mesh contract is +Y forward, Z up.
    positions=vertices['pos'].copy();positions[:,1]*=-1
    normals=vertices['normal'].copy();normals[:,1]*=-1
    positions*=.0254*float(settings['scale'])
    uv=np.mod(vertices['uv'],1).copy();uv[:,1]=1-uv[:,1]
    if settings.get('tail_mode','original')!='original':raise ValueError('M1A0 imports preserve the complete original tail')
    used=np.unique(faces);remap=np.full(count,-1,dtype=int);remap[used]=np.arange(len(used));faces=remap[faces]
    positions=positions[used];normals=normals[used];uv=uv[used]
    if not np.isfinite(positions).all() or not np.isfinite(normals).all():raise ValueError('Nonfinite Source geometry')
    normals/=np.linalg.norm(normals,axis=1,keepdims=True)
    mesh=Mesh();mesh.vertices=positions.tolist();mesh.normals=normals.tolist();mesh.uv=uv.tolist()
    # Reflection reverses winding; align it with the preserved vertex normals.
    for a,b,c in faces:mesh.face(int(a),int(b),int(c))
    mesh.parts=[{'name':'M1A0_local_import','first_vertex':0,'vertex_count':len(positions)}]
    texture=(root/'materials/models/catgun/cat_gun_d_phong.vtf').read_bytes()
    if texture[:4]!=b'VTF\0' or ints(texture,4,2)!=(7,2):raise ValueError('Only inspected VTF 7.2 is supported')
    width,height=struct.unpack_from('<HH',texture,16);fmt=ints(texture,52,1)[0]
    if (width,height,fmt)!=(1024,1024,15):raise ValueError('Unexpected M1A0 diffuse format')
    raw=texture2ddecoder.decode_bc3(texture[-width*height:],width,height)
    image=Image.frombytes('RGBA',(width,height),raw,'raw','BGRA').convert('RGB')
    return mesh,image
