"""Decode a VTF's first frame, largest mip. Never interpret shader code."""
import struct
from PIL import Image
import texture2ddecoder


def image(data):
    if data[:4] != b'VTF\0': raise ValueError('Invalid VTF signature')
    major, minor, header = struct.unpack_from('<III', data, 4)
    if major != 7 or not 2 <= minor <= 5: raise ValueError('Unsupported VTF version')
    w, h, flags, frames = struct.unpack_from('<HHIH', data, 16)
    fmt = struct.unpack_from('<I', data, 52)[0]
    mips = data[56]
    lowfmt, loww, lowh = struct.unpack_from('<IBB', data, 57)
    depth = struct.unpack_from('<H', data, 63)[0]
    if not 0 < w <= 8192 or not 0 < h <= 8192 or depth != 1 or frames != 1 or flags & 0x4000 or not 1 <= mips <= 14:
        raise ValueError('Expected a bounded single-frame 2D VTF')

    def size(x, y, f):
        if f in (13, 14, 15): return max(1, (x + 3) // 4) * max(1, (y + 3) // 4) * (8 if f == 13 else 16)
        if f in (0, 12, 16): return x * y * 4
        if f in (2, 3): return x * y * 3
        raise ValueError('Unsupported VTF image format: ' + str(f))

    offset = header + (size(loww, lowh, lowfmt) if loww and lowh else 0)
    if minor >= 3:
        count = struct.unpack_from('<I', data, 68)[0]
        if count > 32 or 80 + count * 8 > header: raise ValueError('Invalid VTF resource table')
        for n in range(count):
            entry = 80 + n * 8
            if data[entry:entry + 3] == b'\x30\0\0':
                if data[entry + 3] & 2: raise ValueError('Inline high-resolution VTF image')
                offset = struct.unpack_from('<I', data, entry + 4)[0]
                break
        else: raise ValueError('Missing VTF image resource')
    offset += sum(size(max(1, w >> level), max(1, h >> level), fmt) for level in range(1, mips))
    raw = data[offset:offset + size(w, h, fmt)]
    if len(raw) != size(w, h, fmt): raise ValueError('Truncated VTF mip')
    if fmt == 14: raise ValueError('DXT3 decoding is not implemented')
    if fmt in (13, 15):
        decoder = texture2ddecoder.decode_bc1 if fmt == 13 else texture2ddecoder.decode_bc3
        return Image.frombytes('RGBA', (w, h), decoder(raw, w, h), 'raw', 'BGRA')
    return Image.frombytes('RGBA' if fmt in (0, 12, 16) else 'RGB', (w, h), raw, 'raw', {0:'RGBA', 12:'BGRA', 16:'BGRX', 2:'RGB', 3:'BGR'}[fmt]).convert('RGBA')
