"""Independent tiny visual fixtures; no proprietary model data."""
import struct
import unittest
import numpy as np
from catgun.source_model import VERTEX
from model_import.source import load


def fixture(version=53):
    modern=version==53
    shift=4 if modern else 0
    mdl=bytearray(2000)
    def put(offset,fmt,*values):struct.pack_into('<'+fmt,mdl,offset,*values)
    mdl[:4]=b'IDST';put(4,'ii',version,123)
    bone=952;texture=1210;body=1300;model=1316;mesh=1464
    put(156+shift,'ii',1,bone)
    put(bone,'ii',244 if modern else 216,-1)
    name=bone+(244 if modern else 216);mdl[name:name+5]=b'root\0'
    put(bone+(120 if modern else 96),'12f',1,0,0,0,0,1,0,0,0,0,1,0)
    put(204+shift,'4i',1,texture,0,0);put(texture,'i',44 if modern else 64)
    name=texture+(44 if modern else 64);mdl[name:name+5]=b'body\0'
    put(220+shift,'3i',1,1,1290);put(1290,'H',0)
    put(232+shift,'ii',1,body);put(body,'4i',0,1,1,16)
    mdl[model:model+5]=b'body\0';put(model+72,'4i',1,mesh-model,3,0)
    put(mesh,'4i',0,model-mesh,3,0)
    # VTX: a body/model/LOD/mesh/group followed by vertices, indices, strip.
    group_stride,strip_stride=(33,35) if modern else (25,27)
    group=73;verts=group+group_stride;indices=verts+27;strip=indices+6
    vtx=bytearray(strip+strip_stride)
    def x(offset,fmt,*values):struct.pack_into('<'+fmt,vtx,offset,*values)
    x(0,'i',7);x(16,'5i',123,1,0,1,36)
    x(36,'ii',1,8);x(44,'ii',1,8);x(52,'ii',1,12);x(64,'ii',1,9)
    x(group,'6i',3,verts-group,3,indices-group,1,strip-group)
    for n in range(3):x(verts+9*n,'3BBH3B',0,0,0,1,n,0,0,0)
    x(indices,'3H',0,1,2);x(strip,'4ihB2i',3,0,3,0,1,1,0,0)
    vvd=bytearray(64+144)
    struct.pack_into('<4s4i',vvd,0,b'IDSV',4,123,1,3)
    struct.pack_into('<4i',vvd,48,0,0,64,0)
    vertices=np.zeros(3,dtype=VERTEX);vertices['weights'][:,0]=1;vertices['numbones']=1
    vertices['pos']=[[0,0,0],[1,0,0],[0,1,0]];vertices['normal'][:,2]=1
    vvd[64:]=vertices.tobytes()
    if modern:
        vo=len(mdl);mdl.extend(vtx);vd=len(mdl);mdl.extend(vvd)
        put(428,'8i',vo,vd,0,0,len(vtx),len(vvd),0,0);put(80,'i',len(mdl))
    return mdl,vvd,vtx


class RespawnSource(unittest.TestCase):
    def test_embedded_matches_legacy_visual_contract(self):
        modern,_,_=fixture();legacy,vvd,vtx=fixture(48)
        a=load(modern);b=load(legacy,vvd,vtx)
        for key in ('positions','normals','faces','uv','inverse_bind','bone_weights','bone_indices','bone_parents','face_materials'):
            np.testing.assert_array_equal(a[key],b[key])
        self.assertEqual(a['textures'],['body']);self.assertEqual(a['bone_names'],['root'])
        np.testing.assert_array_equal(a['faces'],[[0,2,1]])

    def test_invalid_embedded_ranges_and_checksum(self):
        for offset,value,error in ((428,-1,'outside'),(432,2000,'overlap'),(444,0,'lacks'),(80,1,'length')):
            mdl,_,_=fixture();struct.pack_into('<i',mdl,offset,value)
            with self.assertRaisesRegex(ValueError,error):load(mdl)
        mdl,_,_=fixture();vvd=struct.unpack_from('<i',mdl,432)[0];struct.pack_into('<i',mdl,vvd+8,7)
        with self.assertRaisesRegex(ValueError,'checksums'):load(mdl)

    def test_respawn_quads_are_not_misread_as_legacy_triangle_strip(self):
        mdl,_,vtx=fixture();start=struct.unpack_from('<i',mdl,428)[0]
        mdl[start+len(vtx)-35+18]=2
        with self.assertRaisesRegex(ValueError,'topology'):load(mdl)

    def test_truncation_and_external_data_rejected(self):
        mdl,vvd,vtx=fixture()
        with self.assertRaisesRegex(ValueError,'embedded'):load(mdl,vvd,vtx)
        for size in (0,7,100,952,len(mdl)-1):
            with self.assertRaises(ValueError):load(mdl[:size])


if __name__=='__main__':unittest.main()
