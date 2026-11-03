"""Compile the exact same FT frontend for Linux or MinGW Windows."""
import argparse,json,subprocess
from PIL import Image
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--windows',action='store_true');a=p.parse_args()
root=Path(__file__).resolve().parent
mods=json.loads((root/'catalog.json').read_text())
header='#pragma once\nstruct Mod {std::string id,title,group,description,thumbnail,kind;float thumb_w=1,thumb_h=1;bool selected=false;ft::ImageHandle* image=nullptr;};\nstatic std::vector<Mod> mods={\n'
for m in mods:
    with Image.open(root/m['thumbnail']) as img:w,h=img.size
    header+='{'+','.join(json.dumps(m[k]) for k in ('id','title','group','description','thumbnail','preview_kind'))+f',{w},{h}'+'},\n'
(root/'catalog.generated.hpp').write_text(header+'};\n')
output=root/'build'/('mwc-installer.exe' if a.windows else 'mwc-installer');output.parent.mkdir(exist_ok=True)
cmd=['x86_64-w64-mingw32-g++' if a.windows else 'c++','-std=c++17','-O2',str(root/'app.cpp'),'-o',str(output),'-pthread']
if a.windows:cmd+=['-static','-mwindows','-ld2d1','-ldwrite','-lgdi32','-lole32','-luuid','-luser32','-lwindowscodecs','-lcomdlg32','-lshell32','-lws2_32']
else:cmd+=subprocess.check_output(['pkg-config','--cflags','--libs','cairo','x11'],text=True).split()
subprocess.run(cmd,check=True)
print(output)
