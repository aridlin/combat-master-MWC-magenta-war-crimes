"""Read-only bundle index. Never loads game assemblies or inspects processes."""
import collections
import fnmatch
import gc
import json
from pathlib import Path

import UnityPy
from bundle_utils import digest

RENDERERS = {'SkinnedMeshRenderer', 'MeshRenderer', 'ParticleSystemRenderer', 'TrailRenderer', 'LineRenderer'}


def key(asset, path_id):
    return f'{Path(asset).name}:{path_id}'


def pointer(ptr, owner):
    if not ptr or not ptr.m_PathID:
        return None
    if ptr.m_FileID == 0:
        asset = owner.name
    elif 0 < ptr.m_FileID <= len(owner.externals):
        asset = owner.externals[ptr.m_FileID - 1].name
    else:
        return f'UNRESOLVED:{ptr.m_FileID}:{ptr.m_PathID}'
    return key(asset, ptr.m_PathID)


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.partial')
    tmp.write_text(json.dumps(data, indent=2) + '\n')
    tmp.replace(path)


def scan_one(path, relative):
    env = UnityPy.load(str(path))
    result = {'bundle': relative, 'source': str(path.resolve()), 'sha256': digest(path),
              'unity_version': env.file.version_engine, 'textures': [], 'materials': [],
              'renderers': [], 'meshes': [], 'unsupported': [], 'errors': []}
    names = {}
    counts = collections.Counter()
    for obj in env.objects:
        counts[obj.type.name] += 1
        if obj.type.name in ('GameObject', 'Mesh', 'Material', 'Texture2D', 'Shader', 'AnimationClip'):
            try:
                names[key(obj.assets_file.name, obj.path_id)] = obj.peek_name()
            except Exception:
                pass
    for obj in env.objects:
        kind = obj.type.name
        oid = key(obj.assets_file.name, obj.path_id)
        try:
            if kind == 'Texture2D':
                t = obj.read()
                result['textures'].append({'id': oid, 'name': t.m_Name,
                    'width': t.m_Width, 'height': t.m_Height, 'format': t.m_TextureFormat,
                    'mips': t.m_MipCount, 'color_space': t.m_ColorSpace,
                    'filter': t.m_TextureSettings.m_FilterMode,
                    'wrap': [t.m_TextureSettings.m_WrapU, t.m_TextureSettings.m_WrapV],
                    'readable': t.m_IsReadable})
            elif kind == 'Material':
                m = obj.read()
                result['materials'].append({'id': oid, 'name': m.m_Name,
                    'shader': pointer(m.m_Shader, obj.assets_file),
                    'keywords': getattr(m, 'm_ShaderKeywords', None),
                    'properties': [{'slot': slot, 'texture': pointer(x.m_Texture, obj.assets_file),
                        'scale': [x.m_Scale.x, x.m_Scale.y], 'offset': [x.m_Offset.x, x.m_Offset.y]}
                        for slot, x in m.m_SavedProperties.m_TexEnvs if x.m_Texture.m_PathID],
                    'floats': dict(m.m_SavedProperties.m_Floats)})
            elif kind in RENDERERS:
                r = obj.read()
                go = pointer(r.m_GameObject, obj.assets_file)
                mesh = pointer(getattr(r, 'm_Mesh', None), obj.assets_file)
                result['renderers'].append({'id': oid, 'type': kind, 'game_object': go,
                    'name': names.get(go, ''), 'mesh': mesh, 'mesh_name': names.get(mesh, ''),
                    'materials': [pointer(p, obj.assets_file) for p in r.m_Materials if p.m_PathID]})
            elif kind == 'Mesh':
                result['meshes'].append({'id': oid, 'name': names.get(oid, '')})
            elif kind in ('Texture2DArray', 'Cubemap', 'CubemapArray', 'Texture3D', 'RenderTexture'):
                result['unsupported'].append({'id': oid, 'type': kind})
        except Exception as exc:
            result['errors'].append({'id': oid, 'type': kind, 'error': str(exc)[:300]})
    result['object_counts'] = dict(counts)
    del env
    gc.collect()
    return result


def scan(config, report_dir):
    root = Path(config['bundle_root'])
    output = Path(report_dir) / 'scan'
    manifests = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not any(fnmatch.fnmatch(relative, pat) for pat in config['bundles']['include']):
            continue
        if any(fnmatch.fnmatch(relative, pat) for pat in config['bundles']['exclude']):
            continue
        source = Path(config.get('source_overrides', {}).get(relative, path))
        with source.open('rb') as stream:
            if stream.read(8) != b'UnityFS\0':
                continue
        dest = output / (relative.replace('/', '__') + '.json')
        if dest.exists():
            record = json.loads(dest.read_text())
            if record['sha256'] == digest(source) and record['source'] == str(source.resolve()):
                manifests.append(str(dest))
                print('Scan cached:', relative, flush=True)
                continue
        print('Scanning:', relative, flush=True)
        record = scan_one(source, relative)
        dump(dest, record)
        manifests.append(str(dest))
    dump(Path(report_dir) / 'scan-index.json', {'bundles': manifests})
    return manifests


def load_scan(report_dir):
    index = json.loads((Path(report_dir) / 'scan-index.json').read_text())
    return [json.loads(Path(p).read_text()) for p in index['bundles']]
