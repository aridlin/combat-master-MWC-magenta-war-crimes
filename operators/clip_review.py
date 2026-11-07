"""Read-only sampling of reviewed generic Unity clips at dense sample frames.

Offline diagnostics only. No Animator, IK, root-motion or event execution, and
no game/profile writes. Reject unsupported binding formats rather than invent
poses. Format references and limitations: docs/native-clip-review.md.
"""
import struct,zlib
import numpy as np


def euler_xyz(degrees):
    """Reviewed custom-type-0 Euler curves use XYZ, not Quaternion.Euler's ZXY.

    Verified against the original clips and Avatar through Unity's native
    AnimationClipPlayable evaluator; this is not a universal clip convention.
    """
    x,y,z=np.deg2rad(np.asarray(degrees,dtype=float))
    cx,cy,cz=np.cos([x,y,z]);sx,sy,sz=np.sin([x,y,z])
    rx=np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    rz=np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return rz@ry@rx


def quaternion_matrix(value):
    q=np.asarray(value,dtype=float)
    if q.shape!=(4,) or not np.isfinite(q).all() or np.linalg.norm(q)<1e-8:raise ValueError('Invalid clip quaternion')
    x,y,z,w=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def euler_zyx(degrees):
    """ZYX composition for the separately reviewed custom-type-5 Euler layout."""
    return euler_xyz(-np.asarray(degrees,dtype=float)).T


def streamed_values(stream,time):
    count=int(stream['curveCount'])
    if count<0 or stream.get('discreteCurveCount',0):raise ValueError('Unreviewed discrete clip curves')
    data=np.asarray(stream['data'],dtype='<u4').tobytes();offset=0;previous=-np.inf;latest={}
    while offset<len(data):
        if len(data)-offset<8:raise ValueError('Truncated streamed frame')
        moment,n=struct.unpack_from('<fi',data,offset);offset+=8
        if np.isnan(moment) or moment<previous or n<0 or n>(len(data)-offset)//20:raise ValueError('Invalid streamed frame header')
        previous=moment;seen=set()
        for _ in range(n):
            index,*coeff=struct.unpack_from('<i4f',data,offset);offset+=20
            if not 0<=index<count or index in seen or not np.isfinite(coeff).all():raise ValueError('Invalid streamed channel')
            seen.add(index)
            if moment<=time:latest[index]=(moment,coeff)
        if np.isinf(moment) and n:raise ValueError('Stream sentinel contains keys')
    if len(latest)!=count:raise ValueError('Streamed channels lack an initial sample')
    values=np.empty(count)
    for index,(moment,(a,b,c,d)) in latest.items():
        if moment<-1e20:
            if a or b or c:raise ValueError('Nonconstant initialization sentinel')
            values[index]=d
        else:
            dt=time-moment;values[index]=((a*dt+b)*dt+c)*dt+d
    return values


def sample_channels(tree,time):
    if not np.isfinite(time) or tree.get('m_Legacy') or tree.get('m_Compressed') or tree.get('m_CompressedRotationCurves'):
        raise ValueError('Expected a finite time and reviewed generic clip format')
    if any(tree.get(k) for k in ('m_RotationCurves','m_PositionCurves','m_EulerCurves','m_ScaleCurves','m_FloatCurves','m_PPtrCurves')):
        raise ValueError('Legacy/explicit clip curves require a separate sampler')
    muscle=tree['m_MuscleClip']
    if not muscle['m_StartTime']-1e-6<=time<=muscle['m_StopTime']+1e-6:raise ValueError('Sample time outside clip')
    clip=muscle['m_Clip']['data'];dense=clip['m_DenseClip'];curves=int(dense['m_CurveCount']);frames=int(dense['m_FrameCount'])
    samples=np.asarray(dense['m_SampleArray'],dtype=float)
    if min(curves,frames)<0 or samples.size!=curves*frames:raise ValueError('Dense clip dimensions disagree')
    if curves:
        rate=float(dense['m_SampleRate'])
        if not np.isfinite(rate) or rate<=0:raise ValueError('Invalid dense sample rate')
        position=(time-dense['m_BeginTime'])*rate;frame=round(position)
        if abs(frame-position)>1e-4 or not 0<=frame<frames:raise ValueError('Choose an exact dense sample frame; interpolation is not implemented')
        dense_values=samples.reshape(frames,curves)[frame]
    else:dense_values=np.empty(0)
    values=np.r_[streamed_values(clip['m_StreamedClip'],time),dense_values,clip['m_ConstantClip']['data']]
    if not np.isfinite(values).all():raise ValueError('Nonfinite clip sample')
    output=[];cursor=0;ignored=[];euler_orders={}
    for binding in tree['m_ClipBindingConstant']['genericBindings']:
        if any(binding.get(k,0) for k in ('isPPtrCurve','isIntCurve','isSerializeReferenceCurve')):raise ValueError('Unsupported discrete/object clip binding')
        kind=binding.get('typeID',binding.get('classID'));attribute=binding['attribute']
        custom=binding.get('customType',0)
        if kind==4 and attribute in (1,2,3,4) and (custom==0 or custom==5 and attribute==4):
            width=4 if attribute==2 else 3
            if attribute==4:euler_orders[str(custom)]=euler_orders.get(str(custom),0)+1
        elif kind==95 and binding['path']==0 and binding.get('customType')==8 and 7<=attribute<=13:
            width=1;ignored.append({'type':'Animator root channel','attribute':attribute})
        else:raise ValueError('Unsupported clip binding type or transform attribute')
        value=values[cursor:cursor+width];cursor+=width
        if len(value)!=width:raise ValueError('Binding exceeds packed clip channels')
        if kind==4:output.append((int(binding['path']),attribute,value.copy()))
    if cursor!=len(values):raise ValueError('Packed clip channels exceed declared bindings')
    order='mixed XYZ/ZYX' if len(euler_orders)>1 else 'ZYX' if '5' in euler_orders else 'XYZ'
    return output,{'clip':tree['m_Name'],'time':float(time),'transform_bindings':len(output),'packed_euler_order':order,'euler_binding_custom_types':euler_orders,'ignored_root_channels':ignored,'runtime_IK_blending_events_and_root_motion_not_evaluated':True,'in_game_tested':False}


