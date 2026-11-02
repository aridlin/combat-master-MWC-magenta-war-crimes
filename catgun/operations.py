"""Independent cat prototype verification and reversible two-file deployment."""
import gc
import hashlib
import json
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from halftone.pipeline import build_id
from deploy_halftone import close_game,replace_verified
from .geometry import make_cat,palette_image
from .bundle import verify_geometry


def verify(config,cat_config):
    manifest=json.loads((Path(cat_config['output'])/'manifest.json').read_text());build_id(config)
    mesh=make_cat(cat_config['scale']);counts=[]
    for b in manifest['files']:
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:
            raise ValueError('Cat artifact or baseline hash mismatch')
        before_env=UnityPy.load(b['backup']);after_env=UnityPy.load(b['output'])
        before=inventory(before_env);after=inventory(after_env)
        original={key(o.assets_file.name,o.path_id):o for o in before_env.objects}
        modified={key(o.assets_file.name,o.path_id):o for o in after_env.objects}
        added=set(b['added_objects']);allowed=b['existing_object_changes']
        if set(modified)!=set(original)|added:raise ValueError('Unexpected new/missing object IDs')
        for oid,obj in original.items():
            k=(obj.assets_file.name,obj.path_id)
            if oid not in allowed:
                if before[k]!=after[k]:raise ValueError('Nonvisual original data changed: '+oid)
            else:
                a=obj.read_typetree();z=modified[oid].read_typetree();change=allowed[oid]
                if change['kind']=='visual_mesh_binding':
                    a['m_Mesh']=change['new']
                    if change.get('disabled'):a['m_Enabled']=False
                elif change['kind']=='visual_renderer_disabled':a['m_Enabled']=False
                elif change['kind']=='cat_child_link':a['m_Children'].append({'m_FileID':0,'m_PathID':change['child']})
                else:raise ValueError('Unknown permitted edit')
                if a!=z:raise ValueError('Changed fields outside visual binding/child list')
        def local_refs(tree):
            if isinstance(tree,dict):
                if set(tree)>={'m_FileID','m_PathID'} and tree['m_FileID']==0 and tree['m_PathID']:
                    yield tree['m_PathID']
                else:
                    for value in tree.values():yield from local_refs(value)
            elif isinstance(tree,(tuple,list)):
                for value in tree:yield from local_refs(value)
        cat_found=False
        for oid in added:
            obj=modified[oid];tree=obj.read_typetree()
            for pid in local_refs(tree):
                if key(obj.assets_file.name,pid) not in modified:raise ValueError('Dangling new local asset reference')
            if obj.type.name=='Mesh' and tree['m_Name']=='MWC_CatMesh':verify_geometry(obj,mesh);cat_found=True
            elif obj.type.name=='Mesh' and tree['m_VertexData']['m_VertexCount']!=0:raise ValueError('Visual masking mesh is not empty')
            if obj.type.name=='Texture2D' and tree['m_Name']=='MWC_CatPalette':
                import numpy as np
                if not np.array_equal(np.asarray(obj.read().image.convert('RGB')),np.asarray(palette_image())):
                    raise ValueError('Cat palette did not round-trip')
        counts.append({'bundle':b['bundle'],'hidden_render_bindings':len(b['hidden_render_bindings']),
                       'new_objects':len(added),'cat_geometry_verified':cat_found if b['bundle'].endswith('/weapons') else 'not-applicable',
                       'original_gameplay_audio_collision_animation_data_unchanged':True,
                       'new_local_asset_references_resolve':True})
        del original,modified,before_env,after_env;gc.collect()
    result={'bundles':counts,'in_game_tested':False,'geometry':manifest['geometry']}
    dump(Path(cat_config['output'])/'verification.json',result)
    return result


def deploy(config,cat_config,action,dry_run=False):
    build_id(config);manifest=json.loads((Path(cat_config['output'])/'manifest.json').read_text())
    plan=[];base=Path(config['bundle_root']).resolve()
    for b in manifest['files']:
        target=(base/b['bundle']).resolve()
        if base not in target.parents:raise ValueError('Unsafe installed path')
        if digest(Path(b['backup']))!=b['source_sha256'] or digest(Path(b['output']))!=b['output_sha256']:
            raise ValueError('Artifact/backup mismatch')
        current=digest(target)
        if current not in (b['source_sha256'],b['output_sha256']):raise ValueError('Installed bundle changed; do not overwrite another build/mod')
        source=Path(b['output'] if action=='install' else b['backup'])
        wanted=b['output_sha256'] if action=='install' else b['source_sha256']
        plan.append((b,target,source,current,wanted))
    if dry_run:return {'action':action,'dry_run':True,'bundles':[b['bundle'] for b,*_ in plan]}
    if action=='install':verify(config,cat_config)
    close_game(config);completed=[]
    try:
        for b,target,source,current,wanted in plan:
            if current!=wanted:replace_verified(source,target,current,wanted)
            completed.append((b,target,current,wanted))
    except Exception:
        for b,target,current,wanted in reversed(completed):
            if current!=wanted:
                rollback=Path(b['backup'] if action=='install' else b['output'])
                replace_verified(rollback,target,wanted,current)
        raise
    result={'action':action,'files':[{'bundle':b['bundle'],'sha256':digest(target)} for b,target,*_ in plan],
            'game_launched':False,'in_game_tested':False}
    dump(Path(cat_config['output'])/'deployment.json',result);return result
