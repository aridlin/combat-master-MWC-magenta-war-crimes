"""Read classic vanilla sky artwork from a local client jar; never execute it.

Mojang artwork stays local. Only the importer is distributed with MWC.
The result is a static sky adaptation, not Minecraft's renderer or day cycle.
"""
import hashlib,io,json,zipfile
from pathlib import Path
import numpy as np
from PIL import Image

MEMBERS={name:'assets/minecraft/textures/environment/'+name+'.png'
         for name in ('clouds','sun','moon_phases')}
MEMBERS.update(biome='data/minecraft/worldgen/biome/plains.json',version='version.json')
EULA='https://www.minecraft.net/en-us/eula'


def load(jar):
    path=Path(jar).expanduser().resolve()
    if path.suffix.lower()!='.jar' or not path.is_file():
        raise ValueError('Choose a local classic Minecraft client .jar containing the vanilla sky textures')
    def digest():
        with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    before=digest();raw={}
    try:
        with zipfile.ZipFile(path) as archive:
            names=archive.namelist()
            for role,name in MEMBERS.items():
                if names.count(name)!=1:raise ValueError('Missing or duplicate classic Minecraft sky member: '+name)
                info=archive.getinfo(name)
                if not 0<info.file_size<=4*1024*1024:raise ValueError('Minecraft sky member exceeds the supported size: '+name)
                raw[role]=archive.read(name)
    except zipfile.BadZipFile as error:
        raise ValueError('The selected Minecraft jar is not a valid readable archive') from error
    result={}
    for role in ('clouds','sun','moon_phases'):
        with Image.open(io.BytesIO(raw[role])) as image:
            w,h=image.size
            if image.format!='PNG' or not 4<=min(w,h)<=max(w,h)<=1024 or w&(w-1) or h&(h-1):
                raise ValueError('Unsupported classic Minecraft sky image: '+role)
            result[role]=np.asarray(image.convert('RGBA')).copy()
    cloud,sun,moon=(result[k] for k in ('clouds','sun','moon_phases'))
    if cloud.shape[0]!=cloud.shape[1] or sun.shape[0]!=sun.shape[1] or moon.shape[:2]!=(sun.shape[0]*2,sun.shape[1]*4):
        raise ValueError('Unsupported cloud, sun or four-by-two moon-phase layout')
    try:
        effects=json.loads(raw['biome'])['effects'];version=json.loads(raw['version'])['id']
        if not isinstance(version,str) or not 0<len(version)<=128:raise ValueError()
        for field in ('sky_color','fog_color'):
            value=effects[field]
            if type(value) is not int or not 0<=value<=0xffffff:raise ValueError()
            result[field]=tuple((value>>shift)&255 for shift in (16,8,0))
    except (KeyError,TypeError,ValueError) as error:
        raise ValueError('Minecraft source lacks a supported plains sky/fog palette or version') from error
    if digest()!=before:raise ValueError('Minecraft source changed while it was being read')
    result['provenance']={'kind':'local_minecraft_classic','version':version,'jar_sha256':before,
        'members':{MEMBERS[k]:hashlib.sha256(value).hexdigest() for k,value in raw.items()},
        'sky_color':list(result['sky_color']),'fog_color':list(result['fog_color']),
        'assets_redistributed':False,'license_url':EULA,'static_clouds_and_celestial_texture_adaptation':True,
        'night_palette':'MWC adaptation; native nighttime environment not verified'}
    return result


def colors(directions,night,assets):
    d=np.asarray(directions,float);length=np.linalg.norm(d,axis=-1,keepdims=True)
    if d.shape[-1:]!=(3,) or not np.isfinite(d).all() or np.any(length<=0):raise ValueError('Invalid sky sampling directions')
    d=d/length;height=np.clip(d[...,1],0,1)[...,None]
    top=np.array([12,20,48] if night else assets['sky_color'])
    horizon=np.array([39,47,72] if night else assets['fog_color'])
    rgb=horizon*(1-height)+top*height
    cloud=assets['clouds'];safe=np.maximum(d[...,1],.04)
    x=np.floor(d[...,0]/safe*12).astype(np.int64)%cloud.shape[1]
    z=np.floor(d[...,2]/safe*12).astype(np.int64)%cloud.shape[0]
    sample=cloud[z,x];alpha=sample[...,3:4]/255*np.clip((d[...,1:2]-.10)/.20,0,1)
    rgb=rgb*(1-alpha)+sample[...,:3]*(.24 if night else 1)*alpha
    sun=np.array([.45,.72,.35]);sun/=np.linalg.norm(sun)
    right=np.cross(sun,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,sun)
    front=d@sun;u=(d@right)/np.maximum(front,1e-8);v=(d@up)/np.maximum(front,1e-8)
    mask=(front>0)&(np.abs(u)<.30)&(np.abs(v)<.30)
    image=assets['sun']
    if night:image=assets['moon_phases'][:image.shape[0],:image.shape[1]]
    tx=np.clip(np.floor((u/.60+.5)*image.shape[1]),0,image.shape[1]-1).astype(int)
    ty=np.clip(np.floor((.5-v/.60)*image.shape[0]),0,image.shape[0]-1).astype(int)
    celestial=image[ty,tx]
    # Vanilla's black-backed celestial artwork is additive, not an opaque quad.
    rgb+=celestial[...,:3]*(celestial[...,3:4]/255)*mask[...,None]
    return np.rint(np.clip(rgb,0,255)).astype(np.uint8)
