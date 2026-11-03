"""Narrow data-only COLLADA importer for the inspected authored nailgun export.

No external entities, scripts, controllers or polygon fan approximations.
Only explicit triangles and one matrix-instanced geometry per source are accepted.
"""
import json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
NS={'c':'http://www.collada.org/2005/11/COLLADASchema'}
def flatten(files,output):
    positions=[];normals=[];uv=[];faces=[];materials=[];parts=[]
    for path in files:
        path=Path(path);raw=path.read_bytes()
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('XML entity declarations are forbidden')
        root=ET.fromstring(raw)
        if root.findtext('c:asset/c:up_axis',namespaces=NS)!='Z_UP':raise ValueError('Inspect non-Z-up source before conversion')
        sources={}
        for s in root.findall('.//c:mesh/c:source',NS):
            a=s.find('c:float_array',NS);access=s.find('c:technique_common/c:accessor',NS);stride=int(access.attrib['stride']);sources[s.attrib['id']]=np.fromstring(a.text,sep=' ').reshape(-1,stride)
        vertices={v.attrib['id']:v.find('c:input',NS).attrib['source'][1:] for v in root.findall('.//c:mesh/c:vertices',NS)}
        matrix=root.find('.//c:visual_scene/c:node/c:matrix',NS)
        transform=np.fromstring(matrix.text,sep=' ').reshape(4,4) if matrix is not None else np.eye(4)
        if not np.allclose(transform[3],[0,0,0,1]):raise ValueError('Unsupported COLLADA transform')
        normal_matrix=np.linalg.inv(transform[:3,:3]).T;start=len(positions);mi=len(materials)
        # Inspect authored material diffuse color, rather than invent new paint.
        color=root.find('.//c:effect/c:profile_COMMON/c:technique/c:lambert/c:diffuse/c:color',NS)
        if color is None:color=root.find('.//c:effect/c:profile_COMMON/c:technique/c:phong/c:diffuse/c:color',NS)
        materials.append({'name':path.stem,'base_color_linear':list(map(float,color.text.split())) if color is not None else [.8,.8,.8,1.]})
        for t in root.findall('.//c:mesh/c:triangles',NS):
            inputs={i.attrib['semantic']:(int(i.attrib.get('offset','0')),i.attrib['source'][1:]) for i in t.findall('c:input',NS)};stride=max(x[0] for x in inputs.values())+1
            data=np.fromstring(t.findtext('c:p',namespaces=NS),sep=' ',dtype=int).reshape(-1,3,stride)
            for tri in data:
                ids=[]
                for corner in tri:
                    off,src=inputs['VERTEX'];pos=sources[vertices[src]][corner[off],:3];p=transform@np.r_[pos,1.]
                    off,src=inputs['NORMAL'];n=normal_matrix@sources[src][corner[off],:3];n/=np.linalg.norm(n)
                    if 'TEXCOORD' in inputs:off,src=inputs['TEXCOORD'];tex=sources[src][corner[off],:2]
                    else:tex=[.5,.5]
                    ids.append(len(positions));positions.append(p[:3]);normals.append(n);uv.append(tex)
                if np.linalg.det(transform[:3,:3])<0:ids[1],ids[2]=ids[2],ids[1]
                faces.append(ids)
        parts.append({'name':path.stem,'first_vertex':start,'vertex_count':len(positions)-start,'material':mi})
    face_materials=np.zeros(len(faces),dtype='<i4')
    for part in parts:face_materials[part['first_vertex']//3:(part['first_vertex']+part['vertex_count'])//3]=part['material']
    out=Path(output);out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'source.npz',positions=np.asarray(positions,dtype='<f4'),normals=np.asarray(normals,dtype='<f4'),uv=np.asarray(uv,dtype='<f4'),faces=np.asarray(faces,dtype='<u4'),face_materials=face_materials)
    (out/'source.json').write_text(json.dumps({'objects':parts,'materials':materials,'triangles':len(faces),'vertices':len(positions),'scripts_executed':False},indent=2)+'\n')
