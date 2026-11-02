#!/usr/bin/env python3
"""Deploy/restore only verified visual bundles. Never launches the game."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import tempfile
import time

from bundle_utils import digest
from halftone.assets import dump
from halftone.pipeline import build_id

ROOT=Path(__file__).resolve().parent


def replace_verified(source,target,expected_before,expected_after):
    if digest(target)!=expected_before: raise ValueError('Target changed: '+str(target))
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(prefix='.cm-halftone-',dir=target.parent,delete=False) as stream:
            temporary=Path(stream.name)
            with source.open('rb') as incoming: shutil.copyfileobj(incoming,stream)
            stream.flush(); os.fsync(stream.fileno())
        shutil.copystat(target,temporary)
        if digest(temporary)!=expected_after or digest(target)!=expected_before:
            raise ValueError('Staged hash mismatch or concurrent modification')
        os.replace(temporary,target); temporary=None
        if digest(target)!=expected_after: raise ValueError('Installed hash mismatch')
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def close_game(config):
    executable=Path(config['bundle_root']).parents[2]/'CombatMaster.x86_64'
    pids=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try: matches=(p/'exe').resolve()==executable
        except OSError: continue
        if matches:
            os.kill(int(p.name),signal.SIGTERM); pids.append(p)
            print('Closing Combat Master:',p.name,flush=True)
    deadline=time.monotonic()+10
    while any(p.exists() for p in pids):
        if time.monotonic()>deadline: raise ValueError('Game has not exited; no assets replaced')
        time.sleep(.2)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','restore'])
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--config',default=None)
    args=parser.parse_args()
    os.chdir(ROOT)
    active=ROOT/'active-halftone.json'
    config_name=args.config or (json.loads(active.read_text())['config'] if active.exists() else 'halftone.json')
    config=json.loads((ROOT/config_name).read_text()); version=build_id(config)
    report_dir=ROOT/config['paths']['reports']
    manifest=json.loads((report_dir/'modifications.json').read_text())
    journal_path=report_dir/'deployment.json'
    journal=json.loads(journal_path.read_text()) if journal_path.exists() else None
    if manifest['build_id']!=version: raise ValueError('Build mismatch')
    base=Path(config['bundle_root']).resolve()
    previous={}
    if journal:
        if journal['build_id']!=version: raise ValueError('Deployment belongs to a different game build')
        previous={r['bundle']:r for r in journal['files']}
    plans=[]
    for b in manifest['bundles']:
        relative=Path(b['bundle'])
        target=(base/relative).resolve()
        if relative.is_absolute() or '..' in relative.parts or base not in target.parents:
            raise ValueError('Unsafe installed path')
        source=Path(b['output']); original=Path(b['backup'])
        if digest(source)!=b['output_sha256'] or digest(original)!=b['source_sha256']:
            raise ValueError('Artifact/backup mismatch: '+b['bundle'])
        current=digest(target)
        known={b['source_sha256'],b['output_sha256']}
        old_manifest=ROOT/'reports/halftone/modifications.json'
        if old_manifest.exists():
            old=json.loads(old_manifest.read_text())
            for old_bundle in old['bundles']:
                if old_bundle['bundle']==b['bundle'] and old_bundle['source_sha256']==b['source_sha256']:
                    known.add(old_bundle['output_sha256'])
        if b['bundle']=='src/thrid_person':
            for variant in ('player-textures-only','pink-player-textures'):
                legacy=ROOT/'experiments'/variant/'verification.json'
                if legacy.exists():
                    legacy_report=json.loads(legacy.read_text())
                    if legacy_report['source_sha256']==b['source_sha256']:
                        known.add(legacy_report['output_sha256'])
        if b['bundle'] in previous: known.add(previous[b['bundle']]['preinstall_sha256'])
        if current not in known: raise ValueError('Unknown installed version: '+b['bundle'])
        if args.action=='restore':
            # Restore this deployment's exact preinstall state (including the
            # earlier pink experiment), not an older unrelated Steam build.
            if b['bundle'] not in previous: raise ValueError('No installation snapshot for '+b['bundle'])
            old=previous[b['bundle']]; source=Path(old['preinstall_backup']); wanted=old['preinstall_sha256']
            if digest(source)!=wanted: raise ValueError('Preinstall backup mismatch')
        else:
            wanted=b['output_sha256']
        plans.append({'bundle':b['bundle'],'target':str(target),'source':str(source),
                      'current':current,'wanted':wanted,'original_sha256':b['source_sha256']})
    print(f'Preflight verified: {len(plans)} bundles; action={args.action}; dry_run={args.dry_run}',flush=True)
    if args.dry_run: return
    close_game(config)
    if args.action=='install' and journal is None:
        snapshot=ROOT/'backups/halftone-preinstall'/time.strftime('%Y%m%d-%H%M%S')
        files=[]
        for p in plans:
            target=Path(p['target'])
            if digest(target)!=p['current']: raise ValueError('Target changed while closing the game')
            backup=snapshot/p['bundle']; backup.parent.mkdir(parents=True,exist_ok=True)
            with target.open('rb') as incoming,backup.open('xb') as stream: shutil.copyfileobj(incoming,stream)
            if digest(backup)!=p['current']: raise ValueError('Snapshot hash mismatch')
            files.append({'bundle':p['bundle'],'target':p['target'],
                'preinstall_backup':str(backup),'preinstall_sha256':p['current'],
                'installed_sha256':p['wanted']})
        journal={'build_id':version,'files':files,'action':'prepared','completed':[],
                 'game_launched':False,'in_game_tested':False}
        dump(journal_path,journal)
    if journal is None: raise ValueError('No rollback journal')
    # Recheck every file before beginning the transaction.
    for p in plans:
        if digest(Path(p['target']))!=p['current']: raise ValueError('Target changed before transaction')
    changed=[]
    completed=[]
    try:
        for p in plans:
            if p['current']!=p['wanted']:
                replace_verified(Path(p['source']),Path(p['target']),p['current'],p['wanted'])
                changed.append(p)
            journal['action']=args.action+'-in-progress'
            completed.append(p['bundle'])
            journal['completed']=list(completed)
            dump(journal_path,journal)
            print(args.action+': '+p['bundle']+' — hash verified',flush=True)
    except Exception:
        # Roll back this invocation's successful replacements to their exact
        # previous versions, provided no external actor changed the target.
        previous_by_name={x['bundle']:x for x in journal['files']}
        for p in reversed(changed):
            if args.action=='install':
                old=previous_by_name[p['bundle']]; rollback=Path(old['preinstall_backup'])
            else:
                rollback=Path(next(b['output'] for b in manifest['bundles'] if b['bundle']==p['bundle']))
            if digest(rollback)==p['current']:
                replace_verified(rollback,Path(p['target']),p['wanted'],p['current'])
        journal['action']='failed-with-rollback-attempt'; dump(journal_path,journal)
        raise
    for p in plans:
        if digest(Path(p['target']))!=p['wanted']: raise ValueError('Final target verification failed')
    journal['action']='installed' if args.action=='install' else 'restored-preinstall-state'
    journal['completed']=[p['bundle'] for p in plans]
    dump(journal_path,journal)
    if args.action=='install': dump(active,{'config':config_name,'journal':str(journal_path)})
    print('Completed and verified '+str(len(plans))+' bundles. Game remains closed.',flush=True)


if __name__=='__main__': main()
