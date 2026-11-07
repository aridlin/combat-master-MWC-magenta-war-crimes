"""Private audio audition files. Never compose, install, restore or play a game."""
import hashlib,json,os,re,uuid,wave
from pathlib import Path
import numpy as np
import UnityPy
from audio_pcm import resample
from bundle_utils import digest
from halftone.pipeline import build_id,safe_output
from tf2_audio import processed_slot,source_reader


def write_wav(path,pcm,rate):
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate);output.writeframes(pcm)


def audition_pcm(clips,rate=44100,gap_seconds=.3):
    """Separate the fixed clips; this is not a simulation of firing events."""
    parts=[];timeline=[];frame=0;gap=bytes(round(rate*gap_seconds)*2)
    for index,(pcm,source_rate) in enumerate(clips):
        signal=np.frombuffer(pcm,dtype='<i2')
        converted=signal if source_rate==rate else np.clip(np.rint(resample(signal,source_rate,rate)),-32768,32767).astype('<i2')
        data=converted.tobytes();timeline.append({'clip_index':index,'start_frame':frame,'frames':len(converted)})
        parts.append(data);frame+=len(converted)
        if index+1<len(clips):parts.append(gap);frame+=len(gap)//2
    return b''.join(parts),timeline


def export(config,bundle,output,pack,*,tf2='',audiojungle_source=''):
    if pack=='tf2_medigun_audio':spec,read_source=source_reader(config,tf2)
    elif pack=='audiojungle_medigun':
        from audiojungle import prepare
        spec,samples=prepare(audiojungle_source);read_source=samples.__getitem__
    else:raise ValueError('Choose a supported local audio pack to preview')
    if str(build_id(config))!=spec['build_id']:raise ValueError('Audio map belongs to another game build')
    bundle=Path(bundle).resolve();output=safe_output(output,config)
    safe_output(output,{'bundle_root':str(bundle.parent)})
    if output.exists():raise ValueError('Choose a fresh private audio preview directory')
    before=digest(bundle);env=UnityPy.load(str(bundle));byid={obj.path_id:obj for obj in env.objects};cache={};clips=[];rows=[]
    # Fully validate/decode before writing any preview. The source pack's
    # scripts and the native game are never executed.
    for index,row in enumerate(spec['clips']):
        obj=byid.get(int(row['id']))
        if obj is None:raise ValueError('Mapped native audio slot is missing: '+row['name'])
        clip,template,pcm,analysis,source=processed_slot(obj,row,read_source,cache)
        filename=str(index+1).zfill(2)+'.wav';clips.append((pcm,clip.m_Frequency))
        rows.append({'name':row['name'],'native_id':row['id'],'file':filename,'rate':clip.m_Frequency,'frames':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'analysis':analysis,**source})
    if digest(bundle)!=before:raise ValueError('Audio source bundle changed during preview')
    output.mkdir(parents=True)
    for row,(pcm,rate) in zip(rows,clips):write_wav(output/row['file'],pcm,rate)
    pcm,timeline=audition_pcm(clips);write_wav(output/'preview.wav',pcm,44100)
    report={'pack':pack,'private_audio_preview':True,'source_bundle_sha256':before,'source_bundle_unchanged':True,'clips':rows,
            'audition':{'file':'preview.wav','rate':44100,'frames':len(pcm)//2,'gap_seconds':.3,'timeline':timeline,'native_22050_clips_resampled_only_for_combined_audition':True},
            'original_rate_individual_WAVs_PCM_exact':True,'game_or_installer_selection_changed':False,
            'native_firing_sequence_simulated':False,'source_scripts_executed':False,'in_game_auditioned':False}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    return report


def request_preview(request):
    from installer.mwc_installer import engine
    game=request.get('game','')
    if not game:
        found=engine.discover()
        if len(found)!=1:raise ValueError('Choose your Combat Master game folder to preview its sound slots')
        game=found[0]
    config=engine.inspect_game(game);root=Path(config['bundle_root']).resolve();game=Path(game).expanduser().resolve()
    state=Path(request['state']).expanduser().resolve()
    if state==game or game in state.parents or state in game.parents:raise ValueError('Audio previews must be outside the game directory')
    pack={'preview_tf2_audio':'tf2_medigun_audio','preview_audiojungle':'audiojungle_medigun'}.get(request.get('action'))
    if pack is None:raise ValueError('Unknown audio preview action')
    with engine.locked(state):
        bundle=root/'root/audio';saved_path=state/'state.json'
        if saved_path.exists():
            saved=json.loads(saved_path.read_text(encoding='utf8'))
            if Path(saved['bundle_root']).resolve()!=root:raise ValueError('This backup directory belongs to another installation')
            expected=saved['originals'].get('root/audio')
            if expected is not None:
                bundle=state/'originals/root/audio'
                if digest(bundle)!=expected:raise ValueError('Original audio backup changed; preview cancelled')
        parent=state/'audio-previews'/pack
        # Do not follow a preexisting link out of this private preview cache.
        if not (parent.resolve().is_relative_to(state)):raise ValueError('Audio preview cache is outside the state directory')
        output=parent/uuid.uuid4().hex;previous=Path.cwd()
        try:
            os.chdir(state)
            report=export(config,bundle,output,pack,tf2=request.get('tf2',''),audiojungle_source=request.get('audiojungle_source',''))
        finally:os.chdir(previous)
        (state/'audio-preview.txt').write_text(str(output/'preview.wav'),encoding='utf8')
        # Keep the new preview and the preceding one, whose player may still
        # hold a file open on Windows. Never remove unowned directories.
        owned=[]
        for folder in parent.iterdir():
            marker=folder/'manifest.json'
            if folder.is_symlink() or not re.fullmatch(r'[0-9a-f]{32}',folder.name) or not marker.is_file():continue
            try:meta=json.loads(marker.read_text(encoding='utf8'))
            except (OSError,ValueError):continue
            if meta.get('private_audio_preview') is True and meta.get('pack')==pack:owned.append(folder)
        for folder in sorted(owned,key=lambda path:path.stat().st_mtime_ns,reverse=True)[2:]:
            try:
                # Keep the ownership marker until all WAVs can be removed.
                # Windows players may lock preview.wav; a partial rmtree could
                # otherwise remove its marker and strand an untracked cache.
                for child in folder.iterdir():
                    if child.name=='manifest.json':continue
                    if child.is_symlink() or not child.is_file():raise OSError('Unexpected preview cache entry')
                    child.unlink()
                (folder/'manifest.json').unlink();folder.rmdir()
            except OSError:pass # A player holding an old WAV is not an export failure.
    print('Audio preview: '+str(output/'preview.wav'),flush=True)
    return report
