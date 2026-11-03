"""Build portable distributions. Never include game bundles or local addon assets."""
import argparse,hashlib,json,shutil,struct,subprocess,sys,tarfile,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[1];I=R/'installer';DIST=I/'dist'
SOURCES=['bundle_utils.py','configure.py','deploy_halftone.py','menu_background.py','sight_customization.py','helicopter_windows.py','crate_colors.py','cat_audio.py','catgun','weapon_models','skybox','operators','model_import','halftone','installer/mwc_installer','installer/__init__.py','config','assets/branding','assets/authored-weapons','assets/operator-sources']
def copy_sources(dest):
    for name in SOURCES:
        p=R/name;target=dest/name
        if p.is_dir():shutil.copytree(p,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        else:target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    shutil.copyfile(I/'backend.py',dest/'installer/backend.py')
def common(dest,windows):
    dest.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(I/'build'/('mwc-installer.exe' if windows else 'mwc-installer'),dest/('MWC-Installer.exe' if windows else 'MWC-Installer'))
    if not windows:(dest/'MWC-Installer').chmod(0o755)
    shutil.copytree(I/'assets',dest/'assets',dirs_exist_ok=True);shutil.copytree(R/'assets/branding',dest/'branding',dirs_exist_ok=True)
    addon=R/'external-assets/m1a0/M1A0-Cat-Gun.bin'
    if not addon.exists():raise ValueError('Supply the local M1A0 archive under external-assets/m1a0 before building this bundled edition')
    (dest/'addons').mkdir(exist_ok=True);shutil.copyfile(addon,dest/'addons/M1A0-Cat-Gun.bin')
    shutil.copyfile(I/'M1A0-CREDITS.txt',dest/'addons/M1A0-CREDITS.txt')
    shutil.copyfile(I/'catalog.json',dest/'catalog.json');shutil.copyfile(R/'LICENSE',dest/'MWC-LICENSE.txt')
    if (I/'README.md').exists():shutil.copyfile(I/'README.md',dest/'README.md')
    shutil.copyfile(I/'vendor/PROVENANCE.md',dest/'FT-PROVENANCE.md')
    (dest/'OPERATOR-ASSET-CREDITS.md').write_text((R/'assets/operator-sources/ATTRIBUTION.md').read_text().replace('(licenses/','(operator-licenses/'))
    shutil.copytree(R/'assets/operator-sources/licenses',dest/'operator-licenses',dirs_exist_ok=True)
def build(windows,output=None):
    destination_root=Path(output).resolve() if output else DIST
    dest=destination_root/('MWC-Windows-x64' if windows else 'MWC-Linux-x64')
    if dest.exists():shutil.rmtree(dest)
    common(dest,windows)
    if windows:
        runtime=dest/'runtime';runtime.mkdir()
        with zipfile.ZipFile(I/'downloads/python-3.12.10-embed-amd64.zip') as z:z.extractall(runtime)
        lib=runtime/'Lib/site-packages';lib.mkdir(parents=True)
        wheels=sorted((I/'downloads/win-wheels').glob('*.whl'))+sorted((I/'downloads/pure-wheels').glob('*.whl'))
        if len(wheels)<13:raise ValueError('Download the locked Windows dependency wheels first')
        for p in wheels:
            with zipfile.ZipFile(p) as z:z.extractall(lib)
        (runtime/'python312._pth').write_text('python312.zip\n.\nLib/site-packages\nimport site\n')
        copy_sources(dest/'source')
        archive=Path(shutil.make_archive(str(dest),'zip',root_dir=dest.parent,base_dir=dest.name))
    else:
        cmd=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','mwc-backend','--distpath',str(I/'build/backend-dist'),'--workpath',str(I/'build/backend-work'),'--specpath',str(I/'build'),'--paths',str(R)]
        for name in SOURCES:
            target=name if (R/name).is_dir() else str(Path(name).parent)
            cmd+=['--add-data',str(R/name)+':'+target]
        for pkg in ['UnityPy','numpy','PIL','texture2ddecoder','etcpak','astc_encoder','fmod_toolkit','pyfmodex','tpk_ar','archspec','installer.mwc_installer']:cmd+=['--collect-all',pkg]
        # Builders are imported inside branches, and all must be visible to analysis.
        for name in ['catgun.operations','catgun.bundle','catgun.import_addon','weapon_models.bundles','weapon_models.local_tf2','sight_customization','helicopter_windows','crate_colors','cat_audio','menu_background','halftone.arrays','halftone.shared','skybox.bundles','weapon_models.imported','operators.assignments','operators.inventory','operators.retarget','model_import.tf2','operators.assets','operators.bundles','operators.library','operators.profiles','operators.skinning','operators.styles','operators.native_colors','operators.previews']:cmd+=['--hidden-import',name]
        subprocess.run(cmd+[str(I/'backend.py')],check=True,cwd=R)
        shutil.copytree(I/'build/backend-dist/mwc-backend',dest/'backend',symlinks=True)
        import archspec
        shutil.copytree(Path(archspec.__file__).parent,dest/'backend/_internal/archspec',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        # Some portable CPython builds mark PT_GNU_STACK executable although
        # Python does not need executable stacks. Clear only that ELF flag
        # in the private bundled copies for current glibc compatibility.
        for p in (dest/'backend').rglob('*'):
            if not p.is_file() or p.is_symlink():continue
            with p.open('rb') as f:magic=f.read(6)
            if magic!=b'\x7fELF\x02\x01':continue
            data=bytearray(p.read_bytes());offset=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
            changed=False
            for n in range(count):
                pos=offset+n*size;kind,flags=struct.unpack_from('<II',data,pos)
                if kind==0x6474e551 and flags&1:struct.pack_into('<I',data,pos+4,flags&~1);changed=True
            if changed:p.write_bytes(data)
        archive=dest.with_suffix('.tar.gz')
        with tarfile.open(archive,'w:gz') as t:t.add(dest,arcname=dest.name)
    (archive.with_suffix(archive.suffix+'.sha256')).write_text(hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()+'  '+archive.name+'\n')
    print(archive)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--windows',action='store_true');p.add_argument('--output',type=Path,help='Build in a separate directory without replacing a running installer');a=p.parse_args();build(a.windows,a.output)
