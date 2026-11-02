import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from halftone.classify import classify


class ClassificationSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        config_path=Path('halftone.json') if Path('halftone.json').exists() else Path('config/preset.json')
        self.config=json.loads(config_path.read_text())
        self.config.pop('coverage_mode',None)
        self.config['paths']['reports']=self.tmp.name
        self.config['asset_overrides']={}
        self.texture={'id':'CAB-test:10','name':'Test_Albedo','width':512,'height':512,
                      'format':10,'mips':10,'color_space':1}

    def tearDown(self): self.tmp.cleanup()

    def run_fixture(self, materials, overrides=None):
        if overrides: self.config['asset_overrides']=overrides
        bundle={'bundle':'src/maps/example','source':'unused','textures':[self.texture],
                'materials':materials,'renderers':[],'errors':[]}
        with patch('halftone.classify.load_scan',return_value=[bundle]):
            return classify(self.config)['assets'][0]

    def material(self,name,slot='_BaseMap',oid='CAB-test:20'):
        return {'id':oid,'name':name,'properties':[{'slot':slot,'texture':'CAB-test:10','scale':[1,1],'offset':[0,0]}]}

    def test_supported_albedo_is_classified(self):
        r=self.run_fixture([self.material('ConcreteWall')])
        self.assertEqual((r['action'],r['category']),('replace','concrete'))

    def test_shared_data_map_cannot_be_overridden(self):
        r=self.run_fixture([self.material('ConcreteWall'),self.material('ConcreteWall','Normal','CAB-test:21')],{'CAB-test:10':'concrete'})
        self.assertEqual(r['action'],'preserve')
        self.assertIn('also_used_as_noncolor_or_unknown_slot',r['reasons'])

    def test_cross_category_conflict_is_not_overridden(self):
        r=self.run_fixture([self.material('ConcreteWall'),self.material('Wood','_BaseMap','CAB-test:21')],{'CAB-test:10':'concrete'})
        self.assertEqual(r['action'],'preserve')
        self.assertIn('mixed_category_conflict',r['reasons'])

    def test_unknown_shader_slot_not_inferred_from_filename(self):
        self.texture['name']='Concrete_Albedo'
        r=self.run_fixture([self.material('Concrete','CustomMysterySlot')])
        self.assertEqual(r['action'],'preserve')

    def test_mixed_atlas_preserved(self):
        self.texture['name']='T_props_02_alb'
        r=self.run_fixture([self.material('Glass')])
        self.assertEqual(r['action'],'preserve')
        self.assertIn('possible_mixed_category_atlas',r['reasons'])

    def test_full_surface_mode_uses_explicit_neutral_fallback(self):
        self.config['coverage_mode']='all_surface_albedo'; self.config['fallback_category']='concrete'
        r=self.run_fixture([self.material('UnmappedProp')])
        self.assertEqual((r['action'],r['category']),('replace','concrete'))
        self.assertTrue(r['uses_neutral_fallback'])

    def test_full_surface_mode_still_preserves_data_maps(self):
        self.config['coverage_mode']='all_surface_albedo'; self.config['fallback_category']='concrete'
        r=self.run_fixture([self.material('UnmappedProp'),self.material('UnmappedProp','Normal','CAB-test:21')])
        self.assertEqual(r['action'],'preserve')
        self.assertIn('also_used_as_noncolor_or_unknown_slot',r['reasons'])


if __name__=='__main__': unittest.main()
