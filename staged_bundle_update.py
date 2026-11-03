#!/usr/bin/env python3
"""Apply verified staged bundle manifests or restore the exact prior mod stack.

Requires an initialized installer state. Never closes or launches the game.
"""
import argparse,copy,json
from pathlib import Path
from bundle_utils import digest
from halftone.assets import dump
from installer.mwc_installer import engine as e

def run(action,settings):
    c=json.loads(Path(settings['base_config']).read_text());state=Path(settings['state']).resolve();record=Path(settings['record']).resolve()
    with e.locked(state):
        e.recover(c,state);saved=json.loads((state/'state.json').read_text());e.verify_current(c,state,saved)
        if action=='apply':
            if record.exists():raise ValueError('Update already recorded; use a new record or restore the previous update')
            outputs={};manifests=[]
            for filename in settings['manifests']:
                m=json.loads(Path(filename).read_text());manifests.append(m)
                for b in m['files']:
                    rel=b['bundle'];p=Path(b['output'])
                    if rel not in saved['installed']:raise ValueError('Staged output is outside the managed inventory')
                    if digest(p)!=b['output_sha256'] or digest(Path(b['backup']))!=b['source_sha256']:raise ValueError('Staged artifact or source snapshot changed')
                    if rel in outputs:raise ValueError('Overlapping staged modules require explicit composition: '+rel)
                    outputs[rel]=p
            dump(record,{'status':'prepared','before':copy.deepcopy(saved),'manifests':settings['manifests']})
            assignments=settings.get('operator_assignments')
            if assignments is not None:
                from operators.assignments import validate
                assignments=validate(assignments)
            result=e.transaction(c,state,saved,outputs,set(settings['selected']),operator_assignments=assignments)
            journal=state/'transactions'/result['transaction'];undo={r:str(journal/r) for r in outputs if (journal/r).is_file()}
            dump(record,{'status':'applied','before':saved,'after':result,'undo':undo,'in_game_tested':False})
        elif action=='restore':
            rec=json.loads(record.read_text())
            if rec['status']!='applied':raise ValueError('No applied expansion to restore')
            if saved['installed']!=rec['after']['installed']:raise ValueError('Installed selection changed after this update; restore through the manager instead')
            outputs={rel:Path(p) for rel,p in rec['undo'].items()}
            result=e.transaction(c,state,saved,outputs,set(rec['before']['selected']),operator_assignments=rec['before'].get('operator_assignments',{}))
            if result['installed']!=rec['before']['installed']:raise ValueError('Restored stack hashes do not match the recorded prior state')
            rec['status']='restored';dump(record,rec)
        else:raise ValueError('Unknown action')
        (state/'selected.txt').write_text('\n'.join(result['selected'])+'\n')
        from operators.assignments import save_plan
        save_plan(state,result.get('operator_assignments',{}))
        return {'action':action,'selected':result['selected'],'game_process_was_not_closed':True,'in_game_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','restore']);p.add_argument('--config',required=True);a=p.parse_args();print(json.dumps(run(a.action,json.loads(Path(a.config).read_text())),indent=2))
