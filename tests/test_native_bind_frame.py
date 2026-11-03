import copy,unittest
from operators.native import same_bind_frame


class NativeBindFrame(unittest.TestCase):
    def test_empty_lod_may_only_reuse_exact_same_bones_root_and_renderer_frame(self):
        a={'m_Bones':[{'m_PathID':10}],'m_RootBone':{'m_PathID':10},'m_GameObject':{'m_PathID':1}};b=copy.deepcopy(a);b['m_GameObject']['m_PathID']=2;frame={'m_Father':{'m_PathID':3},'m_LocalPosition':{'x':0,'y':0,'z':0},'m_LocalRotation':{'x':0,'y':0,'z':0,'w':1},'m_LocalScale':{'x':1,'y':1,'z':1}};transforms={4:frame,5:copy.deepcopy(frame)};by_go={1:4,2:5}
        self.assertTrue(same_bind_frame(a,b,transforms,by_go));transforms[5]['m_LocalPosition']['y']=.01;self.assertFalse(same_bind_frame(a,b,transforms,by_go));transforms[5]=copy.deepcopy(frame);b['m_Bones'][0]['m_PathID']=11;self.assertFalse(same_bind_frame(a,b,transforms,by_go))


if __name__=='__main__':unittest.main()
