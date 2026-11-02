"""Clone shared albedos per semantic category without changing data-map uses."""
import copy
import gc
import hashlib
import json
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from .assets import key,dump
from .classify import classify
from .encoding import apply_pattern,alpha_hash
from .materials import TINTS,check_material_diff


def separate_shared(config):
    report_dir=Path(config['paths']['reports']); mp=report_dir/'modifications.json'
    classification=classify(config); manifest=json.loads(mp.read_text())
    by_bundle={b['bundle']:b for b in manifest['bundles']}
    targets=[r for r in classification['assets'] if r['reasons'] in (['mixed_category_conflict'],['also_used_as_noncolor_or_unknown_slot'])
             and all(len(ref['categories'])==1 for ref in r['references'] if ref['is_color'])]
    bindings={}; clone_map={}
    def commit(b,env,expected,check=None):
        path=Path(b['output']); tmp=path.with_name(path.name+'.shared-partial')
        with tmp.open('wb') as stream: stream.write(env.file.save(packer='lz4'))
        checked=UnityPy.load(str(tmp))
        if inventory(checked)!=expected: raise ValueError('Shared-albedo serialization mismatch')
        if check: check(checked)
        tmp.replace(path); b['output_sha256']=digest(path)
        dump(str(path)+'.verification.json',b); dump(mp,manifest)
        del checked; gc.collect()
    for relative,b in by_bundle.items():
        rows=[r for r in targets if r['bundle']==relative]
        if not rows: continue
        if digest(Path(b['output']))!=b['output_sha256']: raise ValueError('Staged hash changed')
        env=UnityPy.load(b['output']); objects={key(o.assets_file.name,o.path_id):o for o in env.objects}
        expected=inventory(env); records=b.setdefault('cloned_textures',[]); pending=False
        for r in rows:
            original=objects[r['id']]
            for category in r['candidates']:
                existing=next((c for c in records if c['source_id']==r['id'] and c['category']==category),None)
                if existing:
                    clone_map[(r['id'],category)]=existing
                    continue
                clone=copy.copy(original)
                identifier=int.from_bytes(hashlib.sha256((r['id']+category).encode()).digest()[:7],'little')+1
                while identifier in original.assets_file.objects: identifier+=1
                clone.path_id=identifier; clone.data=None
                original.assets_file.objects[identifier]=clone
                t=clone.read(); t.m_Name=t.m_Name+'__halftone_'+category
                details=apply_pattern(t,config['categories'][category]['color'],config['generation'])
                new_id=key(clone.assets_file.name,identifier)
                record={'id':new_id,'source_id':r['id'],'category':category,**details}
                expected[(clone.assets_file.name,identifier)]={'type':'Texture2D','sha256':hashlib.sha256(clone.data).hexdigest()}
                records.append(record); clone_map[(r['id'],category)]=record; pending=True
        if pending:
            def verify_clones(checked):
                objects={key(o.assets_file.name,o.path_id):o for o in checked.objects}
                for c in records:
                    if alpha_hash(objects[c['id']].read().image)!=c['alpha_sha256']: raise ValueError('Clone alpha changed')
            commit(b,env,expected,verify_clones)
            b['checks'].pop('same_object_ids_and_types',None)
            b['checks']['original_ids_preserved_only_declared_texture_copies_added']=True
            dump(str(b['output'])+'.verification.json',b); dump(mp,manifest)
            print('Category-specific albedo copies verified:',relative,len(records),flush=True)
        del env,objects; gc.collect()
    for r in targets:
        for ref in r['references']:
            if not ref['is_color']: continue
            clone=clone_map[(r['id'],ref['categories'][0])]
            bindings.setdefault(ref['material_bundle'],{}).setdefault(ref['material_id'],[]).append({
                'slot':ref['slot'],'old_path_id':int(r['id'].rsplit(':',1)[1]),
                'new_path_id':int(clone['id'].rsplit(':',1)[1]),'source_id':r['id'],'category':ref['categories'][0]})
    for relative,materials in bindings.items():
        b=by_bundle[relative]
        if digest(Path(b['output']))!=b['output_sha256']: raise ValueError('Staged hash changed')
        env=UnityPy.load(b['output']); expected=inventory(env)
        records=b.setdefault('material_binding_changes',[]); existing={c['id'] for c in records}; changed=False
        for obj in env.objects:
            oid=key(obj.assets_file.name,obj.path_id)
            if oid not in materials or oid in existing: continue
            m=obj.read(); actual=[]
            for slot,value in m.m_SavedProperties.m_TexEnvs:
                for binding in materials[oid]:
                    if slot==binding['slot'] and value.m_Texture.m_PathID==binding['old_path_id']:
                        record={**binding,'file_id':value.m_Texture.m_FileID}
                        value.m_Texture.m_PathID=binding['new_path_id']; actual.append(record)
            if not actual: raise ValueError('Material albedo bindings not found')
            for i,(n,v) in enumerate(m.m_SavedProperties.m_Floats):
                if n=='EnableCamo': m.m_SavedProperties.m_Floats[i]=(n,0.0)
            for n,c in m.m_SavedProperties.m_Colors:
                if n in TINTS: c.r=c.g=c.b=1.0
            m.save(); expected[(obj.assets_file.name,obj.path_id)]['sha256']=hashlib.sha256(obj.data).hexdigest()
            records.append({'id':oid,'bindings':actual}); changed=True
        if changed:
            def check_bindings(checked):
                original=UnityPy.load(b['backup'])
                before={key(o.assets_file.name,o.path_id):o for o in original.objects}
                after={key(o.assets_file.name,o.path_id):o for o in checked.objects}
                for change in records: check_material_diff(before[change['id']],after[change['id']],change['bindings'])
            commit(b,env,expected,check_bindings)
            print('Shared-material category bindings verified:',relative,len(records),flush=True)
        del env; gc.collect()
    return {'shared_source_albedos':len(targets),'category_copies':len(clone_map)}
