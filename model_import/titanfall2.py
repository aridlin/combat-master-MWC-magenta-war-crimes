"""Import real pilot geometry/color from an explicitly selected local TF2 install.

Here TF2 means Titanfall 2 (Steam 1237970), not Team Fortress 2 (440).
No EA/Respawn assets are distributed. No new redistribution rights are granted.
Decompression is supplied separately; no binaries are downloaded or auto-run.
"""
import hashlib
import json
from pathlib import Path
import re
import tempfile
import numpy as np
from PIL import Image
from .respawn_vpk import RespawnVPK
from .respawn_rpak import RPak7
from .source import load

MODELS = {
    'titanfall_grapple': ('pilot_medium_geist_m', 'pilot_grapple_male', 'Armored human Grapple pilot'),
    'titanfall_pulseblade_female': ('pilot_medium_reaper_f', 'pilot_medium_female', 'Female Pulse Blade pilot'),
}


def pack_source(data, images, output, metadata):
    """Keep authored vertices/material seams; avoid expanding every triangle.

    The existing native character atlas uses 512px material tiles. Temporary
    pixel arrays are bounded to that same size, rather than caching hundreds of
    megabytes of redundant full-resolution floats for each imported pilot.
    Original full-resolution mip hashes remain in the provenance record.
    """
    from operators.assets import prepare
    output = Path(output)
    used = sorted(set(map(int, data['face_materials'])))
    if set(images) != set(used):
        raise ValueError('Pilot material images do not match its visual meshes')
    if len(data['positions']) > 65535:
        raise ValueError('Pilot needs explicit uint16 mesh partitioning')
    assigned = np.full(len(data['positions']), -1)
    for number in used:
        vertices = np.unique(data['faces'][data['face_materials'] == number])
        if np.any(assigned[vertices] >= 0):
            raise ValueError('Pilot requires explicit material-boundary vertex splitting')
        assigned[vertices] = number
    if np.any(assigned < 0):
        raise ValueError('Pilot contains unreferenced vertices')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pilot-packing-', dir=output.parent) as temp:
        temp = Path(temp)
        materials = []
        for number in used:
            image = images[number].convert('RGBA').resize((512, 512), Image.Resampling.LANCZOS)
            filename = f'material-{number}.npy'
            np.save(temp / filename, np.flipud(np.asarray(image, dtype='<f4') / 255))
            materials.append(dict(index=number, name=data['textures'][number], pixels=filename,
                                  alpha_mode='opaque', base_color_linear=[1., 1., 1., 1.]))
        uv = data['uv'].copy()
        uv[:, 1] = 1 - uv[:, 1]
        arrays = {k: data[k] for k in ('positions', 'normals', 'faces', 'bone_indices',
                                      'bone_weights', 'inverse_bind', 'bone_parents')}
        arrays.update(uv=uv, face_materials=np.asarray([used.index(int(i)) for i in data['face_materials']], dtype='<i4'))
        np.savez_compressed(temp / 'source.npz', **arrays)
        meta = {**metadata, 'bone_names': data['bone_names'],
                'bone_parents': data['bone_parents'].tolist(), 'objects': data['parts'],
                'materials': materials, 'coordinate_system': 'y_up', 'texture_filter': 'linear',
                'native_material_tile_pixels': 512, 'vertices': len(data['positions']),
                'triangles': len(data['faces']), 'game_files_modified': False,
                'gameplay_data_imported': False, 'in_game_tested': False}
        (temp / 'source.json').write_text(json.dumps(meta, indent=2) + '\n')
        return prepare(temp, output, metadata['source'], 'titanfall2_native')


def import_models(game, decoded_rpak, output, *, decompress=None, names=None):
    """Produce compact, privately held sources compatible with operator builders.

    Requires an already decoded *base* common.rpak, explicit local installation,
    and optional bounded LZHAM callback. This performs no installation itself.
    """
    game, output = Path(game).resolve(), Path(output).resolve()
    if game == output or game in output.parents:
        raise ValueError('Pilot import output must be outside Titanfall 2')
    names = sorted(MODELS if names is None else names)
    if not names or set(names) - MODELS.keys():
        raise ValueError('Unknown or empty Titanfall pilot selection')
    if output.exists():
        raise ValueError('Use a fresh local pilot import directory')
    archive = game / 'vpk/englishclient_mp_common.bsp.pak000_dir.vpk'
    vpk = RespawnVPK(archive, decompress)
    starpak = game / 'r2/paks/Win64/pc_stream.starpak'
    report = []
    with RPak7(decoded_rpak, decoded=True) as rpak:
        for name in names:
            model, identity, title = MODELS[name]
            path = f'models/humans/pilots/{model}.mdl'
            identity_path = f'scripts/players/mp/{identity}.set'
            identity_bytes = vpk.read(identity_path)
            match = re.search(rb'\bbodymodel\s+"([^"\n]+)"', identity_bytes)
            if match is None or match[1].decode('ascii') != path:
                raise ValueError('Local pilot visual identity mapping changed: ' + identity_path)
            raw = vpk.read(path)
            data = load(raw)
            images, textures = {}, []
            for number in sorted(set(map(int, data['face_materials']))):
                texture = rpak.diffuse(data['textures'][number])
                image, record = rpak.texture_image(texture, starpak)
                images[number] = image
                textures.append(record)
            metadata = dict(id=name, title=title, author='Respawn Entertainment / Electronic Arts',
                            source='User local Titanfall 2 installation; Steam App 1237970',
                            redistribution='Local import only; no redistribution grant. Do not bundle game assets.',
                            source_model=model, source_sha256={path: hashlib.sha256(raw).hexdigest(),
                            identity_path: hashlib.sha256(identity_bytes).hexdigest()},
                            original_color_textures=textures)
            result = pack_source(data, images, output / name, metadata)
            report.append(dict(id=name, vertices=result['vertices'], triangles=result['triangles'],
                               textures=len(textures), in_game_tested=False, installed=False))
    return report
