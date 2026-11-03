"""Locally transfer a native skin onto the existing authored Stim pilot.

The native mesh is a private weight reference only. Its geometry is neither
embedded in the result nor distributed. The pilot's authored mesh stays exact.
"""
import hashlib,itertools,json,re,shutil
from pathlib import Path
import numpy as np
import UnityPy
from UnityPy.helpers.MeshHelper import MeshHandler
from .native import native_rig
from .retarget import adapt,rotation_between,NEXT
from .skinning import validate_weights
from .native_weights import read as read_skin

ROOT=Path(__file__).resolve().parents[1]


def region(name):
    if name.startswith(('Head','Jaw')):return 'head'
    side=name.rsplit('_',1)[-1]
    if side in ('L','R'):
        if name.startswith(('Scapula','Shoulder','Elbow','Wrist','Thumb','Index','Middle','Ring','Pinky')):return 'arm_'+side
        if name.startswith(('Hip','Knee','Ankle','Toes')):return 'leg_'+side
    return 'torso'


class Grid:
    def __init__(self,points,cell=.04):
        self.points=np.asarray(points);self.cell=cell;self.cells={}
        for i,c in enumerate(np.floor(self.points/cell).astype(int)):self.cells.setdefault(tuple(c),[]).append(i)
    def nearest(self,point,k=4):
        point=np.asarray(point);center=np.floor(point/self.cell).astype(int);candidates=[]
        for radius in range(10):
            for delta in itertools.product(range(-radius,radius+1),repeat=3):
                if max(map(abs,delta))!=radius:continue
                candidates.extend(self.cells.get(tuple(center+delta),()))
            if len(candidates)<k:continue
            ids=np.asarray(candidates);distance=np.sum((self.points[ids]-point)**2,axis=1);take=np.argpartition(distance,k-1)[:k];bound=min(np.min(point-(center-radius)*self.cell),np.min((center+radius+1)*self.cell-point))
            if distance[take].max()<=bound*bound:return ids[take],distance[take]
        raise ValueError('Pilot surface is too far from the reviewed rig reference')


def segment_distance(p,a,b):
    direction=b-a;t=np.clip((p-a)@direction/max(direction@direction,1e-12),0,1);return np.linalg.norm(p-(a+t*direction))


def helmet_vertices(points,faces):
    """Keep connected chest/collar surfaces out of the rigid helmet region."""
    parent=np.arange(len(points))
    def root(i):
        while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for face in faces:
        a=root(face[0]);parent[root(face[1])]=a;parent[root(face[2])]=a
    labels=np.array([root(i) for i in range(len(points))]);head=np.zeros(len(points),bool)
    for label in np.unique(labels):
        mask=labels==label;p=points[mask]
        if p[:,2].min()>1.44 and p[:,2].max()>1.59:head[mask]=True
    return head


