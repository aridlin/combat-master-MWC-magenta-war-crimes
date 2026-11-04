"""VPK2.3 fixtures exercise chunk boundaries and integrity without game data."""
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from model_import.respawn_vpk import RespawnVPK


def fixture(root,inline=False,compressed=False,path='models/pilot',continuation=None,crc_delta=0):
    chunks=[b'first chunk',b'second chunk'];payload=b'';records=b''
    archive=0x7fff if inline else 0
    for n,data in enumerate(chunks):
        packed=zlib.compress(data) if compressed else data
        records+=struct.pack('<IHQQQ',3,0,len(payload),len(packed),len(data))
        records+=struct.pack('<H',0xffff if n==1 else archive if continuation is None else continuation)
        payload+=packed
    folder,name=path.rsplit('/',1)
    tree=b'mdl\0'+folder.encode()+b'\0'+name.encode()+b'\0'
    tree+=struct.pack('<IHH',zlib.crc32(b''.join(chunks))^crc_delta,0,archive)+records+b'\0\0\0'
    p=Path(root)/'englishclient_mp_test.bsp.pak000_dir.vpk'
    p.write_bytes(struct.pack('<IHHII',0x55AA1234,2,3,len(tree),0)+tree+(payload if inline else b''))
    if not inline:p.with_name('client_mp_test.bsp.pak000_000.vpk').write_bytes(payload)
    return p,b''.join(chunks)


class RespawnArchive(unittest.TestCase):
    def test_external_localized_and_inline_multiple_chunks(self):
        for inline in (False,True):
            with tempfile.TemporaryDirectory() as root:
                p,expected=fixture(root,inline=inline)
                self.assertEqual(RespawnVPK(p).read('models/pilot.mdl'),expected)

    def test_decompress_callback_lengths_and_final_crc(self):
        with tempfile.TemporaryDirectory() as root:
            p,expected=fixture(root,compressed=True)
            self.assertEqual(RespawnVPK(p,lambda b,n:zlib.decompress(b)).read('models/pilot.mdl'),expected)
            with self.assertRaisesRegex(ValueError,'LZHAM'):RespawnVPK(p).read('models/pilot.mdl')
            with self.assertRaisesRegex(ValueError,'length'):RespawnVPK(p,lambda b,n:b'x').read('models/pilot.mdl')
            p,_=fixture(root,crc_delta=1)
            with self.assertRaisesRegex(ValueError,'CRC'):RespawnVPK(p).read('models/pilot.mdl')

    def test_malformed_paths_continuation_and_chunk_bounds(self):
        with tempfile.TemporaryDirectory() as root:
            for path in ('../pilot','/tmp/pilot','a/../../pilot','a/x:y','a/x\\y'):
                p,_=fixture(root,path=path)
                with self.assertRaisesRegex(ValueError,'Unsafe'):RespawnVPK(p)
            p,_=fixture(root,continuation=1)
            with self.assertRaisesRegex(ValueError,'continuation'):RespawnVPK(p)
            p,_=fixture(root)
            p.with_name('client_mp_test.bsp.pak000_000.vpk').write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'outside'):RespawnVPK(p).read('models/pilot.mdl')

    def test_header_and_tree_truncation(self):
        with tempfile.TemporaryDirectory() as root:
            p,_=fixture(root);original=p.read_bytes()
            for length in (0,15,len(original)-1):
                p.write_bytes(original[:length])
                with self.assertRaises(ValueError):RespawnVPK(p)
            data=bytearray(original);struct.pack_into('<H',data,6,2);p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'2.3'):RespawnVPK(p)
            data=bytearray(original);struct.pack_into('<I',data,12,1);p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'preload'):RespawnVPK(p)


if __name__=='__main__':unittest.main()
