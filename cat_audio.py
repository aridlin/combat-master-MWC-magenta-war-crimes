#!/usr/bin/env python3
"""Replace only Lynx PCM samples with locally imported M1A0 cat sounds."""
import argparse,copy,gc,hashlib,io,json,shutil,struct,wave
from pathlib import Path
import numpy as np
import UnityPy
import fmod_toolkit
from fmod_toolkit.fmod import pyfmodex
import atexit
from UnityPy.helpers.ResourceReader import get_resource_data
from UnityPy.streams import EndianBinaryReader
from bundle_utils import digest
from halftone.assets import key,dump
from halftone.pipeline import build_id
from deploy_halftone import close_game,replace_verified

_decode_system=None

def decode_fsb(data):
    global _decode_system
    if _decode_system is None:
        _decode_system=pyfmodex.System();_decode_system.output=pyfmodex.enums.OUTPUTTYPE.NOSOUND
        _decode_system.init(1,pyfmodex.flags.INIT_FLAGS.NORMAL,None);atexit.register(_decode_system.release)
    sound=_decode_system.create_sound(data,pyfmodex.flags.MODE.OPENMEMORY,exinfo=pyfmodex.structure_declarations.CREATESOUNDEXINFO(length=len(data),numchannels=1,defaultfrequency=44100))
    try:return fmod_toolkit.sound_to_wav(sound,'cat',True)
    finally:sound.release()

REL='root/audio'
SOUNDS={'GM6Lynx_Shoot1':'catgun_fire01.wav','GM6Lynx_Shoot2':'catgun_fire03.wav',
        'GM6Lynx_Shoot3':'catgun_fire08.wav','GM6Lynx_MagOut':'catgun_reload00.wav',
        'GM6Lynx_MagIn':'catgun_reload.wav','GM6Lynx_BoltOpen':'catgun_fire04.wav',
        'GM6Lynx_BoltClose':'catgun_fire05.wav'}


