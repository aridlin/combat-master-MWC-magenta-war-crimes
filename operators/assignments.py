"""Explicit per-operator desired assignments, distinct from installed state."""
import json
from pathlib import Path
from halftone.assets import dump

ROOT=Path(__file__).resolve().parents[1]


def catalogue():
    return json.loads((ROOT/'config/operator-targets.json').read_text())['operators'], json.loads((ROOT/'config/operator-models.json').read_text())['models']


def validate(assignments,targets=None,models=None):
    if targets is None or models is None:targets,models=catalogue()
    if not isinstance(assignments,dict):raise ValueError('Operator assignments must be an object')
    targets={x['id']:x for x in targets};models={x['id']:x for x in models}
    if set(assignments)-targets.keys():raise ValueError('Unknown operator target')
    result={}
    claimed={}
    for identifier,model in sorted(assignments.items()):
        if not isinstance(model,str) or model not in models:raise ValueError('Unknown operator model for '+identifier)
        if model=='original':continue
        target=targets[identifier]
        if not target.get('identity_verified'):raise ValueError('Operator identity is unverified: '+identifier)
        for renderer in target['renderers']:
            key=(target['bundle'],renderer['path_id'])
            previous=claimed.get(key)
            if previous and previous[1]!=model:raise ValueError('Operator asset conflict: '+previous[0]+' and '+identifier+' share a renderer')
            claimed[key]=(identifier,model)
        result[identifier]=model
    return result


def save_plan(state,assignments):
    state=Path(state);normalized=validate(assignments)
    dump(state/'operator-plan.json',{'version':1,'assignments':normalized,'installed':False,'status':'Saved choices only; building, rig verification and installation are separate.'})
    (state/'operator-plan.tsv').write_text(''.join(k+'\t'+v+'\n' for k,v in normalized.items()),encoding='utf8')
    return normalized


def load_plan(state):
    path=Path(state)/'operator-plan.json'
    return validate(json.loads(path.read_text())['assignments']) if path.exists() else {}
