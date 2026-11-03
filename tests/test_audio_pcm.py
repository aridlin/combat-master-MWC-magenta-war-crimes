import io,unittest,wave
import numpy as np
from audio_pcm import fit,resample


class AudioPCM(unittest.TestCase):
    def test_downsample_preserves_pitch_and_rejects_aliasing(self):
        rate=44100;t=np.arange(rate)/rate;low=resample(np.sin(2*np.pi*1500*t),rate,22050);high=resample(np.sin(2*np.pi*18000*t),rate,22050)
        self.assertEqual(len(low),22050);self.assertEqual(np.argmax(np.abs(np.fft.rfft(low))),1500);self.assertLess(np.sqrt(np.mean(high[100:-100]**2)),.01)
    def test_stereo_source_fits_exact_mono_slot_duration_and_safe_level(self):
        n=44100;signal=np.rint(np.sin(2*np.pi*440*np.arange(n)/44100)*10000).astype('<i2');stream=io.BytesIO()
        with wave.open(stream,'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(44100);w.writeframes(np.c_[signal,signal].astype('<i2').tobytes())
        reference=np.full(11025,3000,dtype='<i2').tobytes();pcm,report=fit(stream.getvalue(),11025,22050,reference,.1);samples=np.frombuffer(pcm,dtype='<i2');self.assertEqual(len(samples),11025);self.assertEqual(samples[0],0);self.assertEqual(samples[-1],0);self.assertLessEqual(np.max(np.abs(samples.astype(float))),32767);self.assertAlmostEqual(report['output_rms'],3000/32768,delta=.002)


if __name__=='__main__':unittest.main()
