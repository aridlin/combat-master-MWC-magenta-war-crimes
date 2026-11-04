import copy,json,tempfile,unittest
from pathlib import Path
from operators.assignments import catalogue,validate,save_plan,load_plan


class Assignments(unittest.TestCase):
    def test_every_operator_has_one_verified_identity(self):
        targets,_=catalogue();self.assertEqual(len(targets),32)
        self.assertEqual(len({x['prefab_guid'] for x in targets}),32)
        dozer=next(x for x in targets if x['id']=='operator_30')
        self.assertEqual(dozer['name'],'Dozer');self.assertEqual(dozer['internal_name'],'30.VinniePuh')
        self.assertTrue(all(x['identity_verified'] and x['renderers'] for x in targets))

    def test_independent_choices_round_trip_without_game_state(self):
        with tempfile.TemporaryDirectory() as d:
            plan={'operator_0':'tf2_heavy','operator_30':'shrek','operator_31':'original'}
            self.assertEqual(save_plan(d,plan),{'operator_0':'tf2_heavy','operator_30':'shrek'})
            self.assertEqual(load_plan(d),{'operator_0':'tf2_heavy','operator_30':'shrek'})
            self.assertFalse((Path(d)/'state.json').exists())
            self.assertFalse(json.loads((Path(d)/'operator-plan.json').read_text())['installed'])
            before=(Path(d)/'operator-plan.json').read_bytes()
            with self.assertRaises(ValueError):save_plan(d,{'operator_30':'unknown'})
            self.assertEqual((Path(d)/'operator-plan.json').read_bytes(),before)

    def test_native_pilot_choices_are_separate_and_keep_dozer_shrek(self):
        choices={'operator_0':'titanfall_grapple','operator_1':'titanfall_pulseblade_female','operator_30':'shrek'}
        self.assertEqual(validate(choices),choices)

    def test_shared_renderer_conflict_is_explicit(self):
        targets,models=catalogue();targets=copy.deepcopy(targets[:2]);targets[1]['renderers']=copy.deepcopy(targets[0]['renderers'])
        with self.assertRaisesRegex(ValueError,'asset conflict'):validate({'operator_0':'tf2_heavy','operator_1':'tf2_scout'},targets,models)
        self.assertEqual(len(validate({'operator_0':'tf2_heavy','operator_1':'tf2_heavy'},targets,models)),2)

    def test_unknown_targets_rejected(self):
        with self.assertRaises(ValueError):validate({'operator_999':'tf2_scout'})


if __name__=='__main__':unittest.main()
