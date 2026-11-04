import json,tempfile,unittest
from pathlib import Path
import numpy as np
from operators.styles import normalize,save,load
from operators.assets import load as asset

ROOT=Path(__file__).resolve().parents[1]


class OperatorStyles(unittest.TestCase):
    def test_defaults_preserve_character_designs_and_current_native_selection(self):
        plain=normalize(players=False);painted=normalize(players=True)
        self.assertFalse(plain['game_customs_magenta']);self.assertTrue(painted['game_customs_magenta'])
        for name in ['fishguy','shrek','mario','minecraft_steve']:self.assertFalse(plain['model_magenta'][name])
        self.assertTrue(plain['model_magenta']['tf2_heavy'])
        for name in ('titanfall_pilot','titanfall_grapple','titanfall_pulseblade_female'):self.assertTrue(plain['model_magenta'][name])

    def test_model_and_native_preferences_are_independent_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            value={'model_magenta':{'fishguy':True,'tf2_heavy':False},'game_customs_magenta':False};saved=save(directory,value,players=True);self.assertEqual(load(directory),saved);self.assertTrue(saved['model_magenta']['fishguy']);self.assertFalse(saved['model_magenta']['tf2_heavy']);self.assertFalse(saved['game_customs_magenta']);self.assertFalse((Path(directory)/'state.json').exists())

    def test_unknown_models_or_non_boolean_choices_are_rejected(self):
        for value in [{'model_magenta':{'unknown':True}},{'model_magenta':{'shrek':1}},{'game_customs_magenta':'false'}]:
            with self.assertRaises(ValueError):normalize(value)

    def test_magenta_recolors_without_changing_source_geometry_skin_or_alpha(self):
        source=ROOT/'assets/operator-sources/shrek';config=json.loads((ROOT/'config/preset.json').read_text());a,plain,ia,wa,_=asset(source);b,magenta,ib,wb,_=asset(source,'magenta',config)
        for x,y in zip(a.arrays(),b.arrays()):np.testing.assert_array_equal(x,y)
        np.testing.assert_array_equal(ia,ib);np.testing.assert_array_equal(wa,wb);np.testing.assert_array_equal(np.asarray(plain)[:,:,3],np.asarray(magenta)[:,:,3]);self.assertFalse(np.array_equal(np.asarray(plain)[:,:,:3],np.asarray(magenta)[:,:,:3]))


if __name__=='__main__':unittest.main()
