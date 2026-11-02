"""Retexture verified BaseMap arrays, preserving decoded alpha at every mip."""
import gc
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image
import UnityPy
from UnityPy.export.Texture2DConverter import parse_image_data,image_to_texture2d
from UnityPy.helpers.ResourceReader import get_resource_data
from bundle_utils import digest,inventory
from .assets import key,dump
from .patterns import pattern,linear_mips


def data(array):
    if array.image_data: return bytes(array.image_data)
    stream=array.m_StreamData
    return get_resource_data(stream.path,array.object_reader.assets_file,stream.offset,stream.size)


def alpha_hash(image):
    return hashlib.sha256(image.convert('RGBA').getchannel('A').tobytes()).hexdigest()


def verify_array(array,record):
    if (array.m_Width,array.m_Height,array.m_Depth,array.m_MipCount,array.m_Format)!=(record['width'],record['height'],record['depth'],record['mips'],4):
        raise ValueError('Array dimensions/depth/mips/format mismatch')
    raw=data(array); stride=array.m_DataSize//array.m_Depth
    if len(raw)!=array.m_DataSize: raise ValueError('Array byte length mismatch')
    for layer in record['layers']:
        offset=layer['index']*stride
        for level,wanted in enumerate(layer['alpha_mip_sha256']):
            w,h=max(1,array.m_Width>>level),max(1,array.m_Height>>level)
            size=w*h*4
            image=parse_image_data(raw[offset:offset+size],w,h,4,array.object_reader.version,0,None)
            if alpha_hash(image)!=wanted: raise ValueError('Array alpha mismatch')
            offset+=size


def apply_arrays(config,mapping_path):
    report_dir=Path(config['paths']['reports']); manifest_path=report_dir/'modifications.json'
    manifest=json.loads(manifest_path.read_text()); mappings=json.loads(Path(mapping_path).read_text())
    for b in manifest['bundles']:
        selected=[x for x in mappings['arrays'] if x['bundle']==b['bundle']]
        if not selected or b.get('array_changes'): continue
        path=Path(b['output'])
        if digest(path)!=b['output_sha256']: raise ValueError('Staged output changed')
        env=UnityPy.load(str(path)); expected=inventory(env)
        by_id={key(o.assets_file.name,o.path_id):o for o in env.objects}; changes=[]
        for mapping in selected:
            obj=by_id[mapping['id']]; array=obj.read()
            if array.m_Format!=109: raise ValueError('Unsupported source array graphics format')
            original=data(array); stride=array.m_DataSize//array.m_Depth
            record={'id':mapping['id'],'name':array.m_Name,'width':array.m_Width,'height':array.m_Height,
                    'depth':array.m_Depth,'mips':array.m_MipCount,'source_format':109,'output_format':4,'layers':[]}
            chunks=[]
            for index in range(array.m_Depth):
                category=mapping['categories'][index]
                rgb,_=pattern(config['categories'][category]['color'],config['generation'])
                levels=list(linear_mips(rgb)); layer={'index':index,'category':category,'alpha_mip_sha256':[]}
                offset=index*stride
                for level in range(array.m_MipCount):
                    w,h=max(1,array.m_Width>>level),max(1,array.m_Height>>level)
                    size=max(1,(w+3)//4)*max(1,(h+3)//4)*16
                    old=parse_image_data(original[offset:offset+size],w,h,25,obj.version,0,None)
                    layer['alpha_mip_sha256'].append(alpha_hash(old))
                    tile=levels[min(level,len(levels)-1)]
                    pixels=np.tile(tile,(math.ceil(h/tile.shape[0]),math.ceil(w/tile.shape[1]),1))[:h,:w]
                    image=Image.fromarray(pixels).convert('RGBA'); image.putalpha(old.convert('RGBA').getchannel('A'))
                    encoded,_=image_to_texture2d(image,4)
                    chunks.append(encoded); offset+=size
                if offset!=(index+1)*stride: raise ValueError('Unexpected source array slice layout')
                record['layers'].append(layer)
            array.image_data=b''.join(chunks); array.m_Format=4; array.m_ColorSpace=1
            array.m_DataSize=len(array.image_data)
            array.m_StreamData.path=''; array.m_StreamData.offset=0; array.m_StreamData.size=0
            array.m_TextureSettings.m_FilterMode=2
            array.m_TextureSettings.m_WrapU=array.m_TextureSettings.m_WrapV=array.m_TextureSettings.m_WrapW=0
            verify_array(array,record); array.save()
            expected[(obj.assets_file.name,obj.path_id)]['sha256']=hashlib.sha256(obj.data).hexdigest()
            changes.append(record)
            print('Array recolored and all alpha mips verified:',array.m_Name,array.m_Depth,flush=True)
        temporary=path.with_name(path.name+'.arrays-partial')
        with temporary.open('wb') as stream: stream.write(env.file.save(packer='lz4'))
        del array,obj,env,by_id; gc.collect()
        checked=UnityPy.load(str(temporary)); actual=inventory(checked)
        if actual!=expected: raise ValueError('Array bundle serialized objects mismatch')
        by_id={key(o.assets_file.name,o.path_id):o for o in checked.objects}
        for change in changes: verify_array(by_id[change['id']].read(),change)
        del checked,by_id; gc.collect()
        temporary.replace(path)
        b['output_sha256']=digest(path); b['array_changes']=changes
        b['checks']['all_array_layer_alpha_mips_exact']=True
        b['checks']['array_layer_count_and_dimensions_preserved']=True
        dump(str(path)+'.verification.json',b); dump(manifest_path,manifest)
    return {'arrays':sum(len(b.get('array_changes',[])) for b in manifest['bundles']),
            'layers':sum(len(a['layers']) for b in manifest['bundles'] for a in b.get('array_changes',[])),
            'encoding_note':'BC7 arrays converted to lossless sRGB RGBA32 to preserve alpha exactly; increases VRAM/storage.'}
