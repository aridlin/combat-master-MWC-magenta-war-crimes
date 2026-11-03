"""Fit a reviewed source rig to a private native bind-pose snapshot."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from .profiles import profile
from .retarget import adapt


def fit(source,native,output,kind):
    source,native,output=map(Path,(source,native,output))
    if output.exists():raise ValueError('Use a fresh output for each fit review')
    meta=json.loads((source/'source.json').read_text());data=dict(np.load(source/'source.npz',allow_pickle=False));target=np.load(native.with_suffix('.npz'),allow_pickle=False);target_meta=json.loads(native.with_suffix('.json').read_text());options=profile(kind,meta)
    v,n,i,w,report=adapt(data['positions'],data['normals'],meta['bone_names'],data['inverse_bind'],data['bone_indices'],data['bone_weights'],target_meta['bone_names'],target['inverse_bind'],**options)
    data.update(positions=v,normals=n,bone_indices=i,bone_weights=w,inverse_bind=target['inverse_bind'])
    if np.linalg.det(options['source_basis'])<0:data['faces']=data['faces'][:,[0,2,1]]
    output.mkdir(parents=True)
    for mat in meta['materials']:
        if 'pixels' not in mat:continue
        name=mat['pixels']
        if Path(name).name!=name:raise ValueError('Material pixel path must be local to source')
        shutil.copyfile(source/name,output/name)
    np.savez_compressed(output/'source.npz',**data)
    meta.update(bone_names=target_meta['bone_names'],coordinate_system='z_up',fit_profile=kind,fitting=report,source_geometry_sha256=hashlib.sha256((source/'source.npz').read_bytes()).hexdigest(),target_bind_sha256=hashlib.sha256(target['inverse_bind'].tobytes()).hexdigest(),in_game_tested=False)
    (output/'source.json').write_text(json.dumps(meta,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('native');p.add_argument('output');p.add_argument('--profile',required=True);a=p.parse_args();print(json.dumps(fit(a.source,a.native,a.output,a.profile),indent=2))
