"""Read selected local Valve VPK v1/v2 entries, with length and CRC checks.

No executables, scripts, network access, or writes to the source installation.
"""
import io
import struct
import zlib
from pathlib import Path, PurePosixPath


class VPK:
    def __init__(self, directory):
        self.path = Path(directory)
        self.entries = {}
        with self.path.open('rb') as source:
            signature, version, tree_size = struct.unpack('<III', source.read(12))
            if signature != 0x55AA1234 or version not in (1, 2):
                raise ValueError('Unsupported VPK signature/version')
            self.header_size = 12 if version == 1 else 28
            source.seek(self.header_size)
            if tree_size > 64 * 1024 * 1024:
                raise ValueError('VPK directory exceeds limit')
            raw = source.read(tree_size)
        if len(raw) != tree_size:
            raise ValueError('Truncated VPK tree')
        self.data_start = self.header_size + tree_size
        tree = io.BytesIO(raw)

        def string():
            out = bytearray()
            while True:
                b = tree.read(1)
                if not b:
                    raise ValueError('Truncated VPK name')
                if b == b'\0':
                    return out.decode('utf8')
                out += b
                if len(out) > 4096:
                    raise ValueError('VPK name exceeds limit')

        while extension := string():
            while folder := string():
                while name := string():
                    entry = tree.read(18)
                    if len(entry) != 18:
                        raise ValueError('Truncated VPK entry')
                    crc, preload, archive, offset, size, end = struct.unpack('<IHHIIH', entry)
                    if end != 65535 or size + preload > 256 * 1024 * 1024:
                        raise ValueError('Invalid VPK entry')
                    path = ('' if folder == ' ' else folder + '/') + name + ('' if extension == ' ' else '.' + extension)
                    if path.startswith('/') or '\\' in path or '..' in PurePosixPath(path).parts or path in self.entries:
                        raise ValueError('Unsafe or duplicate VPK entry')
                    data = tree.read(preload)
                    if len(data) != preload:
                        raise ValueError('Truncated VPK preload')
                    self.entries[path] = (crc, archive, offset, size, data)

    def read(self, path):
        crc, archive, offset, size, preload = self.entries[path]
        if archive == 0x7fff:
            source = self.path
            offset += self.data_start
        else:
            if not self.path.name.endswith('_dir.vpk'):
                raise ValueError('Expected a VPK directory filename')
            source = self.path.with_name(self.path.name[:-8] + f'_{archive:03d}.vpk')
        with source.open('rb') as f:
            f.seek(offset)
            data = preload + f.read(size)
        if len(data) != len(preload) + size or zlib.crc32(data) != crc:
            raise ValueError('VPK length/CRC mismatch: ' + path)
        return data
