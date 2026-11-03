"""Stage a bounds-only correction for already installed MWC characters."""
import argparse,copy,gc,hashlib,json
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from bundle_utils import digest,inventory
from halftone.assets import key,dump
from .bounds import root_bounds
from .bundles import BUNDLE


def build(config,state,output,backups):
    from installer.mwc_installer.engine import copy_private,verify_current
    state,output,backups=map(Path,(state,output,backups));saved=json.loads((state/'state.json').read_text());verify_current(config,state,saved);source=Path(config['bundle_root'])/BUNDLE
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh bounds correction directory')
    backup=backups/BUNDLE
    if backup.exists():
        if digest(backup)!=saved['installed'][BUNDLE]:raise ValueError('Bounds backup belongs to another baseline')
    else:copy_private(source,backup)
    env=UnityPy.load(str(backup));before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in env.objects};native=UnityPy.load(str(state/'originals'/BUNDLE));original={o.path_id:o for o in native.objects};targets={t['id']:t for t in json.loads((Path(__file__).resolve().parents[1]/'config/operator-targets.json').read_text())['operators']};changes={}
    for identifier,model in saved.get('operator_assignments',{}).items():
        for row in targets[identifier]['renderers']:
            pid=int(row['path_id']);template=original[pid];oid=key(template.assets_file.name,pid);obj=objects[oid];tree=obj.read_typetree();prior=template.read_typetree()
            if any(tree[k]!=value for k,value in prior.items() if k not in ('m_Mesh','m_Materials','m_AABB')):raise ValueError('Installed renderer has unrelated changes')
            mesh=objects[key(obj.assets_file.name,tree['m_Mesh']['m_PathID'])]
            if mesh.read_typetree()['m_VertexData']['m_VertexCount']==0:continue
            if mesh.peek_name()!='MWC_OperatorMesh_'+identifier:raise ValueError('Expected an installed MWC character mesh')
            md=mesh.read_typetree();reference=original[prior['m_Mesh']['m_PathID']].read_typetree()
            if md['m_BindPose']!=reference['m_BindPose']:raise ValueError('Installed character skeleton differs from native')
            bind=np.asarray([[[p['e'+str(i)+str(j)] for j in range(4)] for i in range(4)] for p in md['m_BindPose']]);index=[p['m_PathID'] for p in tree['m_Bones']].index(tree['m_RootBone']['m_PathID']);h=MeshHandler(mesh.read());h.process();bounds=root_bounds(h.m_Vertices,bind,index,prior['m_AABB'])
            if tree['m_AABB']==bounds:continue
            changes[oid]={'operator':identifier,'model':model,'before':tree['m_AABB'],'after':bounds};tree['m_AABB']=bounds;obj.save_typetree(tree)
    if not changes:raise ValueError('No installed character bounds require correction')
    expected=copy.deepcopy(before)
    for oid in changes:
        obj=objects[oid];expected[(obj.assets_file.name,obj.path_id)]={'type':obj.type.name,'sha256':hashlib.sha256(obj.data).hexdigest()}
    target=output/BUNDLE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(target))
    if inventory(checked)!=expected:raise ValueError('Bounds correction changed unexpected serialized data')
    after={key(o.assets_file.name,o.path_id):o for o in checked.objects};old=UnityPy.load(str(backup))
    for obj in old.objects:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid in changes:
            tree=obj.read_typetree();tree['m_AABB']=changes[oid]['after']
            if tree!=after[oid].read_typetree():raise ValueError('Bounds correction exceeded field whitelist')
        elif obj.get_raw_data()!=after[oid].get_raw_data():raise ValueError('Bounds correction changed an unrelated asset')
    report={'files':[{'bundle':BUNDLE,'backup':str(backup.resolve()),'output':str(target.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target)}],'changes':changes,'verification':{'only_renderer_m_AABB_changed':True,'all_other_objects_byte_exact':True,'bounds_space':'root_bone','original_animation_envelope_retained':True},'in_game_tested':False};dump(output/'manifest.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--state',required=True);p.add_argument('--output',required=True);p.add_argument('--backups',required=True);a=p.parse_args();print(json.dumps(build(json.loads(Path(a.config).read_text()),a.state,a.output,a.backups),indent=2))
