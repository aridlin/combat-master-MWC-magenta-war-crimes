import unittest
import numpy as np
from operators.bounds import root_bounds


class RendererBounds(unittest.TestCase):
    def test_rotated_translated_and_scaled_root_contains_mesh_and_original_envelope(self):
        # Mesh is Z-up in centimetres, while the bone frame uses metres with X up.
        bind=np.eye(4);bind[:3,:3]=np.array([[0,0,.01],[0,.01,0],[-.01,0,0]]);bind[0,3]=-.97
        v=np.array([[-40,-20,0],[40,20,200],[0,0,210]])
        old={'m_Center':dict(x=0,y=.13,z=0),'m_Extent':dict(x=.91,y=.61,z=.63)};bounds=root_bounds(v,bind[None],0,old);c=np.array([bounds['m_Center'][k] for k in 'xyz']);e=np.array([bounds['m_Extent'][k] for k in 'xyz']);local=(np.c_[v,np.ones(len(v))]@bind.T)[:,:3]
        self.assertTrue(np.all(local>=c-e));self.assertTrue(np.all(local<=c+e));self.assertLess(np.max(e),2.)
        oc=np.array([old['m_Center'][k] for k in 'xyz']);oe=np.array([old['m_Extent'][k] for k in 'xyz']);self.assertTrue(np.all(oc-oe>=c-e));self.assertTrue(np.all(oc+oe<=c+e))


if __name__=='__main__':unittest.main()
