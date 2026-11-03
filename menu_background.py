"""Replace only the named lobby background texture; never alter sprite bindings."""
import gc, hashlib, json, shutil
from pathlib import Path
import UnityPy
import numpy as np
from PIL import Image
from UnityPy.export.Texture2DConverter import image_to_texture2d
from bundle_utils import digest, inventory
from halftone.assets import dump, key
from halftone.pipeline import build_id

REL='root/root'
def build(config, settings):
    build_id(config)
    source=Path(config['bundle_root'])/REL
    if digest(source)!=settings['source_sha256']:raise ValueError('Menu baseline changed')
    out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    backup=Path(settings['backups'])/REL;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():raise ValueError('Choose a fresh menu backup')
    shutil.copyfile(source,backup)
    env=UnityPy.load(str(backup));expected=inventory(env)
    matches=[o for o in env.objects if o.type.name=='Texture2D' and o.peek_name()=='LobbyBG2']
    if len(matches)!=1:raise ValueError('Expected one LobbyBG2 texture')
    obj=matches[0];texture=obj.read();size=(texture.m_Width,texture.m_Height)
    with Image.open(settings['image']) as img:image=img.convert('RGBA').resize(size,Image.Resampling.LANCZOS)
    raw,_=image_to_texture2d(image,4)
    texture.image_data=raw;texture.m_TextureFormat=4;texture.m_CompleteImageSize=len(raw);texture.m_MipCount=1
    if texture.m_MipMap is not None:texture.m_MipMap=False
    texture.m_StreamData.path='';texture.m_StreamData.offset=0;texture.m_StreamData.size=0;texture.save()
    oid=key(obj.assets_file.name,obj.path_id)
    expected[(obj.assets_file.name,obj.path_id)]['sha256']=hashlib.sha256(obj.data).hexdigest()
    output=out/REL;output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(env.file.save(packer='lz4'))
    del env,texture;gc.collect()
    check=UnityPy.load(str(output))
    if inventory(check)!=expected:raise ValueError('Menu changed unrelated objects')
    found=next(o for o in check.objects if key(o.assets_file.name,o.path_id)==oid)
    if not np.array_equal(np.asarray(found.read().image.convert('RGBA')),np.asarray(image)):raise ValueError('Menu pixels mismatch')
    result={'files':[{'bundle':REL,'backup':str(backup.resolve()),'output':str(output.resolve()),'source_sha256':digest(backup),'output_sha256':digest(output)}], 'texture':oid,'all_other_objects_byte_exact':True,'in_game_tested':False}
    dump(out/'manifest.json',result);return result
