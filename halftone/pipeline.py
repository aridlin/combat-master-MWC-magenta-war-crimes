"""Stage, verify and restore bundle copies with SHA-256 and version guards."""
import collections
import gc
import hashlib
import json
import re
import shutil
from pathlib import Path
import UnityPy
from bundle_utils import digest, inventory
from .assets import dump, key, load_scan, pointer
from .classify import classify
from .encoding import apply_pattern, alpha_hash


def build_id(config):
    text=Path(config['app_manifest']).read_text()
    match=re.search(r'"buildid"\s+"([^"]+)"',text)
    if not match or match[1]!=config['expected_build_id']:
        raise ValueError('Steam build changed: rescan and review mappings before editing')
    return match[1]


def safe_output(path, config):
    requested=Path(path)
    path=requested.resolve()
    source=Path(config['bundle_root']).resolve()
    if path==source or source in path.parents:
        raise ValueError('Staged output/backup paths must be outside the Steam bundle tree')
    # Restrict this CLI to the project workspace for reviewable staged artifacts.
    workspace=Path.cwd().resolve()
    if workspace not in path.parents:
        # Bulk work directories may live on another disk. Only explicitly
        # registered workspace links qualify; an arbitrary symlink does not.
        manifest=workspace/'.mwc-storage.json'
        permitted=False
        if manifest.is_file():
            storage=json.loads(manifest.read_text())
            if storage.get('version')!=1 or storage.get('workspace')!=str(workspace):
                raise ValueError('Workspace storage manifest does not match this workspace')
            for entry in storage.get('mounts',[]):
                alias=Path(entry['alias'])
                if alias.is_absolute() or '..' in alias.parts or not alias.parts:
                    raise ValueError('Invalid workspace storage alias')
                link=workspace/alias;target=Path(entry['target'])
                if not target.is_absolute():raise ValueError('Storage target must be absolute')
                target=target.resolve()
                # Later pipeline steps reuse this resolved path, so both the
                # workspace alias and its registered target must be accepted.
                if link.is_symlink() and link.resolve()==target and (path==target or target in path.parents):
                    permitted=True;break
        if not permitted:
            raise ValueError('Output and backup paths must stay inside the project workspace or registered storage')
    return path


def verify_one(path, expected, changes):
    env=UnityPy.load(str(path))
    actual=inventory(env)
    if actual!=expected:
        raise ValueError('Serialized object set/bytes differ after reopening')
    by_id={key(o.assets_file.name,o.path_id):o for o in env.objects}
    for change in changes:
        t=by_id[change['id']].read()
        if alpha_hash(t.image)!=change['alpha_sha256']:
            raise ValueError('Reopened alpha mismatch: '+t.m_Name)
        if (t.m_Width,t.m_Height,t.m_TextureFormat,t.m_MipCount)!=(change['width'],change['height'],change['format'],change['mips']):
            raise ValueError('Reopened texture metadata mismatch')
        if t.m_TextureSettings.m_FilterMode!=2 or t.m_TextureSettings.m_WrapU!=0 or t.m_TextureSettings.m_WrapV!=0 or t.m_ColorSpace!=1:
            raise ValueError('Incorrect filtering, wrapping or color space')
    del env
    gc.collect()