def build(config,source,output):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Choose a fresh local pilot rig directory')
    meta=json.loads((source/'source.json').read_text())
    for filename,field in [('source.npz','mesh_sha256'),('albedo.png','albedo_sha256')]:
        if hashlib.sha256((source/filename).read_bytes()).hexdigest()!=meta[field]:raise ValueError('Pilot source hash mismatch: '+filename)
    data=dict(np.load(source/'source.npz',allow_pickle=False));spec=json.loads((ROOT/'config/titanfall-stim-rig.json').read_text());v=data['positions']
    if not np.allclose([v.min(0),v.max(0)],spec['source_bounds'],atol=2e-5):raise ValueError('Pilot source differs from inspected authored model')
    native_root=Path(config.get('operator_original_root',config['bundle_root']));env=UnityPy.load(str(native_root/'src/thrid_person'));target=next(t for t in json.loads((ROOT/'config/operator-targets.json').read_text())['operators'] if t['id']=='operator_0');rig=native_rig(env,target);snapshot=rig['snapshots'][rig['primary'][0]];names=[n.split(':')[-1] for n in snapshot['bone_names']];parents=snapshot['bone_parents'];native_bind=snapshot['inverse_bind'];rest=np.linalg.inv(native_bind);points=rest[:,:3,3];index={n:i for i,n in enumerate(names)};joints={k:np.asarray(p,float) for k,p in spec['joints'].items()};scale=np.linalg.norm(joints['Head_M']-joints['Root_M'])/np.linalg.norm(points[index['Head_M']]-points[index['Root_M']]);matrices={}
    for name,p in joints.items():
        base,_,side=name.rpartition('_');child=NEXT.get(base if side in ('L','R') else name);child=child+'_'+side if child and side in ('L','R') else child;linear=np.eye(3)*scale
        finger=re.fullmatch(r'(.+Finger)([123])_([LR])',name)
        if finger:child=finger[1]+str(int(finger[2])+1)+'_'+finger[3]
        destination=joints.get(child)
        if name.startswith('Wrist_'):child='MiddleFinger1_'+side;destination=p+np.array([-.012 if side=='L' else .012,-.005,-.035])
        if child in index and destination is not None:
            a=points[index[child]]-points[index[name]];b=destination-p;direction=a/np.linalg.norm(a);transverse=scale*(.65 if name.startswith('Wrist_') else 1.);ratio=np.linalg.norm(b)/(np.linalg.norm(a)*transverse);linear=rotation_between(a,b)@(np.eye(3)+(ratio-1)*np.outer(direction,direction))*transverse
        if name.endswith('_M'):linear=np.eye(3)*scale
        matrices[name]=(linear,p-linear@points[index[name]])
    pilot_points=[]
    for i,name in enumerate(names):
        current=i;seen=set()
        while names[current] not in matrices:
            if current in seen or parents[current]<0:current=index['Root_M'];break
            seen.add(current);current=parents[current]
        linear,translation=matrices[names[current]];pilot_points.append(linear@points[i]+translation)
    pilot_rest=np.repeat(np.eye(4)[None],len(names),axis=0);pilot_rest[:,:3,3]=pilot_points;pilot_bind=np.linalg.inv(pilot_rest).astype('<f4');native_mesh=snapshot['mesh_object'].read();h=MeshHandler(native_mesh);h.process();reference=np.asarray(h.m_Vertices);bi,bw=read_skin(native_mesh,h);semantics={i:('Root_M' if n=='root_jnt' else n) for i,n in enumerate(names)};primary={n:i for i,n in semantics.items() if n!='Root_M' or i==index['Root_M']}
    warped,_,_,_,_=adapt(reference,np.asarray(h.m_Normals),names,native_bind,bi,bw,names,pilot_bind,source_targets=semantics,source_basis=np.eye(3),primary_sources=primary,source_root=index['Root_M'],source_head=index['Head_M']);groups=np.asarray([region(names[int(i)]) for i in bi[np.arange(len(bi)),np.argmax(bw,axis=1)]]);grids={};group_ids={}
    for group in ['torso','arm_L','arm_R','leg_L','leg_R']:
        ids=np.flatnonzero(groups==group);group_ids[group]=ids;grids[group]=Grid(warped[ids])
    capsules=[('torso','Root_M','Neck_M',.16)]
    for side in ('L','R'):
        capsules.extend([('arm_'+side,'Shoulder_'+side,'Elbow_'+side,.06),('arm_'+side,'Elbow_'+side,'Wrist_'+side,.055),('leg_'+side,'Hip_'+side,'Knee_'+side,.08),('leg_'+side,'Knee_'+side,'Ankle_'+side,.04),('leg_'+side,'Ankle_'+side,'ToesEnd_'+side,.05)])
    unique,inverse=np.unique(np.round(v,7),axis=0,return_inverse=True);helmet=helmet_vertices(unique,inverse[data['faces']]);out_indices=np.zeros((len(unique),4),dtype='<u2');out_weights=np.zeros((len(unique),4),dtype='<f4');distances=[];counts={}
    for vi,p in enumerate(unique):
        if helmet[vi]:out_indices[vi,0]=index['Head_M'];out_weights[vi,0]=1;counts['head']=counts.get('head',0)+1;continue
        group=min(capsules,key=lambda c:segment_distance(p,joints[c[1]],joints[c[2]])-c[3])[0];counts[group]=counts.get(group,0)+1;ids,distance=grids[group].nearest(p);ids=group_ids[group][ids];blend=1/np.maximum(distance,1e-8);blend/=blend.sum();weights={}
        for row,factor in zip(ids,blend):
            for bone,weight in zip(bi[row],bw[row]):
                if group=='torso' and region(names[int(bone)])!='torso':continue
                weights[int(bone)]=weights.get(int(bone),0)+float(weight)*factor
        best=sorted(weights.items(),key=lambda pair:-pair[1])[:4];total=sum(w for _,w in best)
        if total<=0:raise ValueError('Pilot skin transfer produced an unweighted vertex')
        for k,(bone,w) in enumerate(best):out_indices[vi,k]=bone;out_weights[vi,k]=w/total
        distances.append(float(np.sqrt(distance.min())))
    data.update(bone_indices=out_indices[inverse],bone_weights=out_weights[inverse],inverse_bind=pilot_bind,bone_parents=np.asarray(parents,dtype='<i4'));validate_weights(data['bone_indices'],data['bone_weights'],len(v),len(names));output.mkdir(parents=True);np.savez_compressed(output/'source.npz',**data);shutil.copyfile(source/'albedo.png',output/'albedo.png');report={'method':'Local native-reference skin transfer onto unchanged authored pilot mesh','unique_vertices':len(unique),'region_counts':counts,'nearest_reference_distance_percentiles_m':np.percentile(distances,[50,95,100]).tolist(),'source_geometry_unchanged':True,'native_geometry_embedded':False,'in_game_tested':False};meta.update(rigless=False,profile='titanfall_transfer',bone_names=names,bone_parents=parents,rigging=report,mesh_sha256=hashlib.sha256((output/'source.npz').read_bytes()).hexdigest());(output/'source.json').write_text(json.dumps(meta,indent=2)+'\n');return output
