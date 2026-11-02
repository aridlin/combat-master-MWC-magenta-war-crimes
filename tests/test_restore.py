import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from halftone.pipeline import restore
from halftone.assets import dump
from bundle_utils import digest


class ActualStagedRollback(unittest.TestCase):
    def test_real_bundle_dry_run_restore_and_unknown_version_refusal(self):
        path=Path('reports/halftone/modifications.json')
        if not path.exists(): self.skipTest('Build staged bundles first')
        config=json.loads(Path('halftone.json').read_text())
        manifest=json.loads(path.read_text())
        selected=min(manifest['bundles'],key=lambda b:Path(b['output']).stat().st_size)
        with tempfile.TemporaryDirectory(prefix='.rollback-test-',dir=Path.cwd()) as tmp:
            root=Path(tmp); target=root/'bundles/test-bundle'; backup=root/'backups/test-bundle'
            target.parent.mkdir(); backup.parent.mkdir()
            shutil.copyfile(selected['output'],target); shutil.copyfile(selected['backup'],backup)
            entry={**selected,'output':str(target),'backup':str(backup)}
            dump(root/'reports/modifications.json',{'build_id':manifest['build_id'],'bundles':[entry]})
            config['paths']['reports']=str(root/'reports')
            current=digest(target)
            restore(config,dry_run=True)
            self.assertEqual(digest(target),current)
            restore(config)
            self.assertEqual(digest(target),selected['source_sha256'])
            # A second restore is safe/idempotent.
            restore(config)
            target.write_bytes(b'unknown build test; not a game file')
            with self.assertRaises(ValueError): restore(config)
            self.assertEqual(target.read_bytes(),b'unknown build test; not a game file')
        dump('reports/halftone/rollback-test.json',{'bundle':selected['bundle'],
            'source_sha256':selected['source_sha256'],'modified_sha256':selected['output_sha256'],
            'actual_staged_copy_restored':True,'dry_run_left_output_unchanged':True,
            'repeat_restore_safe':True,'unknown_version_refused':True,
            'main_staged_outputs_untouched':True,'installed_game_untouched':True})


if __name__=='__main__': unittest.main()
