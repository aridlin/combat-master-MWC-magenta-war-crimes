"""Selection boundaries for local viewmodel import, without game data."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch,call
from operators.library import prepare

CLASSES=('scout','soldier','pyro','demoman','heavy','engineer','medic','sniper','spy')

class TF2ArmSelection(unittest.TestCase):
    def run_prepare(self,work,models,matching):
        return prepare({},dict(enumerate(models)),work,matching_arms=matching)

    def test_every_selected_class_gets_its_own_authored_arms(self):
        with tempfile.TemporaryDirectory() as work, \
             patch('operators.library.discover_tf2',return_value=Path('/local/tf')) as discover, \
             patch('model_import.tf2.import_models') as importer, \
             patch('model_import.tf2.flatten',side_effect=lambda raw,dest:dest), \
             patch('operators.tf2_arms.add_virtual_landmarks',side_effect=lambda p,**kw:p) as landmarks, \
             patch('operators.local_pilots.sources',return_value={}):
            models=['tf2_'+n for n in CLASSES];result=self.run_prepare(work,models,True)
            self.assertEqual(set(result),set(models));discover.assert_called_once()
            names=sorted(CLASSES)
            self.assertEqual(importer.call_args_list,[call(Path('/local/tf'),Path(work)/'tf2-local',names),call(Path('/local/tf'),Path(work)/'tf2-local-lod1',names,lod=1),call(Path('/local/tf'),Path(work)/'tf2-local-lod2',names,lod=2),call(Path('/local/tf'),Path(work)/'tf2-local-arms',names,first_person=True)])
            for model in models:
                self.assertEqual(result[model]['first_person_source'],str(Path(work)/'operator-arm-sources'/model))
                self.assertEqual(result[model]['source'],str(Path(work)/'operator-sources'/model))
                self.assertEqual(result[model]['lod_sources'],{str(level):str(Path(work)/'operator-lod-sources'/model/('lod'+str(level))) for level in (1,2)})
            self.assertEqual(landmarks.call_args_list,[call(Path(work)/'operator-arm-sources'/m,expected_model=m) for m in sorted(models)])

    def test_disabling_matching_arms_never_imports_viewmodels(self):
        with tempfile.TemporaryDirectory() as work, \
             patch('operators.library.discover_tf2',return_value=Path('/local/tf')), \
             patch('model_import.tf2.import_models') as importer, \
             patch('model_import.tf2.flatten',side_effect=lambda raw,dest:dest), \
             patch('operators.tf2_arms.add_virtual_landmarks') as landmarks, \
             patch('operators.local_pilots.sources',return_value={}):
            result=self.run_prepare(work,['tf2_scout'],False)
            self.assertEqual(importer.call_args_list,[call(Path('/local/tf'),Path(work)/'tf2-local',['scout']),call(Path('/local/tf'),Path(work)/'tf2-local-lod1',['scout'],lod=1),call(Path('/local/tf'),Path(work)/'tf2-local-lod2',['scout'],lod=2)])
            landmarks.assert_not_called();self.assertNotIn('first_person_source',result['tf2_scout'])

    def test_unselected_classes_are_not_imported_and_failure_is_explicit(self):
        def reject_arms(tf,raw,names,**kwargs):
            self.assertEqual(names,['spy'])
            if kwargs.get('first_person'):raise ValueError('Missing authored Spy arms')
        with tempfile.TemporaryDirectory() as work, \
             patch('operators.library.discover_tf2',return_value=Path('/local/tf')), \
             patch('model_import.tf2.import_models',side_effect=reject_arms), \
             patch('model_import.tf2.flatten',side_effect=lambda raw,dest:dest), \
             patch('operators.local_pilots.sources',return_value={}):
            with self.assertRaisesRegex(ValueError,'Missing authored Spy arms'):
                self.run_prepare(work,['tf2_spy'],True)
