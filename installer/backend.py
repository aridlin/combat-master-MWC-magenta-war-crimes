#!/usr/bin/env python3
"""Backend entry point. Arguments are paths, never shell fragments."""
import argparse,json,os,sys,traceback
from pathlib import Path
if getattr(sys,'frozen',False):ROOT=Path(sys._MEIPASS)
else:ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from installer.mwc_installer import engine
engine.ROOT=ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('--request',type=Path);p.add_argument('--status',type=Path);p.add_argument('--diagnose',action='store_true');a=p.parse_args()
    if a.diagnose:
        from weapon_models.bundles import model_asset,asset_kind,SPECS
        from skybox.pixels import faces
        rows={}
        for name in SPECS:
            if asset_kind({'models':{}},name)=='local_tf2':
                rows[name]={'asset':'local_tf2','requires_local_tf2':True,'content_bundled':False};continue
            m,image,meta=model_asset({'models':{}},name);rows[name]={'asset':asset_kind({'models':{}},name),'vertices':len(m.vertices),'triangles':len(m.faces),'image_size':list(image.size),'author':meta['author']}
        from operators.assets import load as operator_asset
        from operators.skinning import validate_weights
        operators={}
        for name in ('shrek','fishguy','mario','minecraft_steve'):
            mesh,texture,indices,weights,meta=operator_asset(ROOT/'assets/operator-sources'/name);validate_weights(indices,weights,len(mesh.vertices),len(meta['bone_names']));operators[name]={'vertices':len(mesh.vertices),'triangles':len(mesh.faces),'source_bones':len(meta['bone_names']),'hashes_verified':True}
        print(json.dumps({'model_assets_verified':rows,'operator_sources_verified':operators,'sky_faces':len(faces(32)),'game_files_modified':False,'in_game_tested':False},indent=2));return
    if a.status:
        from installer.mwc_installer.engine import discover
        from operators.assignments import load_plan,save_plan
        state_path=a.status.parent/'state.json';saved=json.loads(state_path.read_text()) if state_path.exists() else {}
        choices=load_plan(a.status.parent) if (a.status.parent/'operator-plan.json').exists() else saved.get('operator_assignments',{})
        save_plan(a.status.parent,choices)
        from operators.styles import load as load_styles,save as save_styles
        save_styles(a.status.parent,load_styles(a.status.parent,saved.get('operator_appearance'),players='players' in saved.get('selected',[])))
        games=discover();a.status.parent.mkdir(parents=True,exist_ok=True);a.status.write_text(games[0] if len(games)==1 else '',encoding='utf8');return
    if not a.request:p.error('--request or --status required')
    request=json.loads(a.request.read_text(encoding='utf8'))
    if request.get('action')=='preview_tf2':
        from operators.previews import generate
        with engine.locked(Path(request['state'])):models=generate(request['state'],request.get('tf2',''))
        print('Created '+str(len(models))+' private TF2 previews. Game files unchanged.',flush=True);return
    if request.get('action')=='save_operators':
        from operators.assignments import save_plan
        with engine.locked(Path(request['state'])):
            saved=save_plan(request['state'],request.get('operator_assignments',{}))
            from operators.styles import save as save_styles
            save_styles(request['state'],request.get('operator_appearance'),players='players' in request.get('selected',[]))
            Path(request['state'],'tf2.txt').write_text(request.get('tf2',''),encoding='utf8')
        print('Saved '+str(len(saved))+' operator choices. Game files unchanged; rig builds and installation remain pending.',flush=True)
        return
    result=engine.execute(request)
    Path(request['state'],'selected.txt').write_text('\n'.join(result['selected']),encoding='utf8')
    if request['action']=='apply':
        from operators.assignments import save_plan
        save_plan(request['state'],result.get('operator_assignments',{}));Path(request['state'],'tf2.txt').write_text(request.get('tf2',''),encoding='utf8')
    from operators.styles import save as save_styles
    save_styles(request['state'],result.get('operator_appearance'),players='players' in result['selected'])
if __name__=='__main__':
    try:main()
    except BaseException as e:
        print('ERROR: '+str(e),flush=True);traceback.print_exc();sys.exit(1)
