"""Exercise the actual FMOD decoder using original synthetic PCM, no game data."""
import struct,unittest
import numpy as np
from cat_audio import replace_fsb


class NativePCMContainers(unittest.TestCase):
    def test_both_native_rates_decode_to_exact_tone_samples_without_playback(self):
        for rate,mode in ((44100,16),(22050,10)):
            with self.subTest(rate=rate):
                count=1000;header=bytearray(96);header[:4]=b'FSB5'
                struct.pack_into('<6I',header,4,1,1,36,0,2016,2)
                struct.pack_into('<Q',header,60,(count<<34)|mode)
                pcm=np.rint(np.sin(2*np.pi*440*np.arange(count)/rate)*10000).astype('<i2').tobytes()
                # replace_fsb independently decodes through FMOD NOSOUND and
                # rejects any changed channels/rate/frame count/sample values.
                encoded=replace_fsb(bytes(header),pcm,rate)
                self.assertEqual(encoded[96:96+len(pcm)],pcm)
                self.assertEqual(struct.unpack_from('<Q',encoded,60)[0],(count<<34)|mode)


if __name__=='__main__':unittest.main()
