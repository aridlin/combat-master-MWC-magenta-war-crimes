"""Local Audiojungle excerpts; no archive redistribution or script execution."""
import hashlib,json
from pathlib import Path,PurePosixPath
from audio_pcm import read_wav
import fmod_toolkit
from cat_audio import pyfmodex
from tf2_audio import build_slots

ROOT=Path(__file__).resolve().parent
MAX_SOURCE_BYTES=16*1024*1024


def decode_mp3(data):
    # MP3 is a top-level stream, whereas the native FSB reader enumerates
    # subsounds. No mixer channel is played and no output device is opened.
    system=pyfmodex.System();sound=None
    try:
        system.output=pyfmodex.enums.OUTPUTTYPE.NOSOUND
        system.init(1,pyfmodex.flags.INIT_FLAGS.NORMAL,None)
        sound=system.create_sound(data,pyfmodex.flags.MODE.OPENMEMORY,exinfo=pyfmodex.structure_declarations.CREATESOUNDEXINFO(length=len(data)))
        if sound.num_subsounds:raise ValueError('Expected one top-level Audiojungle MP3 stream')
        return fmod_toolkit.subsound_to_wav(sound,True)
    finally:
        if sound is not None:sound.release()
        system.release()


def read_local(root,relative):
    path=PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or path.suffix.lower() not in ('.wav','.mp3'):
        raise ValueError('Invalid Audiojungle sample path')
    target=(root/relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():raise ValueError('Audiojungle sample missing or outside selected folder: '+relative)
    if not 0<target.stat().st_size<=MAX_SOURCE_BYTES:raise ValueError('Audiojungle sample is empty or too large: '+relative)
    original=target.read_bytes()
    if path.suffix.lower()=='.mp3':
        wav=decode_mp3(original)
    else:wav=original
    samples,rate=read_wav(wav)
    if len(samples)>rate*60:raise ValueError('Audiojungle sample exceeds one minute')
    return wav,{'source_local_file':relative,'source_sha256':hashlib.sha256(original).hexdigest(),'decoded_wav_sha256':hashlib.sha256(wav).hexdigest(),'source_seconds':len(samples)/rate}


def prepare(folder,spec=None):
    """Validate all chosen files before expensive composition; read only."""
    if not isinstance(folder,(str,Path)) or not str(folder).strip():raise ValueError('Choose the extracted Audiojungle folder containing sound/')
    root=Path(folder).expanduser().resolve()
    if not root.is_dir():raise ValueError('Audiojungle source must be an extracted folder containing sound/, not the .7z archive')
    if spec is None:spec=json.loads((ROOT/'config/audiojungle-map.json').read_text())
    cache={row['source']:None for row in spec['clips']}
    for relative in cache:cache[relative]=read_local(root,relative)
    return spec,cache


def build(config,settings,folder):
    spec,cache=prepare(folder)
    return build_slots(config,settings,spec,cache.__getitem__,{'source_audio_bundled':False,'source_scripts_executed':False,'random_event_scripts_imported':False,'fixed_excerpts_only':True})
