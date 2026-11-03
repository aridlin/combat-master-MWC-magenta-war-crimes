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
            m,image,meta=model_asset({'models':{}},name);rows[name]={'asset':asset_kind({'models':{}},name),'vertices':len(m.vertices),'triangles':len(m.faces),'image_size':list(image.size),'author':meta['author']}
        print(json.dumps({'model_assets_verified':rows,'sky_faces':len(faces(32)),'game_files_modified':False,'in_game_tested':False},indent=2));return
    if a.status:
        from installer.mwc_installer.engine import discover
        games=discover();a.status.parent.mkdir(parents=True,exist_ok=True);a.status.write_text(games[0] if len(games)==1 else '',encoding='utf8');return
    if not a.request:p.error('--request or --status required')
    request=json.loads(a.request.read_text(encoding='utf8'))
    result=engine.execute(request)
    Path(request['state'],'selected.txt').write_text('\n'.join(result['selected']),encoding='utf8')
if __name__=='__main__':
    try:main()
    except BaseException as e:
        print('ERROR: '+str(e),flush=True);traceback.print_exc();sys.exit(1)
