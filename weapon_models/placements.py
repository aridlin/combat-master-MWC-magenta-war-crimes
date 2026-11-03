"""Visual-only authored model placement; original weapon rigs stay untouched."""
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def offset(settings,name):
    defaults=json.loads((ROOT/'config/weapon-model-placements.json').read_text())['models'];value=settings.get('models',{}).get(name,{}).get('offset',defaults.get(name,[0.,0.,0.]));value=np.asarray(value,dtype=float)
    if value.shape!=(3,) or not np.isfinite(value).all() or np.max(np.abs(value))>.25:raise ValueError('Visual model offset must be three finite metre values within 0.25 m')
    return value


def parent_position(settings,name):
    # The existing MWC child uses a 180-degree Y/Z rotation. Convert authored
    # Z-up displacement to parent Y-up, without moving the parent or sights.
    degrees,pivot=roll(settings,name);a=np.deg2rad(degrees);c,s=np.cos(a),np.sin(a);rotation=np.array([[c,0,s],[0,1,0],[-s,0,c]])
    x,y,z=offset(settings,name)+pivot-rotation@pivot
    return dict(zip('xyz',map(float,np.asarray([-x,z,y],dtype='<f4'))))


def roll(settings,name):
    defaults=json.loads((ROOT/'config/weapon-model-placements.json').read_text()).get('roll',{}).get(name,{})
    spec=settings.get('models',{}).get(name,{});degrees=spec.get('roll_degrees',defaults.get('degrees',0.));pivot=np.asarray(spec.get('roll_pivot',defaults.get('pivot',[0,0,0])),dtype=float)
    if type(degrees) not in (int,float) or not np.isfinite(degrees) or abs(degrees)>180 or pivot.shape!=(3,) or not np.isfinite(pivot).all() or np.max(np.abs(pivot))>1:raise ValueError('Invalid visual roll or shaft pivot')
    return degrees,pivot


def parent_rotation(settings,name):
    degrees,_=roll(settings,name);a=np.deg2rad(degrees)/2;s,c=np.sin(a)/2**.5,np.cos(a)/2**.5
    return dict(zip('xyzw',map(float,np.asarray([-s,c,c,-s],dtype='<f4'))))
