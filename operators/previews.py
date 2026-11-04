"""Create private TF2 model thumbnails from the user's local files."""
import json,os,uuid
from pathlib import Path
import numpy as np
from catgun.geometry import render
from operators.assets import load
from operators.library import discover_tf2
from model_import.tf2 import import_models,flatten


def generate(state,requested=''):
    state=Path(state);run=state/'preview-imports'/uuid.uuid4().hex;raw=run/'tf2';import_models(discover_tf2({},requested),raw);output=state/'previews';output.mkdir(parents=True,exist_ok=True);report=[]
    basis=np.array([[-1.,0,0],[0,0,-1],[0,1,0]])
    for p in sorted(raw.glob('*/source.json')):
        name=p.parent.name
        if name=='medigun':
            from weapon_models.local_tf2 import prepare
            from weapon_models.imported import load as weapon
            fitted=prepare({},run/'medigun',requested);mesh,image,meta=weapon(fitted.name,fitted.parent);w,h=640,480
        else:
            source=flatten(p.parent,run/'normalized'/name);mesh,image,*_=load(source);mesh.vertices=(np.asarray(mesh.vertices)@basis.T).tolist();mesh.normals=(np.asarray(mesh.normals)@basis.T).tolist();mesh.faces=np.asarray(mesh.faces)[:,[0,2,1]].tolist();w,h=480,600
        v=np.asarray(mesh.vertices);center=(v.min(0)+v.max(0))/2;span=np.ptp(v,axis=0).max();identifier='medigun' if name=='medigun' else 'tf2_'+name;temporary=run/(identifier+'.png')
        render(mesh,temporary,eye=center+np.array([.8,-1.5,.20])*span,target=center,width=w,height=h,texture=image,label=identifier+' | local authored model preview | not in-game');os.replace(temporary,output/(identifier+'.png'));report.append(identifier)
    (output/'provenance.json').write_text(json.dumps({'models':report,'source':'Local Steam App 440 installation','redistribution':'Private previews; no Valve model assets included in MWC packages','game_files_modified':False,'in_game_tested':False},indent=2)+'\n');return report


def generate_native_pilots(state,models):
    """Create private source-color thumbnails for verified local pilot packages."""
    from .local_pilots import verify
    state=Path(state);run=state/'preview-imports'/uuid.uuid4().hex;run.mkdir(parents=True)
    output=state/'previews';output.mkdir(exist_ok=True);report=[]
    basis=np.array([[-1.,0,0],[0,0,-1],[0,1,0]])
    for model in sorted(models):
        source=state/'operator-imports'/model;hashes=verify(source,model);mesh,image,*_=load(source)
        mesh.vertices=(np.asarray(mesh.vertices)@basis.T).tolist();mesh.normals=(np.asarray(mesh.normals)@basis.T).tolist();mesh.faces=np.asarray(mesh.faces)[:,[0,2,1]].tolist()
        vertices=np.asarray(mesh.vertices);center=(vertices.min(0)+vertices.max(0))/2;span=np.ptp(vertices,axis=0).max();temporary=run/(model+'.png')
        render(mesh,temporary,eye=center+np.array([.8,-1.5,.20])*span,target=center,width=480,height=600,texture=image,label='Local pilot source preview | not in-game',lighting='studio')
        os.replace(temporary,output/(model+'.png'));report.append({'model':model,'source_sha256':hashes})
    (output/'provenance-titanfall.json').write_text(json.dumps({'models':report,'source':'Local Steam App 1237970 import','game_files_modified':False,'in_game_tested':False},indent=2)+'\n')
    return report
