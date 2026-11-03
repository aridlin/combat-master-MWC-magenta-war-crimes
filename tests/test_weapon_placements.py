import unittest
import numpy as np
from weapon_models.placements import offset,parent_position


class Placement(unittest.TestCase):
    def test_upward_adjustment_moves_only_the_visual_in_parent_up_axis(self):
        for name,up in [('fishing_rod',.10),('nail_gun',.055),('toaster',.06)]:
            p=parent_position({},name);self.assertEqual(p['x'],0);self.assertEqual(p['z'],0);self.assertAlmostEqual(p['y'],up,places=7)
            for value in p.values():self.assertEqual(float(np.float32(value)),value)
        self.assertEqual(parent_position({},'scorpion'),dict(x=0.,y=0.,z=0.))
    def test_invalid_or_oversize_offsets_are_rejected(self):
        for value in ([0,0,float('nan')],[0,0,1],[0,0]):
            with self.assertRaises(ValueError):offset({'models':{'toaster':{'offset':value}}},'toaster')


if __name__=='__main__':unittest.main()
