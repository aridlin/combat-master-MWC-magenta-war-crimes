"""Owned two-mesh/three-LOD fixture with nontrivial VVD ordering."""
import struct,unittest
import numpy as np
from test_respawn_source import fixture
from catgun.source_model import VERTEX
from model_import.source import load


def lod_fixture():
    mdl,_,_=fixture(48);model=1316;first_mesh=1464
    def put(offset,fmt,*values):struct.pack_into('<'+fmt,mdl,offset,*values)
    put(model+72,'4i',2,first_mesh-model,9,0)
    for offset,count,base,lods in [(first_mesh,5,0,[5,3,3]),(first_mesh+116,4,5,[4,3,0])]:
        put(offset,'4i',0,model-offset,count,base)
        put(offset+52,'8i',*(lods+[lods[-1]]*5))
    vvd=bytearray(112+9*48)
    struct.pack_into('<4s4i',vvd,0,b'IDSV',4,123,3,9)
    struct.pack_into('<8i',vvd,16,9,6,3,3,3,3,3,3)
    struct.pack_into('<4i',vvd,48,4,64,112,0)
    # In LOD0 mesh order: A=[4,5,6,7,8], B=[0,1,2,3]. Lower
    # LOD1 retains the first three vertices of EACH mesh, not globally.
    for k,row in enumerate([(2,4,3),(0,7,2),(1,0,3),(0,3,1)]):struct.pack_into('<3i',vvd,64+k*12,*row)
    vertices=np.zeros(9,dtype=VERTEX);vertices['weights'][:,0]=1;vertices['numbones']=1
    vertices['pos'][:,0]=np.arange(9);vertices['pos'][:,1]=np.arange(9)**2;vertices['normal'][:,2]=1
    vertices['uv'][:,0]=np.arange(9)/10;vvd[112:]=vertices.tobytes()
    # Header, body, model, three LOD headers, then two mesh records per LOD.
    vtx=bytearray(142)
    def x(offset,fmt,*values):struct.pack_into('<'+fmt,vtx,offset,*values)
    x(0,'i',7);x(16,'5i',123,3,0,1,36);x(36,'ii',1,8);x(44,'ii',3,8)
    for level in range(3):x(52+level*12,'iif',2,88+level*18-(52+level*12),float(level*10))
    def mesh(level,index,count,triangles):
        header=88+level*18+index*9
        if not triangles:x(header,'ii',0,0);return
        group=len(vtx);verts=group+25;indices=verts+count*9;strip=indices+len(triangles)*6;vtx.extend(bytes(strip+27-len(vtx)))
        x(header,'ii',1,group-header);x(group,'6i',count,verts-group,len(triangles)*3,indices-group,1,strip-group)
        for k in range(count):x(verts+9*k,'3BBH3B',0,0,0,1,k,0,0,0)
        x(indices,'H'*(len(triangles)*3),*(v for tri in triangles for v in tri));x(strip,'4ihB2i',len(triangles)*3,0,count,0,1,1,0,0)
    mesh(0,0,5,[(0,4,3),(0,2,1)]);mesh(0,1,4,[(0,3,1),(0,2,1)])
    mesh(1,0,3,[(0,2,1)]);mesh(1,1,3,[(0,2,1)])
    mesh(2,0,3,[(0,2,1)]);mesh(2,1,0,[])
    return mdl,vvd,vtx


class AuthoredSourceLODs(unittest.TestCase):
    def test_authored_mesh_prefixes_and_vvd_fixups_keep_original_values(self):
        data=lod_fixture();before=[bytes(x) for x in data];high=load(*data);medium=load(*data,lod=1);low=load(*data,lod=2)
        np.testing.assert_array_equal(high['positions'][:,0],[4,5,6,7,8,0,1,2,3])
        np.testing.assert_array_equal(medium['positions'][:,0],[4,5,6,0,1,2])
        np.testing.assert_array_equal(low['positions'][:,0],[4,5,6])
        np.testing.assert_array_equal(medium['faces'],[[0,1,2],[3,4,5]])
        self.assertEqual([len(d['faces']) for d in [high,medium,low]],[4,2,1])
        for lower in [medium,low]:
            for name in ['bone_names','textures','material_dirs']:self.assertEqual(lower[name],high[name])
            np.testing.assert_array_equal(lower['inverse_bind'],high['inverse_bind'])
            np.testing.assert_array_equal(lower['normals'],np.tile([0,0,1],(len(lower['positions']),1)))
        self.assertEqual([bytes(x) for x in data],before)

    def test_invalid_or_unavailable_lod_never_falls_back(self):
        for lod in [-1,8,True,1.,3]:
            with self.subTest(lod=lod),self.assertRaises(ValueError):load(*lod_fixture(),lod=lod)

    def test_respawn_nonzero_lods_require_separate_verification(self):
        mdl,_,_=fixture(53)
        with self.assertRaisesRegex(ValueError,'separate format verification'):load(mdl,lod=1)

    def test_lower_lod_local_vertex_ids_are_checked_against_that_mesh(self):
        mdl,vvd,vtx=lod_fixture();mesh=106;group=mesh+struct.unpack_from('<i',vtx,mesh+4)[0];verts=group+struct.unpack_from('<i',vtx,group+4)[0]
        struct.pack_into('<H',vtx,verts+4,4) # valid for LOD0, outside LOD1
        with self.assertRaisesRegex(ValueError,'outside MDL mesh LOD'):load(mdl,vvd,vtx,lod=1)

    def test_material_replacements_require_explicit_support(self):
        mdl,vvd,vtx=lod_fixture();table=len(vtx);vtx.extend(bytes(24));struct.pack_into('<i',vtx,24,table);struct.pack_into('<i',vtx,table+8,1)
        with self.assertRaisesRegex(ValueError,'material replacements'):load(mdl,vvd,vtx,lod=1)

    def test_truncated_lod_table_fails_bounds_check(self):
        mdl,vvd,vtx=lod_fixture();struct.pack_into('<i',vtx,48,len(vtx)+1024)
        with self.assertRaisesRegex(ValueError,'outside file'):load(mdl,vvd,vtx,lod=2)
