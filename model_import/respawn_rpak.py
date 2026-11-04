"""Read-only base RPak7 visual index and original 2D diffuse mip extraction.

Original Python implementation of disk layout facts documented in r-ex/rsx
18cd364421c883d475a78643e3796caf19204355 cpakfile.h, texture.h and material.h.
No shader bytecode, game scripts, asset patch operations or process access.
Compressed RPaks must be explicitly decoded by a separate reviewed tool first.
No proprietary content or decompressor implementation is included here.
"""
from pathlib import Path
import hashlib
import mmap
import struct


class RPak7:
    def __init__(self, path, *, decoded=False):
        self.file = Path(path).open('rb')
        self.data = None
        try:
            size = self.file.seek(0, 2)
            if not 88 <= size <= 512 * 1024 * 1024:
                raise ValueError('RPak file exceeds supported size bounds')
            self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
            self._index(decoded)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.data is not None:
            self.data.close()
            self.data = None
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def unpack(self, fmt, offset):
        if offset < 0 or offset + struct.calcsize('<' + fmt) > len(self.data):
            raise ValueError('RPak field outside file')
        return struct.unpack_from('<' + fmt, self.data, offset)

    def pointer(self, offset, size=1):
        page, at = self.unpack('II', offset)
        if size < 0 or page >= len(self.pages) or at + size > self.pages[page][2]:
            raise ValueError('RPak pointer outside page')
        return self.starts[page] + at

    def pointer_string(self, offset):
        page, at = self.unpack('II', offset)
        start = self.pointer(offset)
        end = self.data.find(b'\0', start, min(self.starts[page] + self.pages[page][2], start + 4096))
        if end < 0:
            raise ValueError('Unterminated RPak name')
        return self.data[start:end].decode('utf8')

    def _index(self, decoded):
        b = self.data
        if b[:4] != b'RPak' or self.unpack('H', 4)[0] != 7:
            raise ValueError('Expected RPak7')
        flags = self.unpack('H', 6)[0]
        packed, size = self.unpack('Q', 24)[0], self.unpack('Q', 40)[0]
        if size != len(b) or (flags & 0xff00 and not decoded) or (not decoded and packed != size):
            raise ValueError('Expected an uncompressed or explicitly decoded RPak')
        streaming, segments, pages, patch, *counts = self.unpack('4H6I', 56)
        if patch:
            raise ValueError('RPak patch composition is unsupported')
        if not 0 < segments <= 8192 or not 0 < pages <= 65535 or counts[1] > 200000 or max(counts) > 4000000:
            raise ValueError('RPak index limits exceeded')
        if 88 + streaming > len(b):
            raise ValueError('RPak streaming names outside file')
        self.streams = [s.decode('ascii') for s in b[88:88 + streaming].split(b'\0') if s]
        base = 88 + streaming + 16 * segments
        self.pages = [self.unpack('3I', base + i * 12) for i in range(pages)]
        assets = base + pages * 12 + counts[0] * 8
        start = assets + 72 * counts[1] + counts[2] * 8 + counts[3] * 4 + counts[4] * 4 + counts[5]
        self.starts = []
        position = start
        for segment, alignment, page_size in self.pages:
            if segment >= segments or not alignment or alignment & (alignment - 1):
                raise ValueError('Invalid RPak page segment/alignment')
            self.starts.append(position)
            position += page_size
        if position != len(b):
            raise ValueError('RPak page extents mismatch')
        self.assets, self.names = {}, {}
        for i in range(counts[1]):
            a = assets + i * 72
            guid, = self.unpack('Q', a)
            version, = self.unpack('I', a + 64)
            kind = b[a + 68:a + 72].decode('ascii')
            header_size = self.unpack('I', a + 60)[0]
            h = self.pointer(a + 16, header_size)
            entry = dict(guid=guid, kind=kind, version=version, header=h,
                         data_pointer=a + 24, stream=self.unpack('Q', a + 32)[0])
            if guid in self.assets:
                raise ValueError('Duplicate RPak asset GUID')
            self.assets[guid] = entry
            if kind in ('txtr', 'matl'):
                expected = 8 if kind == 'txtr' else 12
                if version != expected:
                    raise ValueError('Unsupported RPak visual asset version')
                if header_size != (56 if kind == 'txtr' else 208):
                    raise ValueError('Unexpected RPak visual header size')
                if self.unpack('Q', h + (0 if kind == 'txtr' else 16))[0] != guid:
                    raise ValueError('RPak visual header GUID mismatch')
                name = self.pointer_string(h + (8 if kind == 'txtr' else 24))
                entry['name'] = name
                # Several material shader variants can legitimately share names.
                self.names.setdefault((kind, name.replace('\\', '/').lower()), []).append(entry)

    def material_textures(self, entry):
        if entry['kind'] != 'matl' or entry['version'] != 12:
            raise ValueError('Expected material v12')
        h = entry['header']
        page, offset = self.unpack('II', h + 152)
        end_page, end_offset = self.unpack('II', h + 160)
        length = end_offset - offset
        if page != end_page or not 0 <= length <= 1024 or length % 8:
            raise ValueError('RPak texture table bounds')
        start = self.pointer(h + 152, length)
        return list(self.unpack('Q' * (length // 8), start))

    def diffuse(self, name):
        """Resolve the authored albedo slot; fail on conflicting shader variants."""
        entries = self.names.get(('matl', name.replace('\\', '/').lower()), [])
        references = {refs[0] for entry in entries if (refs := self.material_textures(entry)) and refs[0]}
        if len(references) != 1:
            raise ValueError('Missing or ambiguous material albedo: ' + name)
        texture = self.assets.get(references.pop())
        if not texture or texture['kind'] != 'txtr' or not texture['name'].endswith('_col'):
            raise ValueError('Material albedo does not resolve to an original color texture')
        return texture

    def texture_image(self, entry, starpak=None):
        from PIL import Image
        import texture2ddecoder
        if entry['kind'] != 'txtr' or entry['version'] != 8:
            raise ValueError('Expected texture v8')
        h = entry['header']
        width, height, depth, fmt = self.unpack('4H', h + 16)
        opt, array, layers, usage, permanent, streamed = self.unpack('6B', h + 29)
        if not 1 <= width <= 8192 or not 1 <= height <= 8192 or depth not in (0, 1) or opt or array not in (0, 1) or layers or not 1 <= permanent + streamed <= 14:
            raise ValueError('Unsupported RPak texture dimensions/layout')
        if fmt not in (0, 1, 4, 5, 12, 13):
            raise ValueError('Unsupported RPak diffuse format')
        block = 8 if fmt in (0, 1) else 16
        def mip_size(level):
            return max(1, ((width >> level) + 3) // 4) * max(1, ((height >> level) + 3) // 4) * block
        if streamed:
            encoded = entry['stream']
            index, start = encoded & 0xfff, encoded & ~0xfff
            if starpak is None or index != 0 or len(self.streams) != 1 or Path(starpak).name != self.streams[0].replace('\\', '/').split('/')[-1]:
                raise ValueError('Expected explicitly selected Starpak source')
            with Path(starpak).open('rb') as f:
                if f.read(8) != b'SRPk\x01\0\0\0':
                    raise ValueError('Unexpected Starpak header')
                file_size = f.seek(0, 2)
                if file_size < 16:
                    raise ValueError('Truncated Starpak')
                f.seek(-8, 2)
                count, = struct.unpack('<Q', f.read(8))
                table_start = file_size - 8 - count * 16
                if not 0 < count <= 1000000 or table_start < 8:
                    raise ValueError('Starpak table bounds')
                f.seek(table_start)
                records = list(struct.iter_unpack('<QQ', f.read(count * 16)))
                table = dict(records)
                if len(table) != len(records) or start not in table or start < 4096 or start + table[start] > table_start:
                    raise ValueError('Texture absent from valid Starpak directory')
                offset = sum((mip_size(level) + 15) & ~15 for level in range(streamed - 1, 0, -1))
                if offset + mip_size(0) > table[start]:
                    raise ValueError('Texture mip outside Starpak entry')
                f.seek(start + offset)
                raw = f.read(mip_size(0))
            source = 'starpak'
        else:
            offset = sum((mip_size(level) + 15) & ~15 for level in range(permanent - 1, 0, -1))
            start = self.pointer(entry['data_pointer'], offset + mip_size(0))
            raw = self.data[start + offset:start + offset + mip_size(0)]
            source = 'rpak'
        if len(raw) != mip_size(0):
            raise ValueError('Truncated RPak texture mip')
        decoder = texture2ddecoder.decode_bc1 if fmt in (0, 1) else texture2ddecoder.decode_bc3 if fmt in (4, 5) else texture2ddecoder.decode_bc7
        image = Image.frombytes('RGBA', (width, height), decoder(raw, width, height), 'raw', 'BGRA')
        return image, dict(guid=f'{entry["guid"]:016x}', name=entry['name'], width=width,
                          height=height, format=fmt, source=source, mip_bytes=len(raw),
                          mip_sha256=hashlib.sha256(raw).hexdigest())