def apply(config,dry_run=False,only_bundle=None):
    version=build_id(config)
    classification=classify(config)
    groups=collections.defaultdict(list)
    for record in classification['assets']:
        if record['action']=='replace' and (not only_bundle or record['bundle'] in only_bundle):
            groups[record['bundle']].append(record)
    scans={b['bundle']:b for b in load_scan(config['paths']['reports'])}
    output=safe_output(config['paths']['output'],config)
    backups=safe_output(config['paths']['backups'],config)
    if not config['backup']['enabled']:
        raise ValueError('Backups are required for bundle edits')
    manifest_path=Path(config['paths']['reports'])/'modifications.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'build_id':version,'bundles':[]}
    if manifest['build_id']!=version:
        raise ValueError('Staged manifest build mismatch')
    planned=[{'bundle':b,'eligible_textures':len(x)} for b,x in groups.items()]
    if dry_run:
        return {'dry_run':True,'plan':planned,'texture_count':sum(len(x) for x in groups.values())}
    settings_hash=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    if any(b['settings_sha256']!=settings_hash for b in manifest['bundles']):
        raise ValueError('Configuration changed: select fresh report/output paths and rescan; old category outputs will not be silently reused')
    for relative,records in groups.items():
        scan=scans[relative]
        if scan['unity_version']!=config['expected_unity_version']:
            raise ValueError('Unsupported Unity version: '+relative)
        source=Path(scan['source'])
        if digest(source)!=scan['sha256']:
            raise ValueError('Input changed since scan: '+relative)
        dst=safe_output(output/relative,config)
        report_path=Path(str(dst)+'.verification.json')
        if report_path.exists():
            prior=json.loads(report_path.read_text())
            if prior['settings_sha256']==settings_hash and dst.exists() and digest(dst)==prior['output_sha256']:
                print('Verified output cached:',relative,flush=True)
                continue
            raise ValueError('Existing output uses different settings; choose a new output directory')
        backup=safe_output(backups/relative,config)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            with source.open('rb') as incoming,backup.open('xb') as stream:
                shutil.copyfileobj(incoming,stream)
        if digest(backup)!=scan['sha256']:
            raise ValueError('Backup hash mismatch')
        print(f'Editing {relative}: {len(records)} albedo textures',flush=True)
        env=UnityPy.load(str(backup))
        before=inventory(env)
        by_id={key(o.assets_file.name,o.path_id):o for o in env.objects}
        changes=[]
        for i,record in enumerate(records,1):
            obj=by_id[record['id']]
            texture=obj.read()
            details=apply_pattern(texture,config['categories'][record['category']]['color'],config['generation'])
            changes.append({'id':record['id'],'name':record['name'],'category':record['category'],**details})
            if i%50==0:
                print(f'  {i}/{len(records)} verified in memory',flush=True)
        expected=inventory(env)
        changed_keys={r['id'] for r in records}
        for oid,obj in by_id.items():
            k=(obj.assets_file.name,obj.path_id)
            if oid in changed_keys:
                expected[k]['sha256']=hashlib.sha256(obj.data).hexdigest()
            elif before[k]!=expected[k]:
                raise ValueError('Unrelated object changed')
        if set(before)!=set(expected):
            raise ValueError('Unexpected object creation/removal')
        dst.parent.mkdir(parents=True,exist_ok=True)
        temporary=dst.with_name(dst.name+'.partial')
        with temporary.open('wb') as stream:
            stream.write(env.file.save(packer='lz4'))
        del texture,obj,by_id,env
        gc.collect()
        verify_one(temporary,expected,changes)
        if digest(source)!=scan['sha256']:
            raise ValueError('Source changed while staging')
        temporary.replace(dst)
        report={'bundle':relative,'source':str(source.resolve()),'backup':str(backup),'output':str(dst),
                'source_sha256':scan['sha256'],'output_sha256':digest(dst),'settings_sha256':settings_hash,
                'build_id':version,'changes':changes,
                'checks':{'reopened':True,'same_object_ids_and_types':True,'all_unselected_objects_unchanged':True,
                          'materials_shaders_geometry_animations_unchanged':True,'all_selected_base_alpha_exact':True,
                          'same_dimensions':True,'full_mip_chains':True,'srgb_repeat_trilinear':True},
                'in_game_tested':False,'uv_scale':'original UVs and material tiling retained; metric scale not guaranteed'}
        dump(report_path,report)
        manifest['bundles']=[b for b in manifest['bundles'] if b['bundle']!=relative]+[report]
        dump(manifest_path,manifest)
        print('Reopened, alpha-verified and hash-verified:',relative,flush=True)
    from .materials import finalize
    finalize(config)
    return {'manifest':str(manifest_path),'bundles':len(manifest['bundles']),
            'textures':sum(len(b['changes']) for b in manifest['bundles'])}


