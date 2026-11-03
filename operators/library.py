"""Resolve permitted packaged sources and read-only local TF2 imports."""
import json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def discover_tf2(config,requested=''):
    if requested:
        p=Path(requested).expanduser().resolve();p=p if (p/'tf2_misc_dir.vpk').is_file() else p/'tf'
        if not (p/'tf2_misc_dir.vpk').is_file():raise ValueError('Selected TF2 folder does not contain tf/tf2_misc_dir.vpk')
        return p
    from configure import libraries
    found=[]
    for library in libraries():
        manifest=library/'steamapps/appmanifest_440.acf'
        if not manifest.is_file():continue
        match=re.search(r'"installdir"\s+"([^"]+)"',manifest.read_text())
        if match:
            p=library/'steamapps/common'/match[1]/'tf'
            if (p/'tf2_misc_dir.vpk').is_file():found.append(p.resolve())
    found=list(dict.fromkeys(found))
    if len(found)!=1:raise ValueError('Choose the local TF2 installation; automatic detection found '+str(len(found))+' usable copies')
    return found[0]


def prepare(config,assignments,work,tf2='',appearance=None):
    from .styles import normalize
    appearance=normalize(appearance)
    required=set(assignments.values());result={}
    for model in required & {'shrek','fishguy','mario','minecraft_steve'}:
        source=ROOT/'assets/operator-sources'/model
        if not (source/'source.json').is_file():raise ValueError('Packaged operator source missing: '+model)
        meta=json.loads((source/'source.json').read_text());result[model]={'source':str(source),'profile':meta['profile'],'style':'original','glasses':model=='shrek'}
    tf_models=required & {'tf2_'+name for name in ['scout','soldier','pyro','demoman','heavy','engineer','medic','sniper','spy']}
    if tf_models:
        from model_import.tf2 import import_models,flatten
        raw=Path(work)/'tf2-local';names=[name.removeprefix('tf2_') for name in tf_models];import_models(discover_tf2(config,tf2),raw,names)
        for model in tf_models:
            source=flatten(raw/model.removeprefix('tf2_'),Path(work)/'operator-sources'/model);result[model]={'source':str(source),'profile':model,'style':'magenta'}
    if 'titanfall_pilot' in required:
        from .autorig import build as pilot_rig
        source=pilot_rig(config,ROOT/'assets/operator-sources/titanfall_pilot',Path(work)/'operator-sources/titanfall_pilot');result['titanfall_pilot']={'source':str(source),'profile':'titanfall_transfer','style':'magenta'}
    missing=required-result.keys()
    if missing:raise ValueError('These models are still being prepared and cannot be installed yet: '+', '.join(sorted(missing)))
    for model,spec in result.items():spec['style']='magenta' if appearance['model_magenta'][model] else 'original'
    return result