def hierarchy(transforms,names,root):
    owned=[];active=set();done=set()
    def walk(node):
        if node in active or node in done:raise ValueError('Cyclic or multiply owned native hierarchy')
        active.add(node);owned.append(node)
        for pointer in transforms[node]['m_Children']:
            child=pointer['m_PathID']
            if pointer['m_FileID'] or child not in transforms:raise ValueError('External or absent native child')
            if transforms[child]['m_Father']['m_PathID']!=node:raise ValueError('Native child/parent links disagree')
            walk(child)
        active.remove(node);done.add(node)
    walk(root);paths={};hashes={}
    for node in owned:
        parent=transforms[node]['m_Father']['m_PathID'];name=names[transforms[node]['m_GameObject']['m_PathID']]
        path=(paths[parent]+'/'+name) if parent in paths else name;paths[node]=path;parts=path.split('/')
        for n in range(len(parts)):hashes.setdefault(zlib.crc32('/'.join(parts[n:]).encode('utf8')),set()).add(node)
    return owned,hashes


def sample_world(tree,time,transforms,names,root):
    channels,report=sample_channels(tree,time);owned,hashes=hierarchy(transforms,names,root);overrides={};node_euler_orders={}
    rotation_orders={int(b['path']):b.get('customType',0) for b in tree['m_ClipBindingConstant']['genericBindings'] if b.get('typeID',b.get('classID'))==4 and b['attribute']==4}
    for path,attribute,value in channels:
        candidates=hashes.get(path,set())
        if len(candidates)!=1:raise ValueError('Clip path hash is absent or ambiguous: '+str(path))
        node=next(iter(candidates));attrs=overrides.setdefault(node,{})
        if attribute in attrs or attribute in (2,4) and any(a in attrs for a in (2,4)):raise ValueError('Duplicate or mixed clip rotation binding')
        attrs[attribute]=value
        if attribute==4:node_euler_orders[node]=rotation_orders[path]
    world={}
    for node in owned:
        native=transforms[node];attrs=overrides.get(node,{})
        position=attrs.get(1,[native['m_LocalPosition'][k] for k in 'xyz'])
        scale=attrs.get(3,[native['m_LocalScale'][k] for k in 'xyz'])
        if 4 in attrs:
            order=node_euler_orders[node]
            rotation=(euler_zyx if order==5 else euler_xyz)(attrs[4])
        else:rotation=quaternion_matrix(attrs.get(2,[native['m_LocalRotation'][k] for k in 'xyzw']))
        local=np.eye(4);local[:3,:3]=rotation@np.diag(scale);local[:3,3]=position
        if not np.isfinite(local).all():raise ValueError('Nonfinite clip transform')
        parent=native['m_Father']['m_PathID'];world[node]=world[parent]@local if parent in world else local
    report.update(resolved_transform_bindings=len(channels),hierarchy_nodes=len(owned),unused_ambiguous_path_aliases=sum(len(v)>1 for v in hashes.values()))
    return world,report


