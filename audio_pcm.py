"""Offline WAV fitting for native PCM sound slots; no playback/event changes."""
import io,wave
import numpy as np


def read_wav(data):
    with wave.open(io.BytesIO(data)) as w:
        channels,rate,width,frames=w.getnchannels(),w.getframerate(),w.getsampwidth(),w.getnframes()
        if channels not in (1,2) or width!=2 or w.getcomptype()!='NONE' or not 8000<=rate<=96000:raise ValueError('Expected a mono/stereo PCM16 WAV')
        samples=np.frombuffer(w.readframes(frames),dtype='<i2').reshape(-1,channels).astype(float).mean(1)/32768
    if not len(samples):raise ValueError('Empty source WAV')
    return samples,rate


def resample(samples,source_rate,target_rate):
    samples=np.asarray(samples,dtype=float)
    if source_rate==target_rate:return samples.copy()
    ratio=target_rate/source_rate
    if ratio<1:
        # Anti-alias before downsampling, unlike plain point interpolation.
        x=np.arange(65)-32;cutoff=.45*ratio;kernel=2*cutoff*np.sinc(2*cutoff*x)*np.hanning(65);kernel/=kernel.sum();samples=np.convolve(np.pad(samples,(32,32),mode='edge'),kernel,mode='valid')
    count=round(len(samples)*ratio);positions=np.arange(count)/ratio
    return np.interp(positions,np.arange(len(samples)),samples)


def fit(data,count,rate,reference_pcm,offset_seconds=0.):
    if count<1 or rate not in (22050,44100) or len(reference_pcm)!=count*2 or not np.isfinite(offset_seconds) or offset_seconds<0:raise ValueError('Invalid native sound-slot dimensions/window')
    samples,source_rate=read_wav(data);samples=resample(samples,source_rate,rate);start=min(round(offset_seconds*rate),max(0,len(samples)-count));signal=np.pad(samples[start:start+count],(0,max(0,count-len(samples[start:start+count]))));reference=np.frombuffer(reference_pcm,dtype='<i2').astype(float)/32768;original_rms=float(np.sqrt(np.mean(reference**2)));source_rms=float(np.sqrt(np.mean(signal**2)));gain=min(4.,original_rms/max(source_rms,1e-12));signal*=gain
    peak=float(np.max(np.abs(signal)))
    if peak>.98:signal*=.98/peak
    fade=min(round(rate*.005),count//2)
    if fade:signal[:fade]*=np.linspace(0,1,fade);signal[-fade:]*=np.linspace(1,0,fade)
    pcm=np.clip(np.rint(signal*32768),-32768,32767).astype('<i2').tobytes()
    return pcm,{'source_rate':source_rate,'target_rate':rate,'source_window_start_frame':start,'frames':count,'pitch_preserved_by_rate_conversion':True,'gain_before_peak_limit':gain,'original_rms':original_rms,'output_rms':float(np.sqrt(np.mean(signal**2))),'output_peak':float(np.max(np.abs(signal)))}
