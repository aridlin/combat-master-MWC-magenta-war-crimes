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
    x,y,z=offset(settings,name);return dict(zip('xyz',map(float,np.asarray([-x,z,y],dtype='<f4'))))
