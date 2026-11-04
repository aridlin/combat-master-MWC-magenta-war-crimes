import struct,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from catgun.bundle import visual_transform,build
from installer.mwc_installer import engine

class CatTransform(unittest.TestCase):
    def test_incomplete_or_invalid_transform_fails_before_any_bundle_access(self):
        for rotation in ([0,2**-.5,2**-.5],[0,0,0,0],[0,0,float('nan'),1]):
            with self.subTest(rotation=rotation),self.assertRaisesRegex(ValueError,'four xyzw'):build({}, {'rotation':rotation})
        with self.assertRaisesRegex(ValueError,'three finite'):build({}, {'position':[0,0]})

    def test_manager_supplies_complete_native_quaternion(self):
        captured={}
        class StopAfterConfiguration(Exception):pass
        def capture(config,settings):
            captured.update(settings);raise StopAfterConfiguration
        with tempfile.TemporaryDirectory() as root:
            work=Path(root);c={'bundle_root':str(work),'paths':{'reports':str(work/'reports')},'expected_build_id':'24397779'}
            with patch('catgun.import_addon.extract'),patch('catgun.bundle.build',side_effect=capture),patch('halftone.pipeline.build_id',return_value='24397779'):
                with self.assertRaises(StopAfterConfiguration):engine._compose_modules(c,work,{'originals':{}},{'lynx'},'local-addon',{},'',{},work,work)
        position,rotation=visual_transform(captured)
        self.assertEqual(set(rotation),set('xyzw'));self.assertEqual(len(struct.pack('<4f',*rotation.values())),16)
        np.testing.assert_allclose([rotation[x] for x in 'xyzw'],[0,2**-.5,2**-.5,0],atol=1e-7)
        self.assertEqual(position,{'x':0.,'y':0.,'z':0.})

if __name__=='__main__':unittest.main()
