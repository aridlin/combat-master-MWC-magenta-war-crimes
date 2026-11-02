#!/usr/bin/env python3
"""Clear Little Bird window glass, preserving every other original object."""
import argparse,copy,gc,json,shutil
from pathlib import Path
import UnityPy
from bundle_utils import digest
from halftone.assets import key,dump
from halftone.pipeline import build_id
from deploy_halftone import close_game,replace_verified

RELATIVE='src/src'
MATERIAL='MH6LittleBird_Glass'


def clear_glass(tree):
    d=copy.deepcopy(tree)
    # Blend Zero One contributes nothing; depth and all body materials stay intact.
    settings={'_SrcBlend':0.,'_DstBlend':1.,'_SrcBlendAlpha':0.,'_DstBlendAlpha':1.,'_ZWrite':0.}
    floats=d['m_SavedProperties']['m_Floats'];found=set()
    for i,(name,value) in enumerate(floats):
        if name in settings:floats[i]=(name,settings[name]);found.add(name)
    if not {'_SrcBlend','_DstBlend','_ZWrite'}<=found:raise ValueError('Unexpected glass blend property layout')
    for name,color in d['m_SavedProperties']['m_Colors']:
        if name in ['_BaseColor','_Color']:color['a']=0.
    if '_SURFACE_TYPE_TRANSPARENT' not in d['m_ValidKeywords']:raise ValueError('Glass is not the inspected transparent material')
    return d


def verify(settings):
    r=json.loads((Path(settings['output'])/'manifest.json').read_text())
    for k,h in [('backup','source_sha256'),('output','output_sha256')]:
        if digest(Path(r[k]))!=r[h]:raise ValueError('Helicopter artifact hash mismatch')
    a=UnityPy.load(r['backup']);b=UnityPy.load(r['output'])
    A={key(o.assets_file.name,o.path_id):o for o in a.objects};B={key(o.assets_file.name,o.path_id):o for o in b.objects}
    if set(A)!=set(B):raise ValueError('Helicopter object IDs changed')
    for oid,obj in A.items():
        if oid==r['material']:
            if clear_glass(obj.read_typetree())!=B[oid].read_typetree():raise ValueError('Unexpected helicopter material fields changed')
        elif obj.get_raw_data()!=B[oid].get_raw_data():raise ValueError('Unrelated helicopter/loot data changed')
    return {'material':MATERIAL,'window_opacity':0,'glass_render_bindings':r['glass_render_bindings'],
            'body_frames_collision_loot_scripts_textures_byte_exact':True,'in_game_tested':False}


def build(config,settings):
    build_id(config);source=Path(config['bundle_root'])/RELATIVE
    if digest(source)!=settings.get('source_sha256'):raise ValueError('Run prepare for the intended installed baseline first')
    out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh helicopter output directory')
    backup=Path(settings['backups'])/RELATIVE;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():raise ValueError('Helicopter backup already exists')
    shutil.copyfile(source,backup);env=UnityPy.load(str(backup))
    matches=[o for o in env.objects if o.type.name=='Material' and o.peek_name()==MATERIAL]
    if len(matches)!=1:raise ValueError('Unexpected helicopter glass material count')
    obj=matches[0];count=0
    for o in env.objects:
        if o.type.name in ['MeshRenderer','SkinnedMeshRenderer']:
            count+=any(p.m_FileID==0 and p.m_PathID==obj.path_id for p in o.read().m_Materials)
    if count!=21:raise ValueError('Unexpected Little Bird glass renderer layout')
    oid=key(obj.assets_file.name,obj.path_id);obj.save_typetree(clear_glass(obj.read_typetree()))
    output=out/RELATIVE;output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_name(output.name+'.partial');temp.write_bytes(env.file.save(packer='lz4'));temp.replace(output);del env;gc.collect()
    dump(out/'manifest.json',{'backup':str(backup.resolve()),'output':str(output.resolve()),'material':oid,'glass_render_bindings':count,'source_sha256':digest(backup),'output_sha256':digest(output)})
    return verify(settings)


def deploy(config,settings,action,dry_run):
    build_id(config);r=json.loads((Path(settings['output'])/'manifest.json').read_text());target=Path(config['bundle_root'])/RELATIVE;current=digest(target)
    if current not in [r['source_sha256'],r['output_sha256']]:raise ValueError('Unknown installed helicopter bundle; refusing overwrite')
    result=verify(settings)
    if dry_run:return {'action':action,'dry_run':True,**result}
    source=Path(r['output'] if action=='install' else r['backup']);wanted=r['output_sha256'] if action=='install' else r['source_sha256'];close_game(config)
    if current!=wanted:replace_verified(source,target,current,wanted)
    return {'action':action,'installed_sha256':digest(target),**result}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','build','verify','install','restore']);p.add_argument('--config',default='helicopter-windows.json');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=json.loads(Path(a.config).read_text());c=json.loads(Path(s['base_config']).read_text())
    if a.action=='prepare':
        build_id(c);s['source_sha256']=digest(Path(c['bundle_root'])/RELATIVE);Path(a.config).write_text(json.dumps(s,indent=2)+'\n');result={'recorded_baseline':s['source_sha256'],'game_files_changed':False}
    else:result=build(c,s) if a.action=='build' else verify(s) if a.action=='verify' else deploy(c,s,a.action,a.dry_run)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
