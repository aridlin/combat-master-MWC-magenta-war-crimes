#!/usr/bin/env python3
"""Build the independent MWC Lynx cat visual prototype."""
import argparse
import json
from pathlib import Path
from catgun.bundle import build
from catgun.geometry import make_cat,export,render
from catgun.operations import verify,deploy


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['model','build','verify','install','restore'])
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--config',default='catgun.json');args=p.parse_args()
    c=json.loads(Path(args.config).read_text())
    if args.action=='model':
        m=make_cat(c['scale']);print(json.dumps(export(m,c['asset_output']),indent=2));render(m,Path(c['asset_output'])/'preview.png')
    elif args.action=='build':
        config=json.loads(Path(c['base_config']).read_text());result=build(config,c)
        print(json.dumps({'bundles':len(result['files']),'geometry':result['geometry'],'in_game_tested':False},indent=2))
    else:
        config=json.loads(Path(c['base_config']).read_text())
        result=verify(config,c) if args.action=='verify' else deploy(config,c,args.action,args.dry_run)
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
