import json,os,tempfile,unittest
from pathlib import Path
from halftone.pipeline import safe_output


class WorkspaceStorage(unittest.TestCase):
    def test_registered_link_only_and_game_tree_still_forbidden(self):
        previous=Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);workspace=base/'project';disk=base/'disk';game=base/'game'
            for p in (workspace,disk,game):p.mkdir()
            try:
                os.chdir(workspace);config={'bundle_root':str(game)}
                (workspace/'experiments').symlink_to(disk,target_is_directory=True)
                with self.assertRaisesRegex(ValueError,'registered storage'):safe_output('experiments/new',config)
                manifest={'version':1,'workspace':str(workspace),'mounts':[{'alias':'experiments','target':str(disk)}]}
                (workspace/'.mwc-storage.json').write_text(json.dumps(manifest))
                self.assertEqual(safe_output('experiments/new',config),disk/'new')
                self.assertEqual(safe_output('local/new',config),workspace/'local/new')
                self.assertEqual(safe_output(disk/'new',config),disk/'new')
                self.assertEqual(safe_output(safe_output('experiments/new',config)/'child',config),disk/'new/child')
                (disk/'escape').symlink_to(base/'elsewhere',target_is_directory=True)
                with self.assertRaisesRegex(ValueError,'registered storage'):safe_output('experiments/escape/new',config)
                (disk/'game').symlink_to(game,target_is_directory=True)
                with self.assertRaisesRegex(ValueError,'Steam'):safe_output('experiments/game/new',config)
                with self.assertRaisesRegex(ValueError,'registered storage'):safe_output('experiments/../../escape',config)
                manifest['workspace']=str(base/'wrong');(workspace/'.mwc-storage.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'does not match'):safe_output('experiments/new',config)
            finally:os.chdir(previous)


if __name__=='__main__':unittest.main()
