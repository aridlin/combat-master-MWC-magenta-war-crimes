"""Source MDL48 and embedded Titanfall 2 MDL53 LOD0 visual reader.

Read data only. Includes authored materials and skin influences; no Lua/MEL,
animation events, hitboxes, physics, gameplay scripts, or process access.
"""
import struct
import numpy as np
from catgun.source_model import VERTEX


class Binary:
    def __init__(self, data): self.data = data
    def unpack(self, fmt, offset):
        if offset < 0 or offset + struct.calcsize('<' + fmt) > len(self.data):
            raise ValueError('Source field outside file')
        return struct.unpack_from('<' + fmt, self.data, offset)
    def ints(self, offset, count=1): return self.unpack('i' * count, offset)
    def string(self, offset):
        if not 0 <= offset < len(self.data): raise ValueError('String outside Source file')
        end = self.data.find(b'\0', offset, offset + 4096)
        if end < 0: raise ValueError('Unterminated Source string')
        return self.data[offset:end].decode('utf8')


def load(mdl_data, vvd_data=None, vtx_data=None):
    """Read MDL48 triplets or a self-contained Titanfall 2 MDL53.

    MDL53 layout facts were checked against r-ex/rsx studio_r2.h and
    optimize.h (18cd364421c883d475a78643e3796caf19204355). No exporter
    implementation is embedded here. Only LOD0 visual geometry is read.
    """
    version = Binary(mdl_data).ints(4)[0]
    respawn = version == 53
    if respawn:
        if vvd_data is not None or vtx_data is not None:
            raise ValueError('MDL53 requires its embedded vertex data')
        header = Binary(mdl_data)
        if mdl_data[:4] != b'IDST' or header.ints(80)[0] != len(mdl_data):
            raise ValueError('Invalid MDL53 signature or file length')
        offsets = header.ints(428, 4)
        sizes = header.ints(444, 4)
        blocks = []
        for offset, size in zip(offsets, sizes):
            if size < 0 or (size and (offset < 952 or offset + size > len(mdl_data))):
                raise ValueError('MDL53 embedded block outside file')
            if size:
                if any(offset < end and start < offset + size for start, end in blocks):
                    raise ValueError('MDL53 embedded blocks overlap')
                blocks.append((offset, offset + size))
        if not sizes[0] or not sizes[1]:
            raise ValueError('MDL53 lacks embedded VTX/VVD')
        vtx_data = mdl_data[offsets[0]:offsets[0]+sizes[0]]
        vvd_data = mdl_data[offsets[1]:offsets[1]+sizes[1]]
    elif version != 48 or vvd_data is None or vtx_data is None:
        raise ValueError('Expected MDL48 triplet or embedded MDL53')
    shift = 4 if respawn else 0
    bone_stride, bind_offset = (244, 120) if respawn else (216, 96)
    texture_stride = 44 if respawn else 64
    group_stride, strip_stride = (33, 35) if respawn else (25, 27)
    mdl, vvd, vtx = map(Binary, (mdl_data, vvd_data, vtx_data))
    if mdl_data[:4] != b'IDST' or vvd_data[:4] != b'IDSV' or vvd.ints(4)[0] != 4 or vtx.ints(0)[0] != 7:
        raise ValueError('Expected MDL with VVD4/VTX7')
    if mdl.ints(8) != vvd.ints(8) or mdl.ints(8) != vtx.ints(16):
        raise ValueError('Source model checksums disagree')
    count = vvd.ints(16)[0]
    fix_count, fix_offset, vertex_offset, _ = vvd.ints(48, 4)
    if not 0 < count < 1000000: raise ValueError('Invalid Source vertex count')
    if fix_count:
        ranges = [vvd.ints(fix_offset + n * 12, 3) for n in range(fix_count)]
        if any(lod < 0 or start < 0 or size < 0 or start + size > count for lod, start, size in ranges):
            raise ValueError('Invalid Source fixup')
        remap = np.concatenate([np.arange(start, start + size) for lod, start, size in ranges])
        if len(remap) != count: raise ValueError('LOD0 fixup size mismatch')
    else: remap = np.arange(count)
    if vertex_offset < 0 or vertex_offset + count * 48 > len(vvd_data): raise ValueError('Truncated VVD vertices')
    vertices = np.frombuffer(vvd_data, VERTEX, count, vertex_offset)[remap]
    body_count, body_offset = mdl.ints(232 + shift, 2)
    xb_count, xb_offset = vtx.ints(28, 2)
    if not 0 < body_count <= 128 or xb_count != body_count: raise ValueError('MDL/VTX body mismatch')
    faces, materials, parts = [], [], []
    for b in range(body_count):
        bp = body_offset + b * 16
        _, model_count, _, model_offset = mdl.ints(bp, 4)
        xb = xb_offset + b * 8
        xm_count, xm_offset = vtx.ints(xb, 2)
        if xm_count != model_count or not 0 < model_count < 256: raise ValueError('MDL/VTX model mismatch')
        # Bodygroup choice zero only. Alternatives are not superimposed.
        model = bp + model_offset
        nm, mo, nv, vi = mdl.ints(model + 72, 4)
        if nm == 0: continue
        if vi % 48: raise ValueError('Unaligned model vertex offset')
        xm = xb + xm_offset
        nl, lo = vtx.ints(xm, 2)
        if not 1 <= nl <= 8: raise ValueError('Invalid Source LOD count')
        lod = xm + lo
        nxm, mxo = vtx.ints(lod, 2)
        if nxm != nm or not 0 < nm < 1024: raise ValueError('MDL/VTX mesh mismatch')
        first = len(faces)
        for m in range(nm):
            mesh = model + mo + m * 116
            material, _, mesh_nv, mesh_vo = mdl.ints(mesh, 4)
            xmsh = lod + mxo + m * 9
            ng, go = vtx.ints(xmsh, 2)
            if not 0 <= ng <= 1024: raise ValueError('Invalid strip group count')
            for g in range(ng):
                group = xmsh + go + g * group_stride
                gn, gv, ni, io, ns, so = vtx.ints(group, 6)
                if not 0 < gn <= 65536 or not 0 <= ni <= 1000000 or not 0 <= ns <= 65536: raise ValueError('Invalid strip group sizes')
                mapping = np.array([vtx.unpack('H', group + gv + j * 9 + 4)[0] for j in range(gn)])
                if np.any(mapping >= mesh_nv): raise ValueError('VTX vertex outside MDL mesh')
                mapping += vi // 48 + mesh_vo
                if np.any(mapping >= count): raise ValueError('VTX vertex outside VVD')
                indices = vtx.unpack('H' * ni, group + io)
                for s in range(ns):
                    strip = group + so + s * strip_stride
                    sn, si, sv, vo, bones, flags, changes, change_offset = vtx.unpack('4ihB2i', strip)
                    if si < 0 or sn < 0 or si + sn > ni: raise ValueError('Invalid Source strip range')
                    idx = np.asarray(indices[si:si + sn], dtype=int)
                    if np.any(idx >= gn): raise ValueError('Source strip index outside group')
                    ids = mapping[idx]
                    if flags == 1:
                        if sn % 3: raise ValueError('Invalid Source triangle list')
                        triangles = ids.reshape(-1, 3)
                    elif flags == 2 and not respawn:
                        triangles = np.asarray([(ids[k+1], ids[k], ids[k+2]) if k % 2 else (ids[k], ids[k+1], ids[k+2]) for k in range(sn - 2)], dtype=int).reshape(-1, 3)
                    else: raise ValueError('Unknown Source strip topology')
                    for tri in triangles:
                        if len(set(tri)) == 3: faces.append(tri); materials.append(material)
        parts.append({'name': mdl.string(model), 'first_face': first, 'face_count': len(faces) - first})
    # Source VTX triangles use clockwise front faces. The shared asset format,
    # Blender and the Unity mesh writer use counter-clockwise winding relative
    # to the authored outward normals. Convert once before any mirrored fitting.
    faces = np.asarray(faces, dtype='<u4').reshape(-1, 3)[:,[0,2,1]]
    if not len(faces): raise ValueError('Source model has no visible triangles')
    used, inverse = np.unique(faces, return_inverse=True)
    vertices = vertices[used]
    if not np.isfinite(vertices['pos']).all() or not np.isfinite(vertices['normal']).all(): raise ValueError('Nonfinite Source geometry')
    texture_count, texture_offset = mdl.ints(204 + shift, 2)
    dir_count, dir_offset = mdl.ints(212 + shift, 2)
    if not 0 <= texture_count <= 1024 or not 0 <= dir_count <= 128: raise ValueError('Invalid material directory')
    textures = [mdl.string(texture_offset + i * texture_stride + mdl.ints(texture_offset + i * texture_stride)[0]) for i in range(texture_count)]
    dirs = [mdl.string(mdl.ints(dir_offset + i * 4)[0]) for i in range(dir_count)]
    skin_count, family_count, skin_offset = mdl.ints(220 + shift, 3)
    if not 0 < skin_count <= 1024 or not 0 < family_count <= 4096:
        raise ValueError('Invalid Source skin table')
    skin = mdl.unpack('H' * skin_count, skin_offset)
    materials = np.asarray(materials, dtype=int)
    if materials.min() < 0 or materials.max() >= len(skin): raise ValueError('Material outside skin table')
    materials = np.asarray(skin, dtype=int)[materials]
    if materials.max() >= len(textures): raise ValueError('Skin material outside texture table')
    bone_count, bone_offset = mdl.ints(156 + shift, 2)
    if not 0 < bone_count <= 256: raise ValueError('Invalid Source bone count')
    bone_names = [mdl.string(bone_offset + i * bone_stride + mdl.ints(bone_offset + i * bone_stride)[0]) for i in range(bone_count)]
    bone_parents=np.asarray([mdl.ints(bone_offset+i*bone_stride+4)[0] for i in range(bone_count)],dtype='<i4')
    if np.any(bone_parents < -1) or np.any(bone_parents >= bone_count):raise ValueError('Invalid Source bone parent')
    inverse_bind = np.repeat(np.eye(4)[None], bone_count, axis=0)
    for i in range(bone_count): inverse_bind[i,:3] = np.asarray(mdl.unpack('12f', bone_offset + i * bone_stride + bind_offset)).reshape(3,4)
    if not np.isfinite(inverse_bind).all() or np.any(np.abs(np.linalg.det(inverse_bind[:,:3,:3])) < .1): raise ValueError('Invalid Source inverse bind matrices')
    weights = vertices['weights'].copy(); indices = vertices['bones'].copy()
    if np.any(indices >= bone_count) or not np.isfinite(weights).all() or np.any(weights < 0) or not np.allclose(weights.sum(axis=1), 1, atol=1e-4): raise ValueError('Invalid Source skin influences')
    return dict(positions=vertices['pos'].copy(), normals=vertices['normal'].copy(), uv=vertices['uv'].copy(), faces=inverse.reshape(-1, 3).astype('<u4'), face_materials=materials, bone_indices=indices, bone_weights=weights, inverse_bind=inverse_bind.astype('<f4'), bone_parents=bone_parents, bone_names=bone_names, textures=textures, material_dirs=dirs, parts=parts)
