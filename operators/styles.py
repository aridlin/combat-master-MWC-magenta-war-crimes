"""Independent appearance preferences for modded and native operator models."""
import json
from pathlib import Path
from .assignments import catalogue


def normalize(value=None,players=False):
    _,models=catalogue();defaults={m['id']:m['id'].startswith('tf2_') or m['id']=='titanfall_pilot' for m in models if m['id']!='original'}
    if value is None:return {'model_magenta':defaults,'game_customs_magenta':bool(players)}
    if not isinstance(value,dict) or set(value)-{'model_magenta','game_customs_magenta'}:raise ValueError('Invalid operator appearance preferences')
    choices=value.get('model_magenta',{})
    if not isinstance(choices,dict) or set(choices)-defaults.keys() or any(type(v) is not bool for v in choices.values()):raise ValueError('Model magenta choices must be known model IDs and booleans')
    native=value.get('game_customs_magenta',bool(players))
    if type(native) is not bool:raise ValueError('Native operator magenta choice must be a boolean')
    return {'model_magenta':{**defaults,**choices},'game_customs_magenta':native}


def save(state,value,players=False):
    from halftone.assets import dump
    state=Path(state);value=normalize(value,players);dump(state/'operator-appearance.json',value);(state/'operator-appearance.tsv').write_text('game_customs\t'+str(int(value['game_customs_magenta']))+'\n'+''.join(k+'\t'+str(int(v))+'\n' for k,v in value['model_magenta'].items()),encoding='utf8');return value


def load(state,fallback=None,players=False):
    path=Path(state)/'operator-appearance.json';return normalize(json.loads(path.read_text()) if path.exists() else fallback,players)
