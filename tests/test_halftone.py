import unittest
import numpy as np
from PIL import Image
from halftone.patterns import pattern, colors, validate, linear_mips

SETTINGS = {'size': 512, 'pitch': 32, 'radius': 3, 'white_blend': .18}
PALETTE = {'characters': 'FF00FF', 'weapons': 'FF8500', 'vegetation': '439B45',
           'sheet_metal': '87939B', 'concrete': 'B5ADA0', 'wood': '98663D',
           'dirt': '796B50', 'glass': '65C9D6'}


class ExactPreset(unittest.TestCase):
    def test_all_categories_match_user_reference(self):
        y,x = np.mgrid[:512,:512]
        mask = ((x+16)%32-16)**2 + ((y+16)%32-16)**2 <= 9
        self.assertEqual(mask.sum(),7424)
        self.assertEqual(mask.mean(), .0283203125)
        for name, color in PALETTE.items():
            base = np.array([int(color[i:i+2],16) for i in (0,2,4)],dtype=np.float64)
            light = np.rint(base+(255-base)*.18)
            reference = np.where(mask[...,None],light,base).astype(np.uint8)
            result, actual_mask = pattern(color, SETTINGS)
            np.testing.assert_array_equal(result,reference,err_msg=name)
            np.testing.assert_array_equal(actual_mask,mask)
            self.assertEqual(validate(result,color,SETTINGS)['coverage'],.0283203125)

    def test_radius_pitch_and_boundary_wrap(self):
        image,mask=pattern('FF00FF',SETTINGS)
        self.assertTrue(mask[0,3]); self.assertFalse(mask[0,4])
        self.assertTrue(mask[0,509]); self.assertFalse(mask[0,508])
        self.assertTrue(mask[2,2]); self.assertFalse(mask[3,1])
        np.testing.assert_array_equal(image,np.roll(image,32,axis=0))
        np.testing.assert_array_equal(image,np.roll(image,32,axis=1))
        wide,_=pattern('FF00FF',SETTINGS,1024,1024)
        np.testing.assert_array_equal(wide,np.tile(image,(2,2,1)))

    def test_mips_average_in_linear_light(self):
        x=np.zeros((2,2,3),dtype=np.uint8); x[0]=255
        last=list(linear_mips(x))[-1]
        np.testing.assert_array_equal(last,np.full((1,1,3),188,dtype=np.uint8))

    def test_validation_detects_changes(self):
        x,_=pattern('FF00FF',SETTINGS); x[12,12]=0
        with self.assertRaises(ValueError): validate(x,'FF00FF',SETTINGS)


if __name__=='__main__': unittest.main()
