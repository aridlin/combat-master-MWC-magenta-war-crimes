"""Anatomical palm frames for authored meshes with unusual hand proportions.

The native skeleton is unchanged. Fit palm width and roll from independent
middle/index/pinky landmarks instead of using torso scale for hand thickness.
"""
import numpy as np


def frame(wrist,middle,index,pinky):
    forward=np.asarray(middle,dtype=float)-wrist
    length=float(np.linalg.norm(forward))
    if length<1e-7:raise ValueError('Degenerate palm forward axis')
    forward/=length
    across=np.asarray(index,dtype=float)-pinky
    across-=forward*(across@forward)
    width=float(np.linalg.norm(across))
    if width<1e-7:raise ValueError('Degenerate palm lateral axis')
    across/=width;normal=np.cross(forward,across)
    return np.column_stack((forward,across,normal)),length,width


def fits(source_points,target_points,source_primary,target_index):
    result={}
    for side in ('L','R'):
        names=[n+'_'+side for n in ('Wrist','MiddleFinger1','IndexFinger1','PinkyFinger1')]
        if any(n not in source_primary or n not in target_index for n in names):
            raise ValueError('Hand fitting needs explicit palm landmarks: '+side)
        source,sl,sw=frame(*(source_points[source_primary[n]] for n in names))
        target,tl,tw=frame(*(target_points[target_index[n]] for n in names))
        # The segment fitter already matches longitudinal joint distances.
        # Palm width supplies hand thickness independently of torso scale.
        rotation=target@source.T;scale=tw/sw
        if not np.isfinite(rotation).all() or not np.isfinite(scale) or not .01<scale<1000 or not np.isclose(np.linalg.det(rotation),1,atol=1e-6):
            raise ValueError('Invalid anatomical palm fit')
        result[side]={'rotation':rotation,'scale':scale,'length_scale':tl/sl,'source_length':sl,'target_length':tl,'source_width':sw,'target_width':tw}
    return result




def transition(source,faces,baseline,trial,normals,bind,indices,weights,semantics,primary):
    """Blend fitted palms into the distal forearms using authored mesh edges.

    Hand vertices are fixed to their anatomical fit. The proximal forearm and
    the rest of the body keep their original fitted position. Positive edge
    weights give a harmonic displacement between those boundaries; UVs,
    topology and skin weights are never changed.
    """
    source=np.asarray(source,float);faces=np.asarray(faces,int);baseline=np.asarray(baseline,float);trial=np.asarray(trial,float)
    epsilon=float(np.ptp(source,axis=0).max()*1e-7)
    if not np.isfinite(source).all() or epsilon<=0:raise ValueError('Wrist transition needs finite nondegenerate source geometry')
    required=[joint+'_'+side for side in ('L','R') for joint in ('Elbow','Wrist')]
    if any(name not in primary for name in required):raise ValueError('Wrist transition needs explicit elbow and wrist landmarks')
    _,first,labels=np.unique(np.rint(source/epsilon).astype(np.int64),axis=0,return_index=True,return_inverse=True)
    points=source[first];old=baseline[first];target=trial[first];rest=np.linalg.inv(bind)[:,:3,3];fixed_hand=np.zeros(len(points),bool);free=np.zeros(len(points),bool)
    for side in ('L','R'):
        hand=np.array([s is not None and s.endswith('_'+side) and (s.startswith('Wrist_') or 'Finger' in s) for _,s in sorted(semantics.items())])
        forearm=np.array([s=='Elbow_'+side for _,s in sorted(semantics.items())])
        hc=(weights*hand[indices]).sum(1)[first];fc=(weights*forearm[indices]).sum(1)[first]
        elbow,wrist=rest[primary['Elbow_'+side]],rest[primary['Wrist_'+side]];axis=wrist-elbow
        if axis@axis<1e-14:raise ValueError('Degenerate forearm axis: '+side)
        fraction=(points-elbow)@axis/(axis@axis)
        fixed_hand |= hc>=.8
        free |= (fc>.1)&(fraction>.35)&(hc<.8)
    edges=np.unique(np.sort(np.r_[labels[faces[:,[0,1]]],labels[faces[:,[1,2]]],labels[faces[:,[2,0]]]],axis=1),axis=0)
    edges=edges[edges[:,0]!=edges[:,1]]
    adjacency=[{} for _ in points]
    for a,b in edges:
        weight=1/max(float(np.linalg.norm(points[a]-points[b])),epsilon*100)
        adjacency[a][b]=adjacency[b][a]=weight
    ids=np.flatnonzero(free);column={int(v):i for i,v in enumerate(ids)};matrix=np.zeros((len(ids),len(ids)));rhs=np.zeros((len(ids),3));delta=np.zeros_like(points);delta[fixed_hand]=target[fixed_hand]-old[fixed_hand]
    for row,a in enumerate(ids):
        matrix[row,row]=sum(adjacency[a].values())
        for b,weight in adjacency[a].items():
            if b in column:matrix[row,column[b]]-=weight
            else:rhs[row]+=weight*delta[b]
    if len(ids):
        try:delta[ids]=np.linalg.solve(matrix,rhs)
        except np.linalg.LinAlgError as exc:raise ValueError('Wrist transition has an unanchored mesh region') from exc
    vertices=baseline+delta[labels]
    # Preserve authored normals away from the affected hand/wrist region.
    normals=np.asarray(normals,float).copy();changed=np.linalg.norm(delta[labels],axis=1)>epsilon
    face_normal=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    welded_normal=np.zeros_like(points)
    for k in range(3):np.add.at(welded_normal,labels[faces[:,k]],face_normal)
    welded_normal/=np.maximum(np.linalg.norm(welded_normal,axis=1,keepdims=True),1e-20)
    normals[changed]=welded_normal[labels[changed]]
    if not np.isfinite(vertices).all() or not np.isfinite(normals).all() or not np.allclose(np.linalg.norm(normals,axis=1),1,atol=1e-4):raise ValueError('Invalid transition')
    if not np.array_equal(vertices[~changed].astype('<f4'),baseline[~changed].astype('<f4')):raise ValueError('Wrist transition moved fixed geometry')
    return vertices.astype('<f4'),normals.astype('<f4'),{'unique_vertices':len(points),'free_distal_forearm_vertices':len(ids),'fixed_hand_vertices':int(fixed_hand.sum()),'outside_hand_and_distal_forearm_unchanged':True,'maximum_displacement_native_units':float(np.linalg.norm(delta,axis=1).max()),'in_game_tested':False}
