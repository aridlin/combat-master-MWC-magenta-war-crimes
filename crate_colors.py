#!/usr/bin/env python3
"""Independent, reversible blue albedos for CombatZone loot-crate materials."""
import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path
import shutil
import UnityPy
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from halftone.encoding import apply_pattern,alpha_hash
from halftone.pipeline import build_id,safe_output
from deploy_halftone import close_game,replace_verified

ROOT=Path(__file__).resolve().parent
RELATIVE='src/src'
MATERIAL_NAMES={'Box-1','Box-2','Box-3'}


def verify(c,settings):
    report=json.loads((Path(settings['output'])/'manifest.json').read_text());build_id(c)
    if digest(Path(report['backup']))!=report['source_sha256'] or digest(Path(report['output']))!=report['output_sha256']:
        raise ValueError('Crate artifact hash mismatch')
    before_env=UnityPy.load(report['backup']);after_env=UnityPy.load(report['output'])
    before={key(o.assets_file.name,o.path_id):o for o in before_env.objects}
    after={key(o.assets_file.name,o.path_id):o for o in after_env.objects}
    added={r['new_texture'] for r in report['changes']};materials={r['material'] for r in report['changes']}
    if set(after)!=set(before)|added:raise ValueError('Unexpected crate object IDs')
    for oid,obj in before.items():
        if oid not in materials:
            if obj.get_raw_data()!=after[oid].get_raw_data():raise ValueError('Unrelated crate object data changed')
    for r in report['changes']:
        a=before[r['material']].read_typetree();b=after[r['material']].read_typetree()
        for slot,entry in a['m_SavedProperties']['m_TexEnvs']:
            if slot in ('_BaseMap','_MainTex'):
                entry['m_Texture']={'m_FileID':0,'m_PathID':int(r['new_texture'].rsplit(':',1)[1])}
        if a!=b:raise ValueError('Only crate albedo references may change')
        if alpha_hash(after[r['new_texture']].read().image)!=r['alpha_sha256']:raise ValueError('Crate alpha changed')
    return {'materials':len(materials),'dedicated_albedos':len(added),'color':settings['color'],
            'normal_maps_geometry_collision_animation_other_materials_byte_exact':True,'in_game_tested':False}


def build(c,settings):
    build_id(c);directory=safe_output(settings['output'],c);directory.mkdir(parents=True,exist_ok=True)
    if (directory/'manifest.json').exists():raise ValueError('Existing blue-crate build; choose a fresh output directory')
    full=json.loads((Path(c['paths']['reports'])/'modifications.json').read_text())
    base=next(b for b in full['bundles'] if b['bundle']==RELATIVE);source=Path(base['output'])
    if digest(source)!=base['output_sha256']:raise ValueError('Retexture baseline mismatch')
    backup=safe_output(Path(settings['backups'])/RELATIVE,c);backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        if digest(backup)!=base['output_sha256']:raise ValueError('Crate backup belongs to another baseline')
    else:
        with source.open('rb') as incoming,backup.open('xb') as stream:shutil.copyfileobj(incoming,stream)
    env=UnityPy.load(str(backup));expected=inventory(env)
    objects={key(o.assets_file.name,o.path_id):o for o in env.objects};changes=[]
    for obj in list(objects.values()):
        if obj.type.name!='Material' or obj.peek_name() not in MATERIAL_NAMES:continue
        material=obj.read();albedo=next(entry.m_Texture for name,entry in material.m_SavedProperties.m_TexEnvs if name=='_BaseMap')
        if albedo.m_FileID!=0:raise ValueError('Unexpected external crate texture')
        original=objects[key(obj.assets_file.name,albedo.m_PathID)];clone=copy.copy(original)
        identifier=int.from_bytes(hashlib.sha256(('MWC-blue-crate-'+material.m_Name).encode()).digest()[:7],'little')+1
        while identifier in obj.assets_file.objects:identifier+=1
        clone.path_id=identifier;clone.data=None;obj.assets_file.objects[identifier]=clone
        texture=clone.read();texture.m_Name='MWC_BlueCrate_'+material.m_Name
        details=apply_pattern(texture,settings['color'],c['generation'])
        for slot,entry in material.m_SavedProperties.m_TexEnvs:
            if slot in ('_BaseMap','_MainTex'):entry.m_Texture.m_FileID=0;entry.m_Texture.m_PathID=identifier
        material.save()
        for changed in (obj,clone):
            expected[(changed.assets_file.name,changed.path_id)]={'type':changed.type.name,'sha256':hashlib.sha256(changed.data).hexdigest()}
        changes.append({'name':material.m_Name,'material':key(obj.assets_file.name,obj.path_id),
            'original_texture':key(original.assets_file.name,original.path_id),'new_texture':key(clone.assets_file.name,identifier),**details})
    if {r['name'] for r in changes}!=MATERIAL_NAMES:raise ValueError('Did not find all three loot-crate materials')
    output=directory/RELATIVE;output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_name(output.name+'.partial')
    with temp.open('wb') as stream:stream.write(env.file.save(packer='lz4'))
    del env,objects;gc.collect();checked=UnityPy.load(str(temp))
    if inventory(checked)!=expected:raise ValueError('Crate serialization mismatch')
    del checked;gc.collect();temp.replace(output)
    report={'bundle':RELATIVE,'backup':str(backup.resolve()),'source_sha256':digest(backup),
            'output':str(output.resolve()),'output_sha256':digest(output),'changes':changes,'in_game_tested':False}
    dump(directory/'manifest.json',report);result=verify(c,settings);dump(directory/'verification.json',result);return result


def deploy(c,settings,action,dry_run):
    build_id(c);r=json.loads((Path(settings['output'])/'manifest.json').read_text())
    target=(Path(c['bundle_root'])/RELATIVE).resolve();current=digest(target)
    if current not in (r['source_sha256'],r['output_sha256']):raise ValueError('Unknown installed crate bundle; refusing overwrite')
    result=verify(c,settings)
    if dry_run:return {'dry_run':True,'action':action,**result}
    close_game(c);source=Path(r['output'] if action=='install' else r['backup'])
    wanted=r['output_sha256'] if action=='install' else r['source_sha256']
    if current!=wanted:replace_verified(source,target,current,wanted)
    result={'action':action,'installed_sha256':digest(target),'color':settings['color'],'in_game_tested':False}
    dump(Path(settings['output'])/'deployment.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify','install','restore'])
    p.add_argument('--config',default='crate-colors.json');p.add_argument('--dry-run',action='store_true');args=p.parse_args()
    settings=json.loads(Path(args.config).read_text());c=json.loads(Path(settings['base_config']).read_text())
    result=build(c,settings) if args.action=='build' else verify(c,settings) if args.action=='verify' else deploy(c,settings,args.action,args.dry_run)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
