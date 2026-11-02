#!/usr/bin/env python3
"""Build the independent MWC Lynx cat visual prototype."""
import argparse
import json
from pathlib import Path
from catgun.bundle import build
from catgun.geometry import make_cat,export,render
from catgun.operations import verify,deploy
from catgun.source_model import load_cat


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['import','model','build','verify','install','restore'])
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--config',default='catgun.json');p.add_argument('--addon');args=p.parse_args()
    c=json.loads(Path(args.config).read_text())
    if args.action=='import':
        from catgun.import_addon import extract
        if not args.addon:p.error('--addon is required for import')
        print(json.dumps(extract(args.addon,c['source_assets']),indent=2))
    elif args.action=='model':
        m,coat=load_cat(c);directory=Path(c['asset_output']);directory.mkdir(parents=True,exist_ok=True)
        if c.get('model','procedural')=='procedural':print(json.dumps(export(m,directory),indent=2))
        render(m,directory/'preview.png',texture=coat,label='M1A0 local import | original mesh and tail | software preview, not in-game' if c.get('model')=='m1a0' else None)
    elif args.action=='build':
        config=json.loads(Path(c['base_config']).read_text());result=build(config,c)
        print(json.dumps({'bundles':len(result['files']),'geometry':result['geometry'],'in_game_tested':False},indent=2))
    else:
        config=json.loads(Path(c['base_config']).read_text())
        result=verify(config,c) if args.action=='verify' else deploy(config,c,args.action,args.dry_run)
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
