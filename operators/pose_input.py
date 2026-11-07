"""Match a private world-clip export to its exact serialized model rig.

This reads data only. It never samples live state, modifies clips, or invokes
events, game scripts, controllers or IK. Incompatible inputs fail explicitly.
"""
from pathlib import Path
import json
import numpy as np
from bundle_utils import digest


def main_world_renderer(record,targets):
    """Select the reviewed LOD0 body, not the first path-ID-sorted renderer."""
    targets=[target for target in targets if target.get('id')==record['operator']]
    if len(targets)!=1:raise ValueError('World operator target is absent or ambiguous')
    owned={str(row['renderer']) for row in record['renderers']}
    matches=[str(row['path_id']) for row in targets[0]['renderers'] if str(row['path_id']) in owned and row['name'].endswith('LOD0')]
    if len(matches)!=1:raise ValueError('World LOD0 renderer is absent or ambiguous')
    return int(matches[0])


def read_world_pose(directory,source_hash,operator,renderer,bone_names,inverse_bind):
    directory=Path(directory);report=json.loads((directory/'review.json').read_text())
    if report.get('rig_kind')!='third_person' or report.get('operator')!=operator:
        raise ValueError('Clip pose belongs to another operator or rig kind')
    if report.get('source_bundle_sha256')!=source_hash or not report.get('source_unchanged') or not report.get('clip_source_unchanged'):
        raise ValueError('Clip pose and staged model must use the same verified original bundle')
    if digest(directory/'pose.npz')!=report.get('pose_data_sha256'):
        raise ValueError('Clip pose data changed or lacks a recorded hash; export it again')
    rows=[r for r in report.get('renderers',[]) if r.get('renderer')==str(renderer)]
    if len(rows)!=1:raise ValueError('Clip pose renderer is absent or ambiguous')
    row=rows[0];count=len(bone_names)
    if row.get('bone_names')!=list(bone_names) or row.get('bones')!=count:
        raise ValueError('Clip pose bone names or ordering do not match the serialized model')
    if row.get('pose_space')!='renderer_local' or row.get('world_space')!='Unity Y-up' or 'renderer_to_world_array' not in row:
        raise ValueError('Clip pose lacks evaluated world coordinates; export it again')
    with np.load(directory/'pose.npz',allow_pickle=False) as data:
        pose=data[row['pose_array']].copy();bind=data[row['inverse_bind_array']].copy();world=data[row['renderer_to_world_array']].copy()
    if bind.shape!=(count,4,4) or not np.array_equal(bind,inverse_bind):
        raise ValueError('Clip pose inverse bind matrices do not match the serialized model')
    if pose.shape!=(count,4,4) or not np.isfinite(pose).all() or not np.allclose(pose[:,3],[0,0,0,1],atol=1e-7,rtol=0) or np.any(abs(np.linalg.det(pose[:,:3,:3]))<1e-12):
        raise ValueError('Invalid or singular clip pose bone matrices')
    from .pose_space import preview_transform
    preview_transform(world) # Validate the frame before any review output.
    return pose,world,{k:report[k] for k in ('operator','clip','frame','time','source_bundle_sha256','pose_data_sha256')}
