"""Read-only Titanfall 2 VPK 2.3 directory and selected visual asset reader.

The chunk layout follows pg9182/tf2vpk (MIT), revision
b73c54d8e4245075ea207c7e51a2a86fdb94e4ff. See licenses/tf2vpk-MIT.txt.
Valve VPK v1/v2 remains handled separately by model_import.vpk.
No scripts, model events or game processes are executed or modified.
"""
from dataclasses import dataclass
import io
from pathlib import Path, PurePosixPath
import re
import struct
import zlib


@dataclass(frozen=True)
class Chunk:
    load_flags: int
    texture_flags: int
    offset: int
    packed_size: int
    size: int


@dataclass(frozen=True)
class Entry:
    crc32: int
    archive: int
    chunks: tuple

    @property
    def size(self):
        return sum(chunk.size for chunk in self.chunks)


def unpack(stream, fmt):
    size=struct.calcsize('<'+fmt)
    raw=stream.read(size)
    if len(raw)!=size:
        raise ValueError('Truncated Respawn VPK field')
    return struct.unpack('<'+fmt,raw)


def string(stream):
    raw=bytearray()
    while len(raw)<=4096:
        byte=stream.read(1)
        if not byte:
            raise ValueError('Truncated Respawn VPK name')
        if byte==b'\0':
            return raw.decode('utf8')
        raw.extend(byte)
    raise ValueError('Respawn VPK name exceeds limit')


class RespawnVPK:
    def __init__(self,directory,decompress=None):
        self.path=Path(directory)
        self.decompress=decompress
        self.entries={}
        # The localized directory name and nonlocalized payload name differ.
        match=re.fullmatch(r'[a-z]*?((?:client|server)_[A-Za-z0-9_.-]+)_dir\.vpk',self.path.name)
        if match is None:
            raise ValueError('Expected a localized Respawn VPK directory name')
        self.block_base=match[1]
        with self.path.open('rb') as source:
            magic,major,minor,tree_size,data_size=unpack(source,'IHHII')
            if (magic,major,minor)!=(0x55AA1234,2,3):
                raise ValueError('Expected Respawn VPK 2.3')
            if data_size!=0:
                raise ValueError('Respawn VPK preload data is unsupported')
            if not 0<tree_size<=64*1024*1024:
                raise ValueError('Respawn VPK directory exceeds limit')
            raw=source.read(tree_size)
        if len(raw)!=tree_size:
            raise ValueError('Truncated Respawn VPK directory')
        self.data_start=16+tree_size
        tree=io.BytesIO(raw)
        while extension:=string(tree):
            while folder:=string(tree):
                while name:=string(tree):
                    path=('' if folder==' ' else folder+'/')+name+('' if extension==' ' else '.'+extension)
                    parts=PurePosixPath(path).parts
                    if not path or path.startswith('/') or '\\' in path or '..' in parts or ':' in path or path in self.entries:
                        raise ValueError('Unsafe or duplicate Respawn VPK path')
                    crc,preload,archive=unpack(tree,'IHH')
                    if preload or archive==0xffff:
                        raise ValueError('Unsupported Respawn VPK preload or archive index')
                    chunks=[]
                    while True:
                        chunk=Chunk(*unpack(tree,'IHQQQ'))
                        if not 0<chunk.packed_size<=1024*1024 or not 0<chunk.size<=1024*1024:
                            raise ValueError('Respawn VPK chunk exceeds limit')
                        if chunks and (chunk.load_flags,chunk.texture_flags)!=(chunks[0].load_flags,chunks[0].texture_flags):
                            raise ValueError('Inconsistent Respawn VPK chunk flags')
                        chunks.append(chunk)
                        if len(chunks)>8192:
                            raise ValueError('Respawn VPK file has too many chunks')
                        end,=unpack(tree,'H')
                        if end==0xffff:
                            break
                        if end!=archive:
                            raise ValueError('Invalid Respawn VPK chunk continuation')
                    self.entries[path]=Entry(crc,archive,tuple(chunks))
                    if len(self.entries)>250000:
                        raise ValueError('Respawn VPK has too many files')
        if tree.tell()!=len(raw):
            raise ValueError('Respawn VPK directory has trailing data')

    def read(self,path):
        entry=self.entries[path]
        if entry.size>256*1024*1024:
            raise ValueError('Selected Respawn VPK asset exceeds read limit')
        source=self.path if entry.archive==0x7fff else self.path.with_name(self.block_base+f'_{entry.archive:03d}.vpk')
        chunks=[]
        with source.open('rb') as stream:
            stream.seek(0,2)
            file_size=stream.tell()
            for chunk in entry.chunks:
                offset=chunk.offset+(self.data_start if entry.archive==0x7fff else 0)
                if offset+chunk.packed_size>file_size:
                    raise ValueError('Respawn VPK chunk outside payload')
                stream.seek(offset)
                data=stream.read(chunk.packed_size)
                if len(data)!=chunk.packed_size:
                    raise ValueError('Truncated Respawn VPK chunk')
                if chunk.packed_size!=chunk.size:
                    if self.decompress is None:
                        raise ValueError('Compressed Respawn VPK assets require an LZHAM decoder')
                    data=self.decompress(data,chunk.size)
                if len(data)!=chunk.size:
                    raise ValueError('Respawn VPK decompressed length mismatch')
                chunks.append(data)
        data=b''.join(chunks)
        if len(data)!=entry.size or zlib.crc32(data)!=entry.crc32:
            raise ValueError('Respawn VPK asset length/CRC mismatch: '+path)
        return data
