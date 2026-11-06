import copy,json,struct,unittest,zlib
from pathlib import Path
import numpy as np
from operators.clip_review import sample_channels,sample_world,euler_xyz,quaternion_matrix


def binding(path,attribute):
    return {'typeID':4,'customType':0,'path':zlib.crc32(path.encode()),'attribute':attribute}


def fixture():
    raw=b''
    for time,keys in [(0,[(0,[2,3,4,5]),(1,[0,0,0,10]),(2,[0,0,0,0])]),(1,[(0,[0,0,0,9])]),(float('inf'),[])]:
        raw+=struct.pack('<fi',time,len(keys))
        for index,coeff in keys:raw+=struct.pack('<i4f',index,*coeff)
    data={'m_StreamedClip':{'curveCount':3,'data':list(struct.unpack('<'+str(len(raw)//4)+'I',raw))},'m_DenseClip':{'m_FrameCount':3,'m_CurveCount':3,'m_SampleRate':2,'m_BeginTime':0,'m_SampleArray':[0,0,0,0,0,90,0,0,180]},'m_ConstantClip':{'data':[2,1,1]}}
    return {'m_Name':'synthetic','m_MuscleClip':{'m_StartTime':0.,'m_StopTime':1.,'m_Clip':{'data':data}},'m_ClipBindingConstant':{'genericBindings':[binding('root',1),binding('root',4),binding('root',3)]}}


def transform(go,parent=0,children=()):
    return {'m_GameObject':{'m_PathID':go},'m_Father':{'m_PathID':parent},'m_Children':[{'m_PathID':c,'m_FileID':0} for c in children],'m_LocalPosition':dict(x=0,y=0,z=0),'m_LocalScale':dict(x=1,y=1,z=1),'m_LocalRotation':dict(x=0,y=0,z=0,w=1)}


class NativeClipReview(unittest.TestCase):
    def test_streamed_cubic_dense_exact_frame_and_constant_channels(self):
        tree=fixture();channels,report=sample_channels(tree,.5)
        np.testing.assert_allclose(channels[0][2],[8,10,0])
        np.testing.assert_allclose(channels[1][2],[0,0,90])
        np.testing.assert_allclose(channels[2][2],[2,1,1])
        self.assertEqual(report['transform_bindings'],3)
        np.testing.assert_allclose(sample_channels(tree,1)[0][0][2],[9,10,0])

    def test_world_hierarchy_uses_native_parent_transform_and_xyz_order(self):
        tree=fixture();nodes={1:transform(10,children=[2]),2:transform(20,1)};names={10:'root',20:'child'};nodes[2]['m_LocalPosition']['x']=1
        before=copy.deepcopy(nodes);world,report=sample_world(tree,.5,nodes,names,1)
        np.testing.assert_allclose(world[2][:3,3],[8,12,0],atol=1e-10)
        self.assertEqual(nodes,before);self.assertEqual(report['resolved_transform_bindings'],3)
        # Packed XYZ is distinct from the usual Quaternion.Euler ZXY API.
        np.testing.assert_allclose(euler_xyz([90,90,90])@[0,1,0],[0,1,0],atol=1e-10)
        np.testing.assert_allclose(quaternion_matrix([0,0,2**-.5,2**-.5])@[1,0,0],[0,1,0],atol=1e-10)

    def test_mixed_axis_packed_euler_matches_independent_unity_xyz_reference(self):
        reference=json.loads((Path(__file__).parent/'fixtures/clip-review/euler-xyz-reference.json').read_text())
        rotation=np.asarray(reference['matrix']).reshape(4,4)[:3,:3]
        np.testing.assert_allclose(euler_xyz(reference['angles']),rotation,atol=3e-7,rtol=0)
        tree=fixture();tree['m_MuscleClip']['m_Clip']['data']['m_DenseClip']['m_SampleArray'][3:6]=reference['angles']
        nodes={1:transform(10,children=[2]),2:transform(20,1)};names={10:'root',20:'child'};nodes[2]['m_LocalPosition'].update(x=1,y=.25,z=-.5)
        world,report=sample_world(tree,.5,nodes,names,1)
        expected=rotation@np.array([2.,.25,-.5])+[8,10,0]
        np.testing.assert_allclose(world[2][:3,3],expected,atol=6e-7,rtol=0)
        self.assertEqual(report['packed_euler_order'],'XYZ')

    def test_unknown_and_ambiguous_hashes_fail_instead_of_using_last_node(self):
        tree=fixture();nodes={1:transform(10,children=[2,4]),2:transform(20,1,[3]),3:transform(30,2),4:transform(40,1,[5]),5:transform(50,4)};names={10:'root',20:'a',30:'hand',40:'b',50:'hand'}
        for path in ('hand','missing'):
            tree['m_ClipBindingConstant']['genericBindings'][0]['path']=zlib.crc32(path.encode())
            with self.assertRaisesRegex(ValueError,'absent or ambiguous'):sample_world(tree,0,nodes,names,1)
        tree['m_ClipBindingConstant']['genericBindings'][0]['path']=zlib.crc32(b'a/hand')
        _,report=sample_world(tree,0,nodes,names,1);self.assertGreater(report['unused_ambiguous_path_aliases'],0)

    def test_unimplemented_timing_formats_and_binding_dimensions_rejected(self):
        for time in (-1,.1,float('nan'),2):
            with self.subTest(time=time),self.assertRaises(ValueError):sample_channels(fixture(),time)
        tree=fixture();tree['m_ClipBindingConstant']['genericBindings'][0]['attribute']=99
        with self.assertRaisesRegex(ValueError,'Unsupported'):sample_channels(tree,0)
        tree=fixture();tree['m_MuscleClip']['m_Clip']['data']['m_ConstantClip']['data'].append(1)
        with self.assertRaisesRegex(ValueError,'exceed'):sample_channels(tree,0)

    def test_truncated_stream_and_discrete_data_rejected(self):
        tree=fixture();stream=tree['m_MuscleClip']['m_Clip']['data']['m_StreamedClip'];stream['data']=stream['data'][:-1]
        with self.assertRaisesRegex(ValueError,'Truncated'):sample_channels(tree,0)
        tree=fixture();tree['m_MuscleClip']['m_Clip']['data']['m_StreamedClip']['discreteCurveCount']=1
        with self.assertRaisesRegex(ValueError,'discrete'):sample_channels(tree,0)

    def test_root_channels_are_reported_without_applying_runtime_root_motion(self):
        tree=fixture();tree['m_ClipBindingConstant']['genericBindings'].append({'typeID':95,'customType':8,'path':0,'attribute':7});tree['m_MuscleClip']['m_Clip']['data']['m_ConstantClip']['data'].append(42)
        channels,report=sample_channels(tree,0);self.assertEqual(len(channels),3);self.assertEqual(len(report['ignored_root_channels']),1);self.assertTrue(report['runtime_IK_blending_events_and_root_motion_not_evaluated'])


if __name__=='__main__':unittest.main()
