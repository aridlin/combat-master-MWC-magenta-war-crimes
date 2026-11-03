import unittest
import numpy as np
from weapon_models.placements import offset,parent_position,parent_rotation,roll


def rotate(q,p):
    x,y,z,w=[q[k] for k in 'xyzw'];v=np.array([x,y,z]);p=np.asarray(p);return p+2*np.cross(v,np.cross(v,p)+w*p)


class Placement(unittest.TestCase):
    def test_upward_adjustment_moves_only_the_visual_in_parent_up_axis(self):
        for name,up in [('fishing_rod',.10),('nail_gun',.055),('toaster',.06)]:
            p=parent_position({'models':{name:{'roll_degrees':0}}},name);self.assertEqual(p['x'],0);self.assertEqual(p['z'],0);self.assertAlmostEqual(p['y'],up,places=7)
            for value in p.values():self.assertEqual(float(np.float32(value)),value)
        self.assertEqual(parent_position({},'scorpion'),dict(x=0.,y=0.,z=0.))
    def test_invalid_or_oversize_offsets_are_rejected(self):
        for value in ([0,0,float('nan')],[0,0,1],[0,0]):
            with self.assertRaises(ValueError):offset({'models':{'toaster':{'offset':value}}},'toaster')
    def test_quarter_roll_keeps_the_shaft_line_and_moves_the_reel_sideways(self):
        _,pivot=roll({},'fishing_rod');before={'models':{'fishing_rod':{'roll_degrees':0}}};qb=parent_rotation(before,'fishing_rod');qa=parent_rotation({},'fishing_rod');pb=np.array(list(parent_position(before,'fishing_rod').values()));pa=np.array(list(parent_position({},'fishing_rod').values()))
        for y in [-.2,0,.9]:
            # The stored baseline quaternion is float32, not an exact sqrt(1/2).
            point=pivot+[0,y,0];np.testing.assert_allclose(rotate(qa,point)+pa,rotate(qb,point)+pb,atol=1e-7,rtol=0)
        reel=pivot+[0,0,.06];delta=rotate(qa,reel)-rotate(qa,pivot);np.testing.assert_allclose(delta,[-.06,0,0],atol=1e-8)
        self.assertAlmostEqual(sum(v*v for v in qa.values()),1,places=6)
    def test_invalid_roll_and_pivot_are_rejected(self):
        for spec in [{'roll_degrees':float('nan')},{'roll_degrees':181},{'roll_degrees':'90'},{'roll_pivot':[0,0,float('inf')]}]:
            with self.assertRaises(ValueError):parent_rotation({'models':{'fishing_rod':spec}},'fishing_rod')


if __name__=='__main__':unittest.main()
