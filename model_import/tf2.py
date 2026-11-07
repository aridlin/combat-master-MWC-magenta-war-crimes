"""Import actual models from the user's local TF2 files into a private workdir.

This module ships no Valve content and grants no redistribution rights.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
from .vpk import VPK
from .source import load
from .vtf import image

MODELS = {name: 'player/' + source for name, source in [
    ('scout','scout'), ('soldier','soldier'), ('pyro','pyro'), ('demoman','demo'),
    ('heavy','heavy'), ('engineer','engineer'), ('medic','medic'), ('sniper','sniper'), ('spy','spy')]}
MODELS['medigun'] = 'weapons/c_models/c_medigun/c_medigun'
ARM_MODELS = {name: 'weapons/c_models/c_' + ('demo' if name == 'demoman' else name) + '_arms'
              for name in MODELS if name != 'medigun'}


def flatten(source,output):
    """Normalize the local import to the shared split-corner material format."""
    from PIL import Image
    source,output=Path(source),Path(output);meta=json.loads((source/'source.json').read_text());d=np.load(source/'mesh.npz',allow_pickle=False);order=d['faces'].ravel();materials=[];indices=[]
    output.mkdir(parents=True,exist_ok=True)
    for n,m in enumerate(meta['materials']):
        with Image.open(source/m['image']) as im:pix=np.flipud(np.asarray(im.convert('RGBA'),dtype='<f4')/255)
        name=f'material-{n}.npy';np.save(output/name,pix);materials.append({'name':m['name'],'pixels':name,'alpha_mode':'opaque','base_color_linear':[1.,1.,1.,1.]})
        indices.append(m['index'])
    uv=d['uv'][order].copy();uv[:,1]=1-uv[:,1]
    fm=np.asarray([indices.index(int(i)) for i in d['face_materials']],dtype='<i4')
    arrays={key:d[key][order] for key in ('positions','normals','bone_indices','bone_weights')};arrays.update(uv=uv,faces=np.arange(len(order),dtype='<u4').reshape(-1,3),face_materials=fm,inverse_bind=d['inverse_bind'],bone_parents=d['bone_parents'])
    np.savez_compressed(output/'source.npz',**arrays);meta.update(materials=materials,bone_parents=d['bone_parents'].tolist(),objects=meta['parts']);(output/'source.json').write_text(json.dumps(meta,indent=2)+'\n')
    return output


def import_models(tf, output,names=None,*,first_person=False,lod=0):
    tf, output = Path(tf).resolve(), Path(output).resolve()
    if tf == output or tf in output.parents: raise ValueError('Import output must be outside TF2')
    models = ARM_MODELS if first_person else MODELS
    if names is not None and not set(names)<=models.keys():raise ValueError('Unknown TF2 import selection')
    misc, textures = VPK(tf/'tf2_misc_dir.vpk'), VPK(tf/'tf2_textures_dir.vpk')
    report = []
    for name, model in models.items():
        if names is not None and name not in names:continue
        out = output/name
        out.mkdir(parents=True, exist_ok=True)
        source = {'models/'+model+s: misc.read('models/'+model+s) for s in ('.mdl','.vvd','.dx90.vtx')}
        d = load(*source.values(),lod=lod)
        used = sorted(set(map(int, d['face_materials'])))
        mats = []
        for number in used:
            candidates = ['materials/'+(directory+d['textures'][number]).replace('\\','/').lower()+'.vmt' for directory in ['']+d['material_dirs']]
            path = next((p for p in candidates if p in misc.entries), None)
            if path is None: raise ValueError('Cannot resolve material: '+str(candidates))
            raw = misc.read(path); source[path] = raw
            text = re.sub(r'//[^\n]*', '', raw.decode('utf8','replace'))
            # Prefer the explicit DX8 eye diffuse fallback, preserving authored UVs.
            match = re.search(r'"?\$basetexture"?\s+"([^"\n]+)"', text, re.I)
            if match is None: raise ValueError('Material lacks a supported diffuse: '+path)
            texture = 'materials/'+match[1].replace('\\','/').lower().removesuffix('.vtf')+'.vtf'
            raw = textures.read(texture); source[texture] = raw
            image(raw).convert('RGB').save(out/f'material-{number}.png')
            mats.append({'index': number, 'name': path, 'image': f'material-{number}.png'})
        arrays = {k:v for k,v in d.items() if isinstance(v, np.ndarray)}
        np.savez_compressed(out/'mesh.npz', **arrays)
        meta = {'id':'tf2_'+name,'title':name.title(),'author':'Valve Corporation','source':'Local Team Fortress 2 installation; Steam App 440','redistribution':'Valve content is not included in this project; local import only. No new license granted.', 'materials':mats,'bone_names':d['bone_names'],'parts':d['parts'],'vertices':len(d['positions']),'triangles':len(d['faces']),'source_sha256':{p:hashlib.sha256(b).hexdigest() for p,b in source.items()},'game_files_modified':False,'gameplay_data_imported':False,'in_game_tested':False}
        meta['source_variant'] = 'first_person_arms' if first_person else 'world'
        if lod:meta['source_lod']=lod
        (out/'source.json').write_text(json.dumps(meta,indent=2)+'\n')
        report.append({k:meta[k] for k in ('id','vertices','triangles','in_game_tested')})
        print(name,meta['vertices'],'vertices',meta['triangles'],'triangles',flush=True)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('tf');p.add_argument('output');a=p.parse_args()
    import_models(a.tf,a.output)
