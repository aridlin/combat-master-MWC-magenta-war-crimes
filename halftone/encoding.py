"""DXT color replacement with original base-level alpha and full mip chains."""
import functools
import hashlib
import math
import numpy as np
from PIL import Image
import texture2ddecoder
from UnityPy.export.Texture2DConverter import image_to_texture2d
from .patterns import pattern, linear_mips


def apply_lossless_pattern(texture,color,settings):
    """Handle native RGB/RGBA/BC7 and small swatches without alpha loss."""
    from UnityPy.export.Texture2DConverter import parse_image_data
    old_fmt=texture.m_TextureFormat
    original=texture.image.convert('RGBA'); original_size=original.size
    alpha=original.getchannel('A'); source_alpha_hash=alpha_hash(original)
    promoted=min(original_size)<32
    width,height=(settings['size'],settings['size']) if promoted else original_size
    base_alpha=alpha.resize((width,height),Image.Resampling.NEAREST) if promoted else alpha
    if promoted and base_alpha.resize(original_size,Image.Resampling.NEAREST).tobytes()!=alpha.tobytes():
        raise ValueError('Small-texture promotion changes normalized alpha')
    pixels,_=pattern(color,settings); levels=list(linear_mips(pixels))
    source=bytes(texture.get_image_data()); offset=0; chunks=[]
    count=max(width,height).bit_length()
    for level in range(count):
        w,h=max(1,width>>level),max(1,height>>level)
        mip_alpha=base_alpha.resize((w,h),Image.Resampling.BOX)
        if not promoted and level<texture.m_MipCount:
            size=(max(1,(w+3)//4)*max(1,(h+3)//4)*16 if old_fmt==25 else w*h*(3 if old_fmt==3 else 4))
            if offset+size<=len(source):
                old=parse_image_data(source[offset:offset+size],w,h,old_fmt,texture.object_reader.version,0,None)
                mip_alpha=old.convert('RGBA').getchannel('A')
            offset+=size
        tile=levels[min(level,len(levels)-1)]
        rgb=np.tile(tile,(math.ceil(h/tile.shape[0]),math.ceil(w/tile.shape[1]),1))[:h,:w]
        image=Image.fromarray(rgb).convert('RGBA'); image.putalpha(mip_alpha)
        encoded,_=image_to_texture2d(image,4); chunks.append(encoded)
    texture.image_data=b''.join(chunks); texture.m_TextureFormat=4
    texture.m_Width=width; texture.m_Height=height; texture.m_MipCount=count
    texture.m_CompleteImageSize=len(texture.image_data)
    if texture.m_MipMap is not None: texture.m_MipMap=count>1
    if texture.m_StreamData is not None:
        texture.m_StreamData.path=''; texture.m_StreamData.offset=0; texture.m_StreamData.size=0
    texture.m_TextureSettings.m_FilterMode=2
    texture.m_TextureSettings.m_WrapU=texture.m_TextureSettings.m_WrapV=texture.m_TextureSettings.m_WrapW=0
    if texture.m_TextureSettings.m_WrapMode is not None: texture.m_TextureSettings.m_WrapMode=0
    texture.m_ColorSpace=1
    output=texture.image
    expected_hash=hashlib.sha256(base_alpha.tobytes()).hexdigest()
    if alpha_hash(output)!=expected_hash: raise ValueError('Lossless output alpha changed')
    texture.save()
    return {'alpha_sha256':expected_hash,'original_alpha_sha256':source_alpha_hash,
            'original_dimensions':list(original_size),'dimensions_promoted':promoted,
            'normalized_alpha_preserved':True,'width':width,'height':height,'format':4,'mips':count,
            'encoding_note':'Lossless RGBA32; small swatches promoted with nearest alpha, other dimensions retained.'}


def alpha_hash(image):
    return hashlib.sha256(image.convert('RGBA').getchannel('A').tobytes()).hexdigest()


@functools.lru_cache(maxsize=256)
def color_tile(color, settings_json, mip, fmt):
    import json
    settings = json.loads(settings_json)
    pixels, _ = pattern(color, settings)
    levels = list(linear_mips(pixels))
    array = levels[min(mip, len(levels)-1)]
    image = Image.fromarray(array).convert('RGBA')
    # Texture rows must match UnityPy's image export/import vertical orientation.
    data, _ = image_to_texture2d(image, fmt)
    bh, bw = max(1, (image.height+3)//4), max(1, (image.width+3)//4)
    return np.frombuffer(data, dtype=np.uint8).reshape(bh,bw,8 if fmt==10 else 16).copy()


def tiled_blocks(color, settings_json, mip, fmt, width, height):
    tile = color_tile(color, settings_json, mip, fmt)
    bh,bw = max(1,(height+3)//4),max(1,(width+3)//4)
    return np.tile(tile, (math.ceil(bh/tile.shape[0]),math.ceil(bw/tile.shape[1]),1))[:bh,:bw].reshape(-1,tile.shape[-1]).copy()


def dxt1_alpha(blocks):
    """Convert original 1-bit DXT1 alpha to exact DXT5 alpha blocks."""
    words = np.ascontiguousarray(blocks).view('<u4').reshape(-1,2)
    c0,c1 = words[:,0]&65535, words[:,0]>>16
    indices = words[:,1]
    alpha = np.full(len(blocks),255,dtype='<u8')
    for i in range(16):
        transparent = ((c0<=c1)&(((indices>>(2*i))&3)==3)).astype(np.uint64)
        alpha |= transparent << (16+3*i)
    return alpha.view(np.uint8).reshape(-1,8)


def apply_pattern(texture, color, settings):
    import json
    fmt = texture.m_TextureFormat
    if fmt in (3,4,25) or min(texture.m_Width,texture.m_Height)<32:
        return apply_lossless_pattern(texture,color,settings)
    if fmt not in (10,12,28,29):
        raise ValueError(f'Unsupported color encoding {fmt}')
    original_image = texture.image.convert('RGBA')
    original_alpha_hash = alpha_hash(original_image)
    raw = bytes(texture.get_image_data())
    crunched = fmt in (28,29)
    if crunched:
        raw = texture2ddecoder.unpack_unity_crunch(raw)
    source_block_size = 8 if fmt in (10,28) else 16
    # Retain DXT1 for fully opaque maps. Promote cutout maps to DXT5 to
    # preserve alpha independently of the halftone color endpoints.
    output_fmt = 10 if fmt in (10,28) and original_image.getchannel('A').getextrema()==(255,255) else 12
    settings_json = json.dumps(settings,sort_keys=True)
    width,height=texture.m_Width,texture.m_Height
    mip_count = max(width,height).bit_length()
    offset=0
    chunks=[]
    alpha_image=original_image.getchannel('A')
    for level in range(mip_count):
        w,h=max(1,width>>level),max(1,height>>level)
        n=max(1,(w+3)//4)*max(1,(h+3)//4)
        encoded=tiled_blocks(color,settings_json,level,output_fmt,w,h)
        if output_fmt==12:
            available=not crunched or level==0
            if available and offset+n*source_block_size <= len(raw):
                source=np.frombuffer(raw[offset:offset+n*source_block_size],dtype=np.uint8).reshape(n,source_block_size)
                encoded[:,:8]=source[:,:8] if source_block_size==16 else dxt1_alpha(source)
            else:
                alpha=alpha_image.resize((w,h),Image.Resampling.BOX)
                rgba=Image.new('RGBA',(w,h),(255,255,255,255)); rgba.putalpha(alpha)
                packed,_=image_to_texture2d(rgba,12)
                encoded[:,:8]=np.frombuffer(packed,dtype=np.uint8).reshape(n,16)[:,:8]
        chunks.append(encoded.tobytes())
        offset+=n*source_block_size
    texture.image_data=b''.join(chunks)
    texture.m_TextureFormat=output_fmt
    texture.m_CompleteImageSize=len(texture.image_data)
    texture.m_MipCount=mip_count
    if texture.m_MipMap is not None:
        texture.m_MipMap=mip_count>1
    if texture.m_StreamData is not None:
        texture.m_StreamData.path=''; texture.m_StreamData.offset=0; texture.m_StreamData.size=0
    texture.m_TextureSettings.m_FilterMode=2
    texture.m_TextureSettings.m_WrapU=texture.m_TextureSettings.m_WrapV=0
    texture.m_TextureSettings.m_WrapW=0
    if texture.m_TextureSettings.m_WrapMode is not None:
        texture.m_TextureSettings.m_WrapMode=0
    # 1 is Unity's serialized sRGB Texture2D color-space flag, confirmed in
    # original Albedo objects; noncolor maps in this build use 0.
    texture.m_ColorSpace=1
    if alpha_hash(texture.image) != original_alpha_hash:
        raise ValueError(f'Alpha changed: {texture.m_Name}')
    texture.save()
    return {'alpha_sha256': original_alpha_hash,'format':output_fmt,'mips':mip_count,
            'width':width,'height':height,'crunch_mips_regenerated':crunched,
            'pattern_origin': 'periodic source, dimensions retained; UV/material tiling unchanged'}
