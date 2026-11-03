"""Selection isolation, transaction failure/recovery and asset-path coverage."""
import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from bundle_utils import digest
from halftone.assets import dump
from installer.mwc_installer import engine as e

class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.state=self.base/'state';self.root=self.base/'game/CombatMaster_Data/StreamingAssets/Bundles';self.root.mkdir(parents=True);self.state.mkdir()
        self.config={'bundle_root':str(self.root)};self.saved={'bundle_root':str(self.root),'originals':{},'installed':{},'selected':['lynx']}
        for rel in ('root/root','src/weapons/weapons'):
            p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('original '+rel).encode());b=self.state/'originals'/rel;b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(p.read_bytes());self.saved['originals'][rel]=self.saved['installed'][rel]=digest(p)
        dump(self.state/'state.json',self.saved)
    def tearDown(self):self.tmp.cleanup()
    def output(self):
        p=self.base/'new';p.write_bytes(b'new data');return {'root/root':p,'src/weapons/weapons':p}
    @patch.object(e,'game_running',return_value=False)
    def test_install_and_restore_preserve_state(self,_):
        out=self.output();installed=e.transaction(self.config,self.state,self.saved,out,{'lynx','scorpion'})
        self.assertEqual(installed['selected'],['lynx','scorpion']);self.assertFalse((self.state/'pending.json').exists())
        restored=e.transaction(self.config,self.state,installed,{r:self.state/'originals'/r for r in self.saved['originals']},set())
        self.assertEqual(restored['installed'],self.saved['installed']);self.assertEqual(restored['selected'],[])
    @patch.object(e,'game_running',return_value=False)
    def test_mid_commit_failure_rolls_back(self,_):
        original=e.replace_verified;calls=0
        def fail(source,target,before,after):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('simulated disk error')
            return original(source,target,before,after)
        with patch.object(e,'replace_verified',side_effect=fail):
            with self.assertRaises(OSError):e.transaction(self.config,self.state,self.saved,self.output(),{'scorpion'})
        for rel,sha in self.saved['installed'].items():self.assertEqual(digest(self.root/rel),sha)
        self.assertEqual(json.loads((self.state/'state.json').read_text())['selected'],['lynx'])
    @patch.object(e,'game_running',return_value=False)
    def test_external_change_stops_before_commit(self,_):
        out=self.output();(self.root/'root/root').write_bytes(b'external update')
        with self.assertRaises(ValueError):e.transaction(self.config,self.state,self.saved,out,{'scorpion'})
        self.assertEqual((self.root/'root/root').read_bytes(),b'external update')
    @patch.object(e,'game_running',return_value=False)
    def test_interrupted_commit_recovers(self,_):
        rel='root/root';target=self.root/rel;before=digest(target);backup=self.state/'undo';backup.write_bytes(target.read_bytes());target.write_bytes(b'after');dump(self.state/'pending.json',{'id':'crashed','files':[{'bundle':rel,'backup':str(backup),'before':before,'after':digest(target)}]})
        e.recover(self.config,self.state);self.assertEqual(digest(target),before)
    def test_lock_exclusive(self):
        with e.locked(self.state):
            with self.assertRaises(OSError):
                with e.locked(self.state):pass
    def test_old_frontend_cannot_silently_drop_an_installed_new_mod(self):
        with self.assertRaisesRegex(ValueError,'cannot represent'):
            e.validate_frontend({'selected':['sky','lynx']},{'supported_mods':['lynx'],'selected':['lynx']})
    def test_missing_catalogue_declaration_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'frontend'):
            e.validate_frontend({'selected':['sky']},{'selected':[]})
    def test_old_frontend_cannot_drop_installed_operator_choices(self):
        with self.assertRaisesRegex(ValueError,'operator assignments'):
            e.validate_frontend({'selected':[],'operator_assignments':{'operator_30':'shrek'}},{'supported_mods':sorted(e.IDS)})
    def test_old_frontend_cannot_drop_installed_operator_colors(self):
        with self.assertRaisesRegex(ValueError,'operator colors'):
            e.validate_frontend({'selected':[],'operator_appearance':{'game_customs_magenta':False}},{'supported_mods':sorted(e.IDS),'operator_assignments':{}})
    @patch.object(e,'game_running',return_value=False)
    def test_operator_colors_are_committed_and_preserved_by_unrelated_transactions(self,_):
        colors={'model_magenta':{'fishguy':True},'game_customs_magenta':False};installed=e.transaction(self.config,self.state,self.saved,self.output(),{'lynx'},operator_appearance=colors);self.assertEqual(installed['operator_appearance'],colors);unchanged=e.transaction(self.config,self.state,installed,{},set());self.assertEqual(unchanged['operator_appearance'],colors)
    @patch.object(e,'game_running',return_value=False)
    def test_operator_choices_commit_restore_and_survive_unrelated_transactions(self,_):
        chosen={'operator_30':'shrek'};installed=e.transaction(self.config,self.state,self.saved,self.output(),{'lynx'},chosen)
        self.assertEqual(installed['operator_assignments'],chosen)
        same=e.transaction(self.config,self.state,installed,{},set())
        self.assertEqual(same['operator_assignments'],chosen)
        restored=e.transaction(self.config,self.state,same,{r:self.state/'originals'/r for r in self.saved['originals']},set(),{})
        self.assertEqual(restored['operator_assignments'],{});self.assertEqual(restored['installed'],self.saved['installed'])
    def test_current_frontend_can_intentionally_deselect_any_supported_mod(self):
        e.validate_frontend({'selected':['sky','lynx']},{'supported_mods':sorted(e.IDS),'selected':['lynx']})
    def test_catalog_has_every_mod_and_existing_preview(self):
        root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'installer/catalog.json').read_text());self.assertEqual({m['id'] for m in catalog},e.IDS)
        for m in catalog:self.assertTrue((root/'installer'/m['thumbnail']).is_file(),m['id']);self.assertTrue(m['preview_kind'])

if __name__=='__main__':unittest.main()
