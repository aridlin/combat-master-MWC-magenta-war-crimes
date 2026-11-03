"""Explicit correspondence for inspected source skeletons, never name guessing."""
import re


def tf2_mapping(names,parents):
    """Secondary cloth/prop bones follow their inspected anatomical ancestry.

    TF2 uses prp_ for cigarettes, wrist cuffs, coat tails and helmets alike.
    A blanket chest mapping stretches sleeves and detaches head accessories.
    """
    from .retarget import CENTRAL,target_name
    if len(names)!=len(parents) or not {'bip_pelvis','bip_head'}<=set(names):
        raise ValueError('Unexpected TF2 source hierarchy')
    primary_roles={i:target_name(n) for i,n in enumerate(names) if n in CENTRAL or re.fullmatch(r'bip_(collar|upperArm|lowerArm|hand|hip|knee|foot|toe)_[LR]',n) or re.fullmatch(r'bip_(thumb|index|middle|ring|pinky)_[012]_[LR]',n)}
    roles=dict(primary_roles)
    for i,name in enumerate(names):
        if re.fullmatch(r'hlp_(suitArmTop|suitArmpitBack|thigh)_[LR]',name):roles[i]=target_name(name)
        # Heavy's one continuous chest bandolier is split into helper bones
        # under several spines and a collar. Keep those rigid sections in one
        # chest frame rather than stacking them as those native joints bend.
        if name.startswith('prp_bullet_'):roles[i]='Chest_M'
    semantics={}
    for i in range(len(names)):
        current=i;seen=set()
        while current not in roles and current>=0:
            if current in seen or current>=len(names):raise ValueError('Invalid TF2 source parent chain')
            seen.add(current);current=int(parents[current])
        semantics[i]=roles.get(current)
    return semantics,{name:i for i,name in primary_roles.items()}


def inherited_mapping(names,parents,primary):
    by_index={i:name for name,i in primary.items()};result={}
    for i in range(len(names)):
        current=i;seen=set()
        while current not in by_index and current>=0:
            if current in seen:raise ValueError('Cyclic source skeleton')
            seen.add(current);current=parents[current]
        result[i]=by_index.get(current,'Root_M')
    return result


