"""Optional local-TF2 Minigun audio; retain native timing and event metadata."""
import copy,gc,hashlib,io,json,struct,wave
from pathlib import Path
import UnityPy
from UnityPy.helpers.ResourceReader import get_resource_data
from UnityPy.streams import EndianBinaryReader
from bundle_utils import digest
from halftone.assets import key,dump
from halftone.pipeline import build_id,safe_output
from operators.library import discover_tf2
from model_import.vpk import VPK
from cat_audio import replace_fsb
from audio_pcm import fit

ROOT=Path(__file__).resolve().parent
BUNDLE='root/audio'


def build(config,settings,tf2=''):
    spec=json.loads((ROOT/'config/tf2-audio-map.json').read_text())
    if str(build_id(config))!=spec['build_id']:raise ValueError('TF2 audio map belongs to another game build')
    source=Path(config['bundle_root'])/BUNDLE
    if digest(source)!=settings['source_sha256']:raise ValueError('TF2 audio baseline changed')
    output=safe_output(settings['output'],config);backup=safe_output(settings['backups'],config)/BUNDLE
    if (output/'manifest.json').exists():raise ValueError('Choose a fresh audio build directory')
    output.mkdir(parents=True,exist_ok=True)
    from installer.mwc_installer.engine import copy_private
    if backup.exists():
        if digest(backup)!=settings['source_sha256']:raise ValueError('TF2 audio backup belongs to another baseline')
    else:copy_private(source,backup)
    local=discover_tf2(config,tf2);vpk=VPK(local/'tf2_sound_misc_dir.vpk');env=UnityPy.load(str(backup));objects={key(o.assets_file.name,o.path_id):o for o in env.objects};byid={o.path_id:o for o in env.objects};resources=[p for p in env.file.files if p.endswith('.resource')]
    if len(resources)!=1:raise ValueError('Unexpected native audio resource layout')
    resource=resources[0];original_resource=env.file.files[resource].bytes;blob=bytearray(original_resource);changes={};cache={}
    for row in spec['clips']:
        obj=byid[int(row['id'])]
        if obj.type.name!='AudioClip' or obj.peek_name()!=row['name']:raise ValueError('Mapped native audio slot changed: '+row['name'])
        clip=obj.read();tree=obj.read_typetree();r=clip.m_Resource;template=get_resource_data(r.m_Source,obj.assets_file,r.m_Offset,r.m_Size)
        if clip.m_CompressionFormat!=0 or clip.m_Channels!=1 or clip.m_Frequency not in (22050,44100):raise ValueError('Unreviewed native PCM slot format')
        count=struct.unpack_from('<Q',template,60)[0]>>34
        if abs(count/clip.m_Frequency-clip.m_Length)>1/clip.m_Frequency:raise ValueError('Native PCM frame count/duration mismatch')
        path=row['source']
        if path not in cache:cache[path]=vpk.read(path)
        pcm,analysis=fit(cache[path],count,clip.m_Frequency,template[96:96+count*2],row['offset_seconds']);encoded=replace_fsb(template,pcm,clip.m_Frequency);blob.extend(b'\0'*((-len(blob))%16));offset=len(blob);blob.extend(encoded);tree['m_Resource']['m_Offset']=offset;tree['m_Resource']['m_Size']=len(encoded);obj.save_typetree(tree)
        changes[key(obj.assets_file.name,obj.path_id)]={'name':row['name'],'resource':tree['m_Resource'],'source_vpk_entry':path,'source_sha256':hashlib.sha256(cache[path]).hexdigest(),'fsb_sha256':hashlib.sha256(encoded).hexdigest(),'analysis':analysis}
        with wave.open(str(output/(row['name']+'.wav')),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(clip.m_Frequency);w.writeframes(pcm)
    reader=EndianBinaryReader(bytes(blob));reader.flags=env.file.files[resource].flags;env.file.files[resource]=reader;target=output/BUNDLE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(target));new={key(o.assets_file.name,o.path_id):o for o in checked.objects};old=UnityPy.load(str(backup));before={key(o.assets_file.name,o.path_id):o for o in old.objects}
    if set(new)!=set(before):raise ValueError('Audio object identities changed')
    for oid,obj in before.items():
        if oid in changes:
            tree=obj.read_typetree();tree['m_Resource']=changes[oid]['resource']
            if tree!=new[oid].read_typetree():raise ValueError('Audio event/spatial/load/timing metadata changed')
            clip=new[oid].read();r=clip.m_Resource;data=get_resource_data(r.m_Source,new[oid].assets_file,r.m_Offset,r.m_Size)
            if hashlib.sha256(data).hexdigest()!=changes[oid]['fsb_sha256']:raise ValueError('TF2 sample bytes did not roundtrip')
            count=struct.unpack_from('<Q',data,60)[0]>>34;replace_fsb(data,data[96:96+count*2],clip.m_Frequency)
        elif obj.get_raw_data()!=new[oid].get_raw_data():raise ValueError('An unrelated audio object changed')
    if checked.file.files[resource].bytes[:len(original_resource)]!=original_resource:raise ValueError('Existing audio resource bytes changed, including installed Lynx samples')
    report={'build_id':spec['build_id'],'pack':spec['pack'],'files':[{'bundle':BUNDLE,'backup':str(backup.resolve()),'output':str(target.resolve()),'source_sha256':digest(backup),'output_sha256':digest(target)}],'changes':changes,'verification':{'replaced_clips':len(changes),'all_other_objects_and_existing_sample_bytes_exact':True,'clip_duration_rate_channels_load_pitch_event_spatial_metadata_preserved':True,'fmod_pcm_roundtrip_exact':True,'Valve_audio_bundled':False},'in_game_auditioned':False};dump(output/'manifest.json',report);return report
