#!/usr/bin/env python3
"""Locate Steam Combat Master and create an untracked local configuration."""
import argparse
import json
import os
import re
from pathlib import Path


def libraries():
    roots=[Path.home()/'.local/share/Steam',Path.home()/'.steam/steam',Path.home()/'.var/app/com.valvesoftware.Steam/data/Steam']
    if os.name=='nt':
        import winreg
        for hive,key,value in [(winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam','SteamPath'),(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam','InstallPath')]:
            try:
                with winreg.OpenKey(hive,key) as handle:roots.append(Path(winreg.QueryValueEx(handle,value)[0]))
            except OSError:pass
        roots += [Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))/'Steam']
    result=set()
    for root in roots:
        if root.exists():result.add(root.resolve())
        index=root/'steamapps/libraryfolders.vdf'
        if index.exists():result.update(Path(p.replace('\\\\','\\')).expanduser().resolve() for p in re.findall(r'"path"\s+"([^"]+)"',index.read_text()))
    return sorted(result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path);p.add_argument('--original-bundles',type=Path)
    p.add_argument('--preset',default='config/preset.json');p.add_argument('--output',default='halftone.json')
    args=p.parse_args();c=json.loads(Path(args.preset).read_text())
    candidates=[args.library.expanduser().resolve()] if args.library else libraries()
    found=[]
    for library in candidates:
        manifest=library/'steamapps/appmanifest_2281730.acf'
        if not manifest.exists():continue
        text=manifest.read_text();match=re.search(r'"installdir"\s+"([^"]+)"',text)
        if match:found.append((manifest,library/'steamapps/common'/match[1],text))
    if len(found)!=1:raise SystemExit('Expected one install; use --library /path/to/SteamLibrary to select it')
    manifest,game,text=found[0];match=re.search(r'"buildid"\s+"([^"]+)"',text)
    if not match or match[1]!=c['expected_build_id']:
        raise SystemExit('This game build has not been validated by the preset. Inspect it before editing the expected build ID.')
    root=game/'CombatMaster_Data/StreamingAssets/Bundles'
    if not any((game/n).exists() for n in ('GameAssembly.so','GameAssembly.dll')) or not root.exists():raise SystemExit('Expected a native IL2CPP build')
    c['bundle_root']=str(root);c['app_manifest']=str(manifest);c['source_overrides']={}
    if args.original_bundles:
        original=args.original_bundles.expanduser().resolve()
        for path in original.rglob('*'):
            if path.is_file():c['source_overrides'][path.relative_to(original).as_posix()]=str(path)
    target=Path(args.output)
    if target.exists():raise SystemExit('Refusing to overwrite local config: '+str(target))
    target.write_text(json.dumps(c,indent=2)+'\n')
    print('Combat Master install:',game);print('Local configuration:',target)


if __name__=='__main__':main()
