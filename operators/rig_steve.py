"""Rig Vincent Yanez's existing classic Steve mesh; no substitute geometry.

Adds deformation cuts to the authored flat surfaces, interpolating their UVs,
then assigns an explicit block-character skeleton. Original silhouette stays
exact before fitting. Run with ordinary Python after blender_flatten export.
"""
import argparse,json,shutil
from pathlib import Path
import numpy as np


def rig(source,output):
    source,output=Path(source),Path(output)
    if output.exists():raise ValueError('Use a fresh Steve rig output')
    data=np.load(source/'source.npz',allow_pickle=False);meta=json.loads((source/'source.json').read_text());v=data['positions'];lo=v.min(0);hi=v.max(0)
    if not np.allclose(lo,[-8,-4,-16],atol=2e-4) or not np.allclose(hi,[8,4,16],atol=2e-4):raise ValueError('Steve source differs from inspected 32-pixel classic model')
    names=['Root_M','Spine1_M','Spine2_M','Chest_M','Neck_M','Head_M'];points=[[0,0,-4],[0,0,-1],[0,0,2],[0,0,6],[0,0,8],[0,0,8]];parents=[-1,0,1,2,3,4]
    for side,sign in [('L',1),('R',-1)]:
        for name,point,parent in [('Scapula',[sign*3,0,6],'Chest_M'),('Shoulder',[sign*6,0,7],'Scapula_'+side),('Elbow',[sign*6,0,2],'Shoulder_'+side),('Wrist',[sign*6,0,-4],'Elbow_'+side),('Hip',[sign*2,0,-4],'Root_M'),('Knee',[sign*2,0,-10],'Hip_'+side),('Ankle',[sign*2,0,-15.5],'Knee_'+side),('Toes',[sign*2,-2,-15.5],'Ankle_'+side)]:
            names.append(name+'_'+side);points.append(point);parents.append(names.index(parent))
    rest=np.repeat(np.eye(4)[None],len(names),axis=0);rest[:,:3,3]=points;positions=[];normals=[];uv=[];faces=[];fm=[];indices=[];weights=[]
    regions=[('body','L',[-4,-2,-4],[4,2,8]),('head','L',[-4,-4,8],[4,4,16]),('arm','L',[4,-2,-4],[8,2,8]),('arm','R',[-8,-2,-4],[-4,2,8]),('leg','L',[0,-2,-16],[4,2,-4]),('leg','R',[-4,-2,-16],[0,2,-4])]
    if len(data['faces'])!=72:raise ValueError('Steve topology differs from reviewed six-part source')
    for part_no,(_,_,low,high) in enumerate(regions):
        region=v[data['faces'][part_no*12:(part_no+1)*12]].reshape(-1,3)
        if not np.allclose(region.min(0),low,atol=2e-4) or not np.allclose(region.max(0),high,atol=2e-4):raise ValueError('Steve source part ordering changed')
    for face_no,(face,material) in enumerate(zip(data['faces'],data['face_materials'])):
        part,side,_,_=regions[face_no//12]
        # Split at the existing arm/leg joint heights, preserving every original
        # triangle's surface and barycentrically interpolated normal/UV data.
        cuts=[2.] if part=='arm' else [-10.] if part=='leg' else []
        polygons=[[(v[i].copy(),data['normals'][i].copy(),data['uv'][i].copy()) for i in face]]
        for cut in cuts:
            pieces=[]
            for polygon in polygons:
                if min(p[0][2] for p in polygon)>=cut-1e-5 or max(p[0][2] for p in polygon)<=cut+1e-5:pieces.append(polygon);continue
                for lower in [True,False]:
                    clipped=[]
                    for first,second in zip(polygon,polygon[1:]+polygon[:1]):
                        aa=first[0][2]-cut;bb=second[0][2]-cut;inside=aa<=0 if lower else aa>=0
                        if inside:clipped.append(first)
                        if aa*bb<0:
                            t=-aa/(bb-aa);clipped.append(tuple(a+(b-a)*t for a,b in zip(first,second)))
                    if len(clipped)>=3:pieces.append(clipped)
            polygons=pieces
        for polygon in polygons:
            for k in range(1,len(polygon)-1):
                triangle=[]
                for p,n,t in [polygon[0],polygon[k],polygon[k+1]]:
                    triangle.append(len(positions));positions.append(p);normals.append(n/np.linalg.norm(n));uv.append(t)
                    if part=='head':skin=[('Head_M',1.)]
                    elif part=='body':skin=[('Root_M',1.)]
                    else:
                        joint=2. if part=='arm' else -10.;upper='Shoulder' if part=='arm' else 'Hip';lower='Elbow' if part=='arm' else 'Knee';blend=float(np.clip((p[2]-joint)/1.+.5,0,1));skin=[(upper+'_'+side,blend),(lower+'_'+side,1-blend)]
                    indices.append([names.index(b) for b,w in skin]+[0]*(4-len(skin)));weights.append([w for b,w in skin]+[0.]*(4-len(skin)))
                faces.append(triangle);fm.append(material)
    output.mkdir(parents=True)
    for mat in meta['materials']:
        if 'pixels' in mat:shutil.copyfile(source/mat['pixels'],output/mat['pixels']);mat['base_color_linear']=[1.,1.,1.,1.]
    np.savez_compressed(output/'source.npz',positions=np.asarray(positions,dtype='<f4'),normals=np.asarray(normals,dtype='<f4'),uv=np.asarray(uv,dtype='<f4'),faces=np.asarray(faces,dtype='<u4'),face_materials=np.asarray(fm,dtype='<i4'),bone_indices=np.asarray(indices,dtype='<u2'),bone_weights=np.asarray(weights,dtype='<f4'),inverse_bind=np.linalg.inv(rest).astype('<f4'),bone_parents=np.asarray(parents,dtype='<i4'))
    meta.update(bone_names=names,bone_parents=parents,vertices=len(positions),triangles=len(faces),rigging='Explicit block-character joints, original authored mesh with interpolated elbow/knee cuts; no replacement body geometry',in_game_tested=False);(output/'source.json').write_text(json.dumps(meta,indent=2)+'\n');return meta


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();print(json.dumps(rig(a.source,a.output),indent=2))
