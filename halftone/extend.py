"""Incremental coverage expansion using verified staged bundles and originals."""
import collections
import gc
import hashlib
import json
import shutil
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from .assets import dump,key,load_scan
from .classify import classify
from .encoding import apply_pattern
from .pipeline import build_id,safe_output,verify_one
from .materials import finalize


def extend(config):
    version=build_id(config); report_dir=Path(config['paths']['reports'])
    manifest_path=report_dir/'modifications.json'; manifest=json.loads(manifest_path.read_text())
    if manifest['build_id']!=version: raise ValueError('Build mismatch')
    classified=classify(config); groups=collections.defaultdict(list)
    for r in classified['assets']:
        if r['action']=='replace': groups[r['bundle']].append(r)
    originals={b['bundle']:b for b in load_scan(config['paths']['reports'])}
    outputs={b['bundle']:b for b in manifest['bundles']}
    settings_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    touched=0
    for relative,records in groups.items():
        b=outputs.get(relative)
        if b is None:
            scan=originals[relative]; backup=safe_output(Path(config['paths']['backups'])/relative,config)
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists(): shutil.copyfile(scan['source'],backup)
            if digest(backup)!=scan['sha256']: raise ValueError('Original snapshot mismatch')
            path=safe_output(Path(config['paths']['output'])/relative,config); path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(backup,path)
            b={'bundle':relative,'backup':str(backup),'source':scan['source'],'source_sha256':scan['sha256'],
               'output':str(path),'output_sha256':digest(path),'changes':[],'checks':{},'build_id':version}
            manifest['bundles'].append(b); outputs[relative]=b
        prior={c['id']:c for c in b['changes']}
        pending=[r for r in records if r['id'] not in prior or prior[r['id']]['category']!=r['category']]
        path=Path(b['output'])
        if digest(path)!=b['output_sha256'] or digest(Path(b['backup']))!=b['source_sha256']:
            raise ValueError('Staged output or backup changed')
        if pending:
            print(f'Extending {relative}: {len(pending)} albedos',flush=True)
            env=UnityPy.load(str(path)); expected=inventory(env)
            by_id={key(o.assets_file.name,o.path_id):o for o in env.objects}; changes=[]
            for r in pending:
                obj=by_id[r['id']]; texture=obj.read()
                details=apply_pattern(texture,config['categories'][r['category']]['color'],config['generation'])
                changes.append({'id':r['id'],'name':r['name'],'category':r['category'],**details})
                expected[(obj.assets_file.name,obj.path_id)]['sha256']=hashlib.sha256(obj.data).hexdigest()
            temp=path.with_name(path.name+'.extend-partial')
            with temp.open('wb') as stream: stream.write(env.file.save(packer='lz4'))
            del texture,obj,env,by_id; gc.collect()
            verify_one(temp,expected,changes); temp.replace(path)
            prior.update({c['id']:c for c in changes}); b['changes']=list(prior.values())
            b['output_sha256']=digest(path); b['diffuse_material_cleanup_complete']=False
            touched+=len(pending)
        b['settings_sha256']=settings_hash
        dump(str(path)+'.verification.json',b); dump(manifest_path,manifest)
    # Keep outputs not touched by new classification hash-consistent.
    for b in manifest['bundles']:
        b['settings_sha256']=settings_hash
        dump(str(b['output'])+'.verification.json',b)
    dump(manifest_path,manifest); finalize(config)
    return {'new_or_recolored_albedos':touched,'bundles':len(manifest['bundles']),
            'texture_count':sum(len(b['changes']) for b in manifest['bundles'])}