def verify(config):
    manifest=json.loads((Path(config['paths']['reports'])/'modifications.json').read_text())
    declared_clones={c['id'] for b in manifest['bundles'] for c in b.get('cloned_textures',[])}
    results=[]
    for b in manifest['bundles']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:
            raise ValueError('Artifact hash mismatch: '+b['bundle'])
        # Reopen again; materials/references/geometry are compared to the backup.
        original=UnityPy.load(b['backup']); before=inventory(original)
        original_materials={key(o.assets_file.name,o.path_id):o for o in original.objects if o.type.name=='Material'}
        modified=UnityPy.load(b['output']); after=inventory(modified)
        changes={c['id']:c for c in b['changes']}
        material_changes={c['id']:c for c in b.get('material_changes',[])}
        array_changes={c['id']:c for c in b.get('array_changes',[])}
        clones={c['id']:c for c in b.get('cloned_textures',[])}
        bindings={c['id']:c for c in b.get('material_binding_changes',[])}
        added={(oid.rsplit(':',1)[0],int(oid.rsplit(':',1)[1])) for oid in clones}
        if set(before)|added!=set(after): raise ValueError('Unexpected object IDs changed')
        for obj in modified.objects:
            k=(obj.assets_file.name,obj.path_id); oid=key(*k)
            if oid not in changes and oid not in material_changes and oid not in array_changes and oid not in clones and oid not in bindings and before[k]!=after[k]: raise ValueError('Non-target data changed')
            if oid in clones and alpha_hash(obj.read().image)!=clones[oid]['alpha_sha256']: raise ValueError('Cloned alpha changed')
            if oid in bindings:
                from .materials import check_material_diff
                check_material_diff(original_materials[oid],obj,bindings[oid]['bindings'])
                old_slots=dict(original_materials[oid].read().m_SavedProperties.m_TexEnvs)
                new_slots=dict(obj.read().m_SavedProperties.m_TexEnvs)
                for binding in bindings[oid]['bindings']:
                    old_pointer=pointer(old_slots[binding['slot']].m_Texture,original_materials[oid].assets_file)
                    new_pointer=pointer(new_slots[binding['slot']].m_Texture,obj.assets_file)
                    wanted=binding['source_id'].rsplit(':',1)[0]+':'+str(binding['new_path_id'])
                    if old_pointer!=binding['source_id'] or new_pointer!=wanted or wanted not in declared_clones:
                        raise ValueError('New material pointer does not resolve to a declared category texture')
            if oid in array_changes:
                from .arrays import verify_array
                verify_array(obj.read(),array_changes[oid])
            if oid in material_changes and oid not in bindings:
                from .materials import check_material_diff
                check_material_diff(original_materials[oid],obj)
            if oid in changes and alpha_hash(obj.read().image)!=changes[oid]['alpha_sha256']:
                raise ValueError('Alpha verification failed')
        results.append({'bundle':b['bundle'],'verified':True,'textures':len(changes)})
        print('Verified:',b['bundle'],flush=True)
        del modified,original,original_materials; gc.collect()
    dump(Path(config['paths']['reports'])/'verification-summary.json',{'bundles':results,'in_game_tested':False})
    return results


def restore(config,dry_run=False):
    """Restore staged copies only. Never writes to the installed game."""
    manifest=json.loads((Path(config['paths']['reports'])/'modifications.json').read_text())
    plan=[]
    for b in manifest['bundles']:
        dst=safe_output(b['output'],config); backup=Path(b['backup'])
        if digest(backup)!=b['source_sha256']: raise ValueError('Backup mismatch')
        if digest(dst) not in (b['source_sha256'],b['output_sha256']): raise ValueError('Unknown output version')
        plan.append(b['bundle'])
    if not dry_run:
        for b in manifest['bundles']:
            dst=Path(b['output']); tmp=dst.with_name(dst.name+'.restore')
            shutil.copyfile(b['backup'],tmp)
            if digest(tmp)!=b['source_sha256']: raise ValueError('Restore staging mismatch')
            tmp.replace(dst)
        dump(Path(config['paths']['reports'])/'restoration.json',{'restored':plan,'scope':'staged copies only'})
    return {'dry_run':dry_run,'restore_staged_bundles':plan}
