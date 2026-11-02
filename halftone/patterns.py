"""Exact deterministic two-color source images and linear-light mipmaps."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def colors(hex_color, blend):
    text = hex_color.lstrip('#')
    base = np.array([int(text[i:i+2], 16) for i in (0, 2, 4)], dtype=np.float64)
    return base.astype(np.uint8), np.rint(base + (255 - base) * blend).astype(np.uint8)


def pattern(hex_color, settings, width=None, height=None):
    size, pitch, radius = (settings[x] for x in ('size', 'pitch', 'radius'))
    if size < 1 or pitch < 1 or size % pitch or not 0 < radius < pitch / 2:
        raise ValueError('Require a positive tile size divisible by pitch and 0 < radius < pitch/2')
    width, height = width or size, height or size
    y, x = np.ogrid[:height, :width]
    dx = (x + pitch // 2) % pitch - pitch // 2
    dy = (y + pitch // 2) % pitch - pitch // 2
    mask = dx**2 + dy**2 <= radius**2
    base, light = colors(hex_color, settings['white_blend'])
    return np.where(mask[..., None], light, base).astype(np.uint8), mask


def validate(array, hex_color, settings):
    expected, mask = pattern(hex_color, settings)
    base, light = colors(hex_color, settings['white_blend'])
    if array.shape != expected.shape or not np.array_equal(array, expected):
        raise ValueError('Image differs from reference algorithm')
    unique = np.unique(array.reshape(-1, 3), axis=0)
    if len(unique) != 2:
        raise ValueError('Expected exactly two RGB colors')
    return {'dimensions': list(array.shape[:2][::-1]), 'unique_rgb_colors': unique.tolist(),
            'background': base.tolist(), 'dot': light.tolist(), 'coverage': float(mask.mean()),
            'dot_pixels': int(mask.sum()), 'periodic_x': bool(np.array_equal(array, np.roll(array, settings['pitch'], axis=1))),
            'periodic_y': bool(np.array_equal(array, np.roll(array, settings['pitch'], axis=0)))}


def to_linear(rgb):
    s = np.asarray(rgb, dtype=np.float32) / 255
    return np.where(s <= .04045, s / 12.92, ((s + .055) / 1.055) ** 2.4)


def to_srgb(linear):
    return np.rint(np.clip(np.where(linear <= .0031308, linear * 12.92,
                                    1.055 * np.maximum(linear, 0) ** (1 / 2.4) - .055), 0, 1) * 255).astype(np.uint8)


def linear_mips(image):
    """Periodic RGB mips averaged in linear light, not dark sRGB averages."""
    current = np.asarray(image, dtype=np.uint8)
    yield current
    linear = to_linear(current)
    while linear.shape[0] > 1 or linear.shape[1] > 1:
        h, w = linear.shape[:2]
        # Canonical source is power-of-two; derivatives use tiled canonical levels.
        rows = np.arange(max(1, h // 2)) * 2
        cols = np.arange(max(1, w // 2)) * 2
        linear = sum(linear[np.minimum(rows[:, None] + dy, h-1), np.minimum(cols[None, :] + dx, w-1)]
                     for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1))) / 4
        yield to_srgb(linear)


def generate(config):
    output = Path(config['paths']['canonical'])
    output.mkdir(parents=True, exist_ok=True)
    report = {}
    for category, entry in config['categories'].items():
        pixels, _ = pattern(entry['color'], config['generation'])
        path = output / f'{category}.png'
        Image.fromarray(pixels).save(path)
        report[category] = validate(np.asarray(Image.open(path).convert('RGB')), entry['color'], config['generation'])
    (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def previews(config):
    """Standalone UV spheres: illustrative lighting, never game screenshots."""
    output = Path(config['paths']['reports']) / 'previews'
    output.mkdir(parents=True, exist_ok=True)
    size = 320
    y, x = np.mgrid[:size, :size]
    nx = (x - size/2) / (size*.42)
    ny = (size/2 - y) / (size*.42)
    inside = nx**2 + ny**2 < 1
    nz = np.sqrt(np.maximum(0, 1-nx**2-ny**2))
    u = np.arctan2(nx, nz) / (2*np.pi) + .5
    v = np.arcsin(np.clip(ny, -1, 1)) / np.pi + .5
    light = np.maximum(0, nx*(-.35) + ny*.55 + nz*.76)
    sheets = Image.new('RGB', (size*4, (size+46)*2), '#171d24')
    draw = ImageDraw.Draw(sheets)
    for i, (name, entry) in enumerate(config['categories'].items()):
        pixels, _ = pattern(entry['color'], config['generation'])
        # A fixed UV sphere, same geometry/light/exposure for every category.
        tile_size=config['generation']['size']
        albedo = pixels[(v*tile_size).astype(int)%tile_size, (u*tile_size*2).astype(int)%tile_size]
        shade = to_srgb(to_linear(albedo) * (.16 + .84*light[..., None]))
        frame = np.full((size, size, 3), (23, 29, 36), dtype=np.uint8)
        frame[inside] = shade[inside]
        image = Image.fromarray(frame)
        image.save(output / f'{name}-material.png')
        col, row = i%4, i//4
        sheets.paste(image, (col*size, row*(size+46)))
        draw.text((col*size+16, row*(size+46)+size+4), name+' '+entry['color'], fill='white')
        draw.text((col*size+16, row*(size+46)+size+21), 'Illustrative UV sphere', fill='#aeb8c4')
    sheets.save(output / 'material-contact-sheet.png')
    return str(output / 'material-contact-sheet.png')
