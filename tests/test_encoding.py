import struct
import unittest
import numpy as np
import texture2ddecoder
from halftone.encoding import dxt1_alpha


class PreserveDXTAlpha(unittest.TestCase):
    def test_dxt1_cutouts_promote_without_alpha_changes(self):
        # Palette mode c0<=c1: alternating opaque index 0 / transparent index 3.
        indices=sum((3 if i%2 else 0)<<(2*i) for i in range(16))
        raw=struct.pack('<HHI',0,65535,indices)
        alpha=dxt1_alpha(np.frombuffer(raw,dtype=np.uint8).reshape(1,8)).tobytes()
        pink=struct.pack('<HHI',0xF81F,0xF81F,0)
        decoded=texture2ddecoder.decode_bc3(alpha+pink,4,4)
        self.assertEqual(list(decoded[3::4]),[255 if i%2==0 else 0 for i in range(16)])

    def test_dxt1_four_color_index_three_is_opaque(self):
        raw=struct.pack('<HHI',65535,0,0xffffffff)
        alpha=dxt1_alpha(np.frombuffer(raw,dtype=np.uint8).reshape(1,8)).tobytes()
        decoded=texture2ddecoder.decode_bc3(alpha+struct.pack('<HHI',0xF81F,0xF81F,0),4,4)
        self.assertEqual(set(decoded[3::4]),{255})


if __name__=='__main__': unittest.main()
