#!/usr/bin/env python3
"""Build, verify and reversibly install the four original MWC weapon models."""
import argparse,json
from pathlib import Path
from bundle_utils import digest
from halftone.pipeline import build_id
from weapon_models.bundles import BUNDLES,build,verify,deploy,enabled
from weapon_models.imported import export_model as export_authored
from weapon_models.geometry import export_model as export_legacy
from weapon_models.bundles import asset_kind


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','models','build','verify','install','restore']);p.add_argument('--config',default='weapon-models.json');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=json.loads(Path(a.config).read_text());c=json.loads(Path(s['base_config']).read_text())
    if a.action=='prepare':
        build_id(c);s['sources']={r:digest(Path(c['bundle_root'])/r) for r in BUNDLES};Path(a.config).write_text(json.dumps(s,indent=2)+'\n');r={'recorded_baseline':s['sources'],'game_files_changed':False}
    elif a.action=='models':r={n:(export_legacy if asset_kind(s,n)=='legacy_procedural' else export_authored)(n,Path(s['asset_output'])/n) for n in enabled(s)}
    else:r=build(c,s) if a.action=='build' else verify(s) if a.action=='verify' else deploy(c,s,a.action,a.dry_run)
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