def pcm_window(path,count):
    with wave.open(str(path)) as w:
        if w.getsampwidth()!=2 or w.getframerate()!=44100 or w.getcomptype()!='NONE':raise ValueError('Unsupported addon WAV format')
        a=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).astype(np.float64).mean(1)
    # Pick a continuous audible window; preserve pitch, with a short edge fade.
    start=0
    if len(a)>count:
        energy=np.concatenate(([0.],np.cumsum(a*a)));start=int(np.argmax(energy[count:]-energy[:-count]))
    a=a[start:start+count];a=np.pad(a,(0,count-len(a)))
    fade=min(220,count//2);a[:fade]*=np.linspace(0,1,fade);a[-fade:]*=np.linspace(1,0,fade)
    return np.clip(np.rint(a),-32768,32767).astype('<i2').tobytes(),start


def replace_fsb(template,pcm):
    if template[:4]!=b'FSB5' or struct.unpack_from('<4I',template,4)!=(1,1,36,0) or struct.unpack_from('<I',template,24)[0]!=2:raise ValueError('Unexpected original Lynx PCM container')
    mode=struct.unpack_from('<Q',template,60)[0]
    if mode&((1<<34)-1)!=16:raise ValueError('Expected mono 44100Hz FSB5 without extra chunks')
    count=mode>>34
    if len(pcm)!=count*2:raise ValueError('PCM duration mismatch')
    data=pcm+b'\0'*((-len(pcm))%32);header=bytearray(template[:96]);struct.pack_into('<I',header,20,len(data))
    encoded=bytes(header)+data
    # Decode with the same installed FMOD toolkit used by UnityPy, independently
    # checking the actual codec result, frame count and sample waveform.
    decoded=decode_fsb(encoded)
    if len(decoded)!=1:raise ValueError('Unexpected decoded subsound count')
    with wave.open(io.BytesIO(next(iter(decoded.values())))) as w:
        if (w.getnchannels(),w.getframerate(),w.getsampwidth(),w.getnframes())!=(1,44100,2,count):raise ValueError('FMOD decoded a different audio format/duration')
        if w.readframes(count)!=pcm:raise ValueError('FMOD PCM round-trip mismatch')
    return encoded


def verify(settings):
    r=json.loads((Path(settings['output'])/'manifest.json').read_text())
    if digest(Path(r['backup']))!=r['source_sha256'] or digest(Path(r['output']))!=r['output_sha256']:raise ValueError('Audio artifact hash mismatch')
    A=UnityPy.load(r['backup']);B=UnityPy.load(r['output']);a={key(o.assets_file.name,o.path_id):o for o in A.objects};b={key(o.assets_file.name,o.path_id):o for o in B.objects}
    if set(a)!=set(b):raise ValueError('Audio object IDs changed')
    for oid,obj in a.items():
        if oid not in r['changes']:
            if obj.get_raw_data()!=b[oid].get_raw_data():raise ValueError('Unrelated audio object changed')
        else:
            x=obj.read_typetree();z=b[oid].read_typetree();x['m_Resource']=r['changes'][oid]['resource']
            if x!=z:raise ValueError('Audio metadata or event binding changed')
            clip=b[oid].read();resource=clip.m_Resource;data=get_resource_data(resource.m_Source,b[oid].assets_file,resource.m_Offset,resource.m_Size)
            if hashlib.sha256(data).hexdigest()!=r['changes'][oid]['fsb_sha256']:raise ValueError('Installed sample bytes mismatch')
            count=struct.unpack_from('<Q',data,60)[0]>>34
            replace_fsb(data,data[96:96+count*2])
    old=A.file.files[r['resource_file']].bytes;new=B.file.files[r['resource_file']].bytes
    if new[:len(old)]!=old:raise ValueError('Original audio resource data changed')
    return {'replaced_clips':7,'original_clip_duration_pitch_event_refs_spatial_metadata_preserved':True,'unrelated_clips_and_original_resource_bytes_unchanged':True,'fmod_pcm_roundtrip_exact':True,'in_game_auditioned':False}


def build(config,settings):
    build_id(config);source=Path(config['bundle_root'])/REL
    if digest(source)!=settings.get('source_sha256'):raise ValueError('Run prepare for the intended audio baseline first')
    out=Path(settings['output']);out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh audio output directory')
    backup=Path(settings['backups'])/REL;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():
        if digest(backup)!=settings['source_sha256']:raise ValueError('Audio backup belongs to another baseline')
    else:shutil.copyfile(source,backup)
    env=UnityPy.load(str(backup));names={o.peek_name():o for o in env.objects if o.type.name=='AudioClip'}
    if not set(SOUNDS)<=set(names):raise ValueError('Missing original Lynx audio slots')
    resource_files=[p for p in env.file.files if p.endswith('.resource')]
    if len(resource_files)!=1:raise ValueError('Unexpected audio resource layout')
    resource_file=resource_files[0];blob=bytearray(env.file.files[resource_file].bytes);changes={}
    for name,wav in SOUNDS.items():
        obj=names[name];clip=obj.read();r=clip.m_Resource
        original=get_resource_data(r.m_Source,obj.assets_file,r.m_Offset,r.m_Size);mode=struct.unpack_from('<Q',original,60)[0];count=mode>>34
        pcm,start=pcm_window(Path(settings['source_assets'])/'sound/weapons'/wav,count);encoded=replace_fsb(original,pcm)
        blob.extend(b'\0'*((-len(blob))%16));offset=len(blob);blob.extend(encoded)
        tree=obj.read_typetree();tree['m_Resource']['m_Offset']=offset;tree['m_Resource']['m_Size']=len(encoded);obj.save_typetree(tree)
        changes[key(obj.assets_file.name,obj.path_id)]={'name':name,'source_wav':wav,'window_start_sample':start,'sample_count':count,'duration_seconds':count/44100,'resource':tree['m_Resource'],'fsb_sha256':hashlib.sha256(encoded).hexdigest()}
        with wave.open(str(out/(name+'.wav')),'wb') as w:w.setnchannels(1);w.setframerate(44100);w.setsampwidth(2);w.writeframes(pcm)
    reader=EndianBinaryReader(bytes(blob));reader.flags=env.file.files[resource_file].flags
    env.file.files[resource_file]=reader;output=out/REL;output.parent.mkdir(parents=True,exist_ok=True);temp=output.with_name(output.name+'.partial');temp.write_bytes(env.file.save(packer='lz4'));temp.replace(output);del env;gc.collect()
    dump(out/'manifest.json',{'backup':str(backup.resolve()),'output':str(output.resolve()),'source_sha256':digest(backup),'output_sha256':digest(output),'resource_file':resource_file,'changes':changes})
    return verify(settings)


def deploy(config,settings,action,dry_run):
    build_id(config);r=json.loads((Path(settings['output'])/'manifest.json').read_text());target=Path(config['bundle_root'])/REL;current=digest(target)
    if current not in [r['source_sha256'],r['output_sha256']]:raise ValueError('Unknown installed audio bundle')
    checked=verify(settings)
    if dry_run:return {'action':action,'dry_run':True,**checked}
    source=Path(r['output'] if action=='install' else r['backup']);wanted=r['output_sha256'] if action=='install' else r['source_sha256'];close_game(config)
    if current!=wanted:replace_verified(source,target,current,wanted)
    return {'action':action,'installed_sha256':digest(target),**checked}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','build','verify','install','restore']);p.add_argument('--config',default='cat-audio.json');p.add_argument('--dry-run',action='store_true');a=p.parse_args();s=json.loads(Path(a.config).read_text());c=json.loads(Path(s['base_config']).read_text())
    if a.action=='prepare':
        build_id(c);s['source_sha256']=digest(Path(c['bundle_root'])/REL);Path(a.config).write_text(json.dumps(s,indent=2)+'\n');result={'recorded_baseline':s['source_sha256'],'game_files_changed':False}
    else:result=build(c,s) if a.action=='build' else verify(s) if a.action=='verify' else deploy(c,s,a.action,a.dry_run)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
