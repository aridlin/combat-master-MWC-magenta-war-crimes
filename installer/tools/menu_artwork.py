"""Deterministic AM halftone of the user's original lobby bitmap, plus sticker.

No generation or redrawing. Coordinates, crop and original canvas are retained.
Inputs are supplied locally; original game art is never fetched by this script.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

def halftone(original,sticker,output,pitch=7):
    with Image.open(original) as src:source=src.convert('RGB')
    w,h=source.size
    # Smooth only at the size of one printed dot; this forms a tonal screen,
    # not new geometry. A soft edge gives subpixel dot coverage at native size.
    gray=np.asarray(source.convert('L').filter(ImageFilter.BoxBlur(pitch/3)),dtype=np.float32)/255
    y,x=np.mgrid[:h,:w].astype(np.float32)
    u=(x+y)/np.sqrt(2);v=(y-x)/np.sqrt(2)
    dx=(u+pitch/2)%pitch-pitch/2;dy=(v+pitch/2)%pitch-pitch/2
    distance=np.sqrt(dx*dx+dy*dy)
    # Tone calibration includes overlapping dots near the white endpoint.
    grid=(np.arange(512,dtype=np.float32)+.5)/512-.5
    radial=np.sort(np.sqrt((grid[:,None]**2+grid[None,:]**2)).ravel())
    radius=radial[np.minimum((gray*(len(radial)-1)).astype(np.int32),len(radial)-1)]*pitch
    coverage=np.clip(radius-distance+.5,0,1)
    pixels=np.rint(coverage*255).astype(np.uint8)
    art=Image.fromarray(pixels).convert('RGBA')
    with Image.open(sticker) as src:seal=src.convert('RGBA')
    # Intentionally retain the native background stretch: the user prefers
    # the seal's comedic oval appearance at 16:9. Do not precompensate it.
    side=round(w*.18);seal.thumbnail((side,side),Image.Resampling.LANCZOS)
    art.alpha_composite(seal,(round(w*.65-seal.width/2),round(h*.15-seal.height/2)))
    target=Path(output);target.parent.mkdir(parents=True,exist_ok=True);art.convert('RGB').save(target)
    record={'method':'deterministic amplitude-modulated grayscale halftone; original canvas and composition preserved','ai_generated':False,'pitch_pixels':pitch,'size':[w,h],'original_sha256':hashlib.sha256(Path(original).read_bytes()).hexdigest(),'sticker_sha256':hashlib.sha256(Path(sticker).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    target.with_suffix('.provenance.json').write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('original');p.add_argument('sticker');p.add_argument('output');a=p.parse_args();print(json.dumps(halftone(a.original,a.sticker,a.output),indent=2))