def export_clip(bundle,operator,clip_name,frame,output,*,clip_bundle=None,rig_kind='first_person'):
    """Export a private pose; the original clip may live outside the rig bundle."""
    from pathlib import Path
    import json,UnityPy
    from bundle_utils import digest
    from halftone.pipeline import safe_output
    from .native import native_rig
    project=Path(__file__).resolve().parents[1];bundle=Path(bundle).resolve();requested=Path(output).resolve()
    if rig_kind not in ('first_person','third_person'):raise ValueError('Choose first_person or third_person rig')
    if requested==project or project in requested.parents:raise ValueError('Native pose exports must be outside the public source/package directory')
    clip_source=bundle if clip_bundle is None else Path(clip_bundle).resolve()
    output=safe_output(output,{'bundle_root':str(bundle.parent)})
    safe_output(output,{'bundle_root':str(clip_source.parent)})
    if output.exists():raise ValueError('Choose a fresh private pose output directory')
    if type(frame) is not int or frame<0:raise ValueError('Choose a nonnegative integer clip frame')
    target_file='operator-first-person-targets.json' if rig_kind=='first_person' else 'operator-targets.json'
    targets=json.loads((project/'config'/target_file).read_text())['operators']
    matches=[t for t in targets if t['id']==operator]
    if len(matches)!=1:raise ValueError('Unknown '+rig_kind+' operator identity')
    before=digest(bundle);clip_before=before if clip_source==bundle else digest(clip_source)
    env=UnityPy.load(str(bundle));rig=native_rig(env,matches[0],first_person=rig_kind=='first_person')
    clip_env=env if clip_source==bundle else UnityPy.load(str(clip_source))
    clips=[o for o in clip_env.objects if o.type.name=='AnimationClip' and o.peek_name()==clip_name]
    if len(clips)!=1:raise ValueError('Native clip is absent or ambiguous')
    tree=clips[0].read_typetree();dense=tree['m_MuscleClip']['m_Clip']['data']['m_DenseClip'];rate=float(dense['m_SampleRate'])
    if not np.isfinite(rate) or rate<=0:raise ValueError('Clip does not expose a reviewed dense frame rate')
    time=float(dense['m_BeginTime'])+frame/rate
    transforms={o.path_id:o.read_typetree() for o in env.objects if o.type.name=='Transform'}
    names={o.path_id:o.peek_name() for o in env.objects if o.type.name=='GameObject'}
    by_go={t['m_GameObject']['m_PathID']:i for i,t in transforms.items()}
    root=by_go[int(matches[0]['prefab_path_id'])];world,report=sample_world(tree,time,transforms,names,root);arrays={};renderers=[]
    for rid in sorted(rig['snapshots']):
        native=rig['snapshots'][rid];renderer=native['renderer'];mesh=by_go[renderer['m_GameObject']['m_PathID']];model_inv=np.linalg.inv(world[mesh]);ids=[p['m_PathID'] for p in renderer['m_Bones']]
        pose=np.stack([model_inv@world[i] for i in ids]);prefix='renderer_'+str(rid).replace('-','minus_')
        arrays[prefix+'_pose']=pose;arrays[prefix+'_inverse_bind']=native['inverse_bind']
        renderers.append({'renderer':str(rid),'bones':len(ids),'bone_names':native['bone_names'],'pose_array':prefix+'_pose','inverse_bind_array':prefix+'_inverse_bind'})
        if rig_kind=='third_person':
            # Posed renderer coordinates need not share the bind mesh's up
            # axis. Preserve the evaluated frame for private studio review.
            arrays[prefix+'_renderer_to_world']=world[mesh]
            renderers[-1].update(pose_space='renderer_local',world_space='Unity Y-up',renderer_to_world_array=prefix+'_renderer_to_world')
    if digest(bundle)!=before:raise ValueError('Native source bundle changed during inspection')
    if clip_source!=bundle and digest(clip_source)!=clip_before:raise ValueError('Native clip source bundle changed during inspection')
    report.update(operator=operator,rig_kind=rig_kind,frame=frame,sample_rate=rate,source_bundle_sha256=before,
                  clip_source_bundle_sha256=clip_before,clip_source_is_rig_bundle=clip_source==bundle,
                  clip_id=str(clips[0].path_id),renderers=renderers,source_unchanged=True,
                  clip_source_unchanged=True,private_native_game_data=True,
                  game_or_profile_modified=False,events_not_invoked=len(tree.get('m_Events',[])))
    output.mkdir(parents=True);np.savez_compressed(output/'pose.npz',**arrays)
    report['pose_data_sha256']=digest(output/'pose.npz')
    (output/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    import argparse,json
    p=argparse.ArgumentParser(description='Read-only native generic-clip pose review; exported native data remains private')
    p.add_argument('--bundle',required=True,help='Verified original bundle for the chosen rig')
    p.add_argument('--rig',choices=('first_person','third_person'),default='first_person',help='First-person arms or world operator; defaults to first_person')
    p.add_argument('--clip-bundle',help='Original bundle containing the clip; defaults to --bundle')
    p.add_argument('--operator',default='operator_0');p.add_argument('--clip',required=True);p.add_argument('--frame',type=int,default=0);p.add_argument('--output',required=True)
    a=p.parse_args();report=export_clip(a.bundle,a.operator,a.clip,a.frame,a.output,clip_bundle=a.clip_bundle,rig_kind=a.rig)
    print(json.dumps({k:v for k,v in report.items() if k!='renderers'},indent=2))


if __name__=='__main__':main()
