"""Extract only visual and WAV data from a local M1A0 GMAD archive."""
import hashlib,io,json,lzma,struct,zlib
from pathlib import Path

FILES={'models/weapons/w_catgun.mdl','models/weapons/w_catgun.vvd',
       'models/weapons/w_catgun.dx90.vtx','materials/models/catgun/cat_gun_d_phong.vtf'}
FILES|={f'sound/weapons/catgun_fire{i:02d}.wav' for i in range(1,9)}
FILES|={'sound/weapons/catgun_reload.wav','sound/weapons/catgun_reload00.wav',
        'sound/weapons/catgun_reload_shorter.wav','sound/weapons/catgun_reload00_shorter.wav'}


def extract(addon,destination):
    source=Path(addon);raw=source.read_bytes()
    if len(raw)>16*1024*1024:raise ValueError('Unexpectedly large M1A0 archive')
    if raw[:4]!=b'GMAD':
        decoder=lzma.LZMADecompressor();raw=decoder.decompress(raw,max_length=16*1024*1024)
        if not decoder.eof:raise ValueError('Compressed addon exceeds limit')
    f=io.BytesIO(raw)
    if f.read(5)!=b'GMAD\x03':raise ValueError('Only GMAD v3 is supported')
    f.read(16)
    def cstr():
        result=bytearray()
        while True:
            c=f.read(1)
            if not c:raise ValueError('Truncated GMAD string')
            if c==b'\0':return result.decode('utf8')
            result.extend(c)
            if len(result)>65536:raise ValueError('GMAD string exceeds limit')
    while cstr():pass
    name=cstr();description=cstr();author=cstr();f.read(4)
    if name!='M1A0 Cat Gun':raise ValueError('This is not the inspected M1A0 addon')
    entries=[]
    while struct.unpack('<I',f.read(4))[0]:
        path=cstr();size,crc=struct.unpack('<qI',f.read(12))
        if size<0 or size>16*1024*1024:raise ValueError('Invalid GMAD entry size')
        entries.append((path,size,crc))
        if len(entries)>1000:raise ValueError('Unexpected GMAD entry count')
    selected={}
    for path,size,crc in entries:
        data=f.read(size)
        if len(data)!=size or zlib.crc32(data)!=crc:raise ValueError('GMAD CRC/length mismatch: '+path)
        if path in FILES:selected[path]=data
    if set(selected)!=FILES:raise ValueError('Required M1A0 visual inputs missing')
    root=Path(destination)
    for path,data in selected.items():
        target=root/path
        if target.exists() and target.read_bytes()!=data:raise ValueError('Different local asset exists: '+path)
    for path,data in selected.items():
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    provenance={'addon_name':name,'workshop_id':'827320827','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'files':{p:hashlib.sha256(d).hexdigest() for p,d in selected.items()},
                'credits':'Model/textures: Dragonfly GF Co., LTD and Gameforge 4D GmbH. GMod port: xdshot.',
                'lua_executed':False,'redistribution_license':'Not granted by this project; keep assets local.'}
    (root/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    return provenance
