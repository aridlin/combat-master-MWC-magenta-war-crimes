"""Stage position-only corrections to already installed MWC visual children."""
import argparse,copy,hashlib,json
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from .placements import parent_position
from .bundles import SPECS

BUNDLE='src/weapons/weapons'


def build(config,state,output,backups,names=('fishing_rod','nail_gun','toaster')):
    from installer.mwc_installer.engine import verify_current,copy_private
    state,output,backups=map(Path,(state,output,backups));saved=json.loads((state/'state.json').read_text());verify_current(config,state,saved)
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh placement correction directory')
    if any(n not in saved['selected'] for n in names):raise ValueError('Only repair models already installed by the manager')
    source=Path(config['bundle_root'])/BUNDLE;backup=backups/BUNDLE
    if backup.exists():
        if digest(backup)!=saved['installed'][BUNDLE]:raise ValueError('Placement backup belongs to another baseline')
    else:copy_private(source,backup)
    env=UnityPy.load(str(backup));before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in env.objects};gos={o.path_id:o.peek_name() for o in env.objects if o.type.name=='GameObject'};transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'};changes={};counts={n:0 for n in names}
    for obj in env.objects:
        if obj.type.name!='Transform':continue
        tree=obj.read_typetree();name=gos[tree['m_GameObject']['m_PathID']].removeprefix('MWC_Model_')
        if name not in names or gos[tree['m_GameObject']['m_PathID']]!='MWC_Model_'+name:continue
        parent=transforms[tree['m_Father']['m_PathID']];parent_name=gos[parent['m_GameObject']['m_PathID']]
        if parent_name not in SPECS[name]['roots']:raise ValueError('Installed model is attached to an unexpected root')
        counts[name]+=1;position=parent_position({},name)
        if tree['m_LocalPosition']==position:continue
        changes[key(obj.assets_file.name,obj.path_id)]={'model':name,'before':tree['m_LocalPosition'],'after':position};tree['m_LocalPosition']=position;obj.save_typetree(tree)
    if any(counts[n]!=SPECS[n]['root_count'] for n in names):raise ValueError('Unexpected number of installed visual children')
    if not changes:raise ValueError('Installed visual positions already match the configured correction')
    expected=copy.deepcopy(before)
    for oid in changes:
        obj=objects[oid];expected[(obj.assets_file.name,obj.path_id)]={'type':obj.type.name,'sha256':hashlib.sha256(obj.data).hexdigest()}
    target=output/BUNDLE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='lz4'));checked=UnityPy.load(str(target))
    if inventory(checked)!=expected:raise ValueError('Placement correction serialization mismatch')
    after={key(o.assets_file.name,o.path_id):o for o in checked.objects};baseline=UnityPy.load(str(backup))
    for obj in baseline.objects:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid in changes:
            tree=obj.read_typetree();tree['m_LocalPosition']=changes[oid]['after']
            if tree!=after[oid].read_typetree():raise ValueError('Placement correction exceeded position field whitelist')
        elif obj.get_raw_data()!=after[oid].get_raw_data():raise ValueError('Placement correction changed an unrelated object')
    report={'files':[{'bundle':BUNDLE,'backup':str(backup.resolve()),'output':str(target.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target)}],'changes':changes,'verification':{'only_MWC_visual_child_positions_changed':True,'all_other_objects_byte_exact':True,'original_sights_animations_colliders_gameplay_retained':True},'in_game_tested':False};dump(output/'manifest.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--state',required=True);p.add_argument('--output',required=True);p.add_argument('--backups',required=True);a=p.parse_args();print(json.dumps(build(json.loads(Path(a.config).read_text()),a.state,a.output,a.backups),indent=2))