def profile(name,meta):
    names=meta['bone_names'];parents=meta['bone_parents']
    if name.startswith('tf2_'):
        semantics,primary=tf2_mapping(names,parents)
        return dict(source_targets=semantics,primary_sources=primary,source_root=names.index('bip_pelvis'),source_head=names.index('bip_head'),source_basis=[[-1,0,0],[0,0,-1],[0,1,0]])
    if name=='titanfall_transfer':
        if len(names)!=83 or 'Head_M' not in names or 'Root_M' not in names:raise ValueError('Pilot local rig differs from reviewed native-reference hierarchy')
        semantics={i:('Root_M' if n=='root_jnt' else n) for i,n in enumerate(names)};primary={n:i for i,n in semantics.items() if n!='Root_M' or names[i]=='Root_M'}
        return dict(source_targets=semantics,source_basis=[[1,0,0],[0,1,0],[0,0,1]],primary_sources=primary,source_root=names.index('Root_M'),source_head=names.index('Head_M'))
    if name=='steve_classic':
        if len(names)!=22 or names[5]!='Head_M':raise ValueError('Steve rig differs from reviewed assembly')
        return dict(source_targets={i:n for i,n in enumerate(names)},source_basis=[[-1,0,0],[0,1,0],[0,0,1]],primary_sources={n:i for i,n in enumerate(names)},source_root=0,source_head=5)
    if name=='mario_skelenius':
        if len(names)!=99 or names[15]!='Head_53' or names[64]!='HandL_70':raise ValueError('Mario source rig differs from inspected model')
        primary={'Root_M':2,'Spine1_M':13,'Chest_M':14,'Head_M':15,'Hip_L':3,'Knee_L':4,'Ankle_L':6,'Toes_L':7,'Hip_R':8,'Knee_R':9,'Ankle_R':11,'Toes_R':12,'Scapula_L':59,'Shoulder_L':60,'Elbow_L':62,'Wrist_L':64,'Scapula_R':79,'Shoulder_R':80,'Elbow_R':82,'Wrist_R':84}
        for side,offset in [('L',0),('R',20)]:
            for finger,start in [('Index',65),('Pinky',68),('Middle',71),('Ring',74),('Thumb',77)]:
                for j in range(2 if finger=='Thumb' else 3):primary[finger+'Finger'+str(j+1)+'_'+side]=start+offset+j
        semantics=inherited_mapping(names,parents,primary)
        for i,target in [(5,'Ankle_L'),(10,'Ankle_R')]:semantics[i]=target
        return dict(source_targets=semantics,source_basis=[[-1,0,0],[0,1,0],[0,0,1]],primary_sources=primary,source_root=2,source_head=15)
    if name=='shrek_harrison':
        if len(names)!=104 or names[18]!='Jaw_Bone_19' or names[54]!='Left Ear_48':raise ValueError('Shrek source rig differs from inspected model')
        primary={'Root_M':4,'Spine1_M':13,'Spine2_M':14,'Chest_M':15,'Neck_M':16,'Head_M':17,'Hip_R':5,'Knee_R':6,'Ankle_R':7,'Toes_R':8,'Hip_L':9,'Knee_L':10,'Ankle_L':11,'Toes_L':12,'Scapula_R':56,'Shoulder_R':57,'Elbow_R':58,'Wrist_R':59,'Scapula_L':78,'Shoulder_L':79,'Elbow_L':80,'Wrist_L':81}
        for side,starts in [('R',{'Thumb':72,'Index':69,'Middle':66,'Ring':63,'Pinky':60}),('L',{'Thumb':94,'Index':91,'Middle':88,'Ring':85,'Pinky':82})]:
            for finger,start in starts.items():
                for j in range(3):primary[finger+'Finger'+str(j+1)+'_'+side]=start+j
        semantics=inherited_mapping(names,parents,primary)
        for i,target in [(100,'Ankle_R'),(101,'Toes_R'),(102,'Ankle_L'),(103,'Toes_L')]:semantics[i]=target
        return dict(source_targets=semantics,source_basis=[[-1,0,0],[0,1,0],[0,0,1]],primary_sources=primary,source_root=4,source_head=17)
    if name=='fishguy':
        central={'Hips':'Root_M','Spine':'Spine1_M','Spine1':'Spine2_M','Spine2':'Chest_M','Neck':'Neck_M','Head':'Head_M'}
        limb={'Shoulder':'Scapula','Arm':'Shoulder','ForeArm':'Elbow','Hand':'Wrist','UpLeg':'Hip','Leg':'Knee','Foot':'Ankle','ToeBase':'Toes'}
        primary={}
        for i,full in enumerate(names):
            short=full.split(':')[-1]
            if short in central:primary[central[short]]=i;continue
            m=re.fullmatch(r'(Left|Right)(Shoulder|Arm|ForeArm|Hand|UpLeg|Leg|Foot|ToeBase)',short)
            if m:primary[limb[m[2]]+'_'+('L' if m[1]=='Left' else 'R')]=i;continue
            m=re.fullmatch(r'(Left|Right)Hand(Thumb|Index|Middle|Ring|Pinky)([1234])',short)
            if m:primary[m[2]+'Finger'+m[3]+'_'+('L' if m[1]=='Left' else 'R')]=i
        if len(names)!=65 or not all(k in primary for k in ('Root_M','Head_M','Wrist_L','Wrist_R','Ankle_L','Ankle_R')):raise ValueError('Unexpected Fishguy body skeleton')
        return dict(source_targets=inherited_mapping(names,parents,primary),source_basis=[[0,-1,0],[-1,0,0],[0,0,1]],primary_sources=primary,source_root=primary['Root_M'],source_head=primary['Head_M'])
    raise ValueError('Source skeleton has no reviewed correspondence profile: '+name)
