"""Narrow diffuse-only material cleanup for already verified staged bundles."""
import gc
import hashlib
import json
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from .assets import key,dump,load_scan
from .classify import classify

TINTS={'_BaseColor','_Color','AlbedoColor'}
ALBEDO_BINDINGS={'_BaseMap','_MainTex','_Albedo','_AlbedoMap','_Diffuse','_DiffuseMap','_BaseColorMap','Albedo','Base_Map','_Tex'}


def check_material_diff(original,modified,bindings=None):
    """Accept only diffuse RGB neutralization and the exposed camo switch."""
    before=original.read_typetree(); after=modified.read_typetree()
    saved=before['m_SavedProperties']
    for i,(name,value) in enumerate(saved['m_Floats']):
        if name=='EnableCamo': saved['m_Floats'][i]=(name,0.0)
    for name,value in saved['m_Colors']:
        if name in TINTS:
            for c in ('r','g','b'): value[c]=1.0
    for binding in bindings or []:
        if binding['slot'] not in ALBEDO_BINDINGS: raise ValueError('Non-color reference must not be rebound')
        for name,value in saved['m_TexEnvs']:
            if name==binding['slot']:
                p=value['m_Texture']
                if p['m_PathID']!=binding['old_path_id'] or p['m_FileID']!=binding['file_id']:
                    raise ValueError('Unexpected original material binding')
                p['m_PathID']=binding['new_path_id']
    if before!=after:
        raise ValueError('Material changed outside the allowed diffuse fields')


def finalize(config,dry_run=False):
    report_dir=Path(config['paths']['reports'])
    classification=classify(config)
    selected={r['id'] for r in classification['assets'] if r['action']=='replace'}
    scans=load_scan(config['paths']['reports'])
    targets={}
    for b in scans:
        for m in b['materials']:
            albedo=[p['texture'] for p in m['properties'] if p['slot'] in config['color_slots']]
            if albedo and all(t in selected for t in albedo): targets[m['id']]=b['bundle']
    manifest=json.loads((report_dir/'modifications.json').read_text())
    plan={b['bundle']:sum(relative==b['bundle'] for relative in targets.values()) for b in manifest['bundles']}
    if dry_run: return {'dry_run':True,'materials_by_bundle':plan}
    adjusted=0
    for b in manifest['bundles']:
        if b.get('diffuse_material_cleanup_complete'): continue
        path=Path(b['output'])
        if digest(path)!=b['output_sha256']: raise ValueError('Staged hash mismatch')
        env=UnityPy.load(str(path)); expected=inventory(env); changes=[]
        for obj in env.objects:
            oid=key(obj.assets_file.name,obj.path_id)
            if obj.type.name!='Material' or oid not in targets: continue
            m=obj.read(); edits=[]
            for i,(name,value) in enumerate(m.m_SavedProperties.m_Floats):
                if name=='EnableCamo' and value!=0:
                    edits.append({'field':name,'before':value,'after':0})
                    m.m_SavedProperties.m_Floats[i]=(name,0.0)
            for name,color in m.m_SavedProperties.m_Colors:
                if name in TINTS and (color.r,color.g,color.b)!=(1,1,1):
                    edits.append({'field':name,'before':[color.r,color.g,color.b],'after':[1,1,1],'alpha_retained':color.a})
                    color.r=color.g=color.b=1.0
            if edits:
                m.save(); expected[(obj.assets_file.name,obj.path_id)]['sha256']=hashlib.sha256(obj.data).hexdigest()
                changes.append({'id':oid,'name':m.m_Name,'edits':edits})
        if changes:
            temporary=path.with_name(path.name+'.materials-partial')
            with temporary.open('wb') as stream: stream.write(env.file.save(packer='lz4'))
            del m,obj,env; gc.collect()
            checked=UnityPy.load(str(temporary))
            if inventory(checked)!=expected: raise ValueError('Material output serialization mismatch')
            original=UnityPy.load(b['backup'])
            originals={key(o.assets_file.name,o.path_id):o for o in original.objects}
            after={key(o.assets_file.name,o.path_id):o for o in checked.objects}
            for change in changes: check_material_diff(originals[change['id']],after[change['id']])
            del original,originals,checked,after; gc.collect()
            temporary.replace(path)
        else:
            del env; gc.collect()
        retained={c['id']:c for c in b.get('material_changes',[])}
        retained.update({c['id']:c for c in changes})
        b['material_changes']=list(retained.values())
        b['diffuse_material_cleanup_complete']=True
        b['output_sha256']=digest(path)
        b['settings_sha256']=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
        b['checks'].pop('materials_shaders_geometry_animations_unchanged',None)
        b['checks']['geometry_animations_shaders_unchanged']=True
        b['checks']['only_whitelisted_diffuse_material_fields_changed']=True
        b['checks']['all_unselected_objects_unchanged']=True
        adjusted+=len(changes)
        dump(str(path)+'.verification.json',b)
        dump(report_dir/'modifications.json',manifest)
        print(f'Diffuse cleanup verified: {b["bundle"]} ({len(changes)} materials)',flush=True)
    return {'material_changes':sum(len(b.get('material_changes',[])) for b in manifest['bundles']),
            'new_material_changes':adjusted}
