"""Prepare an actual Medigun visual from a local TF2 installation only."""
from pathlib import Path
from operators.library import discover_tf2
from model_import.tf2 import import_models,flatten
from model_import.convert import convert


def prepare(config,work,requested=''):
    work=Path(work);raw=work/'tf2-weapon-import';import_models(discover_tf2(config,requested),raw,['medigun']);source=flatten(raw/'medigun',work/'tf2-weapon-source'/'medigun');destination=work/'tf2-weapon-fitted'/'medigun'
    import json
    meta=json.loads((source/'source.json').read_text())
    convert(source,destination,rotation=[[1,0,0],[0,0,-1],[0,1,0]],length=.95,forward_min=-.32,vertical_center=-.02,provenance={'title':'Team Fortress 2 Medigun','author':'Valve Corporation','license':'Local import only; no redistribution rights granted','source_url':'https://www.teamfortress.com/workshop/','source_files_sha256':meta['source_sha256'],'geometry_created':False,'modifications':'Read-only local import, material atlas, uniform scaling and placement for Minigun visual root. No weapon or healing behavior imported.'})
    return destination
