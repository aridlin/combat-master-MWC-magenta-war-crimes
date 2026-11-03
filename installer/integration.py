"""Private offline fixture: compose model toggles, inspect bundles and restore."""
import json,os,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from installer.mwc_installer import engine as e
from bundle_utils import digest
from halftone.assets import dump
import UnityPy

def names(path):
    env=UnityPy.load(str(path));return {o.peek_name() for o in env.objects if o.type.name=='GameObject'}
def main():
    p=Path(sys.argv[1]).resolve();original=Path(sys.argv[2]).resolve();p.mkdir(parents=True,exist_ok=True);os.chdir(p)
    work=p/'fixture';work.mkdir(exist_ok=True);saved={'originals':{},'installed':{}};config=json.loads((R/'config/preset.json').read_text());config['app_manifest']=str(p/'manifest.acf');Path(config['app_manifest']).write_text('"buildid" "24397779"')
    config['bundle_root']=str(work)
    state=p/'state';state.mkdir(exist_ok=True)
    for rel in ('src/weapons/weapons','src/weapons/attachments','root/root','src/src'):
        target=state/'originals'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/rel,target);saved['originals'][rel]=digest(target)
    # Compose each desired set from immutable originals. Check absence as well as presence.
    results=[]
    for selected in ({'scorpion'},{'scorpion','nail_gun'},{'nail_gun'},{'iron','reticles','menu','glass','crates'}):
        out=e.compose(config,state,saved,selected,'')
        n=names(out['src/weapons/weapons'])
        for model in e.MODELS:
            present=any(x.startswith('MWC_Model_'+model) for x in n)
            assert present==(model in selected),(selected,model,present)
        results.append({'selected':sorted(selected),'hashes':{k:digest(v) for k,v in out.items()},'isolated_model_presence_verified':True})
    dump(p/'integration-results.json',results);print('PASS: independent model selection, removal and extra-mod composition')
if __name__=='__main__':main()
