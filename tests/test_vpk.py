import struct,tempfile,unittest,zlib
from pathlib import Path
from model_import.vpk import VPK


class VpkRead(unittest.TestCase):
    def fixture(self,root,path='models/test',internal=True,corrupt=False,version=2):
        payload=b'body-data';preload=b'header-';crc=zlib.crc32(preload+payload)
        tree=b'mdl\0'+path.rsplit('/',1)[0].encode()+b'\0'+path.rsplit('/',1)[1].encode()+b'\0'+struct.pack('<IHHIIH',crc,len(preload),0x7fff if internal else 0,0,len(payload),65535)+preload+b'\0\0\0'
        header=struct.pack('<III',0x55AA1234,version,len(tree))+(b'\0'*16 if version==2 else b'')
        directory=Path(root)/'fixture_dir.vpk';directory.write_bytes(header+tree+(payload if internal else b''))
        if not internal:directory.with_name('fixture_000.vpk').write_bytes(payload)
        if corrupt:
            target=directory if internal else directory.with_name('fixture_000.vpk');b=bytearray(target.read_bytes());b[-1]^=1;target.write_bytes(b)
        return directory,preload+payload

    def test_inline_and_external_preload_crc(self):
        for internal in (False,True):
            for version in (1,2):
                with tempfile.TemporaryDirectory() as d:
                    p,expected=self.fixture(d,internal=internal,version=version);self.assertEqual(VPK(p).read('models/test.mdl'),expected)

    def test_corrupt_archive_and_unsafe_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,_=self.fixture(d,corrupt=True)
            with self.assertRaisesRegex(ValueError,'CRC'):VPK(p).read('models/test.mdl')
            p,_=self.fixture(d,path='../test')
            with self.assertRaisesRegex(ValueError,'Unsafe'):VPK(p)

    def test_truncated_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,_=self.fixture(d);p.write_bytes(p.read_bytes()[:30])
            with self.assertRaises(ValueError):VPK(p)


if __name__=='__main__':unittest.main()
