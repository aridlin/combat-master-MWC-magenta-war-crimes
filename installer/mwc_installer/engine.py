"""Desired-state composition and recoverable, hash-guarded bundle transactions."""
import copy, fnmatch, gc, json, os, re, shutil, sys, uuid
from pathlib import Path
from contextlib import contextmanager
import tempfile
from bundle_utils import digest
from halftone.assets import dump
from deploy_halftone import replace_verified

ROOT=Path(__file__).resolve().parents[2]
IDS={'lynx','scorpion','fishing_rod','nail_gun','toaster','medigun','players','weapons','terrain','cat_audio','crates','reticles','iron','glass','menu','sky','operator_arms','sonic_impact','tf2_medigun_audio','audiojungle_medigun'}
MODELS={'scorpion','fishing_rod','nail_gun','toaster','medigun'}

def log(message):print(message,flush=True)

def copy_private(source,target):
    """Private CoW snapshot where supported; never a mutable hard link."""
    source=Path(source);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with source.open('rb') as incoming,tempfile.NamedTemporaryFile(dir=target.parent,prefix='.mwc-copy-',delete=False) as out:
            temp=Path(out.name);cloned=False
            if os.name!='nt':
                import fcntl
                try:fcntl.ioctl(out.fileno(),0x40049409,incoming.fileno());cloned=True
                except OSError:pass
            if not cloned:shutil.copyfileobj(incoming,out)
            out.flush()
        os.replace(temp,target);temp=None
    finally:
        if temp is not None:temp.unlink(missing_ok=True)


def discover():
    from configure import libraries
    found=[]
    for library in libraries():
        manifest=library/'steamapps/appmanifest_2281730.acf'
        if not manifest.exists():continue
        match=re.search(r'"installdir"\s+"([^"]+)"',manifest.read_text())
        if match:found.append(str(library/'steamapps/common'/match[1]))
    return found

def inspect_game(game):
    game=Path(game).expanduser().resolve();manifest=game.parent.parent/'appmanifest_2281730.acf'
    from halftone.pipeline import build_id
    config=json.loads((ROOT/'config/preset.json').read_text())
    config.update(bundle_root=str(game/'CombatMaster_Data/StreamingAssets/Bundles'),app_manifest=str(manifest),source_overrides={})
    build_id(config)
    if not any((game/name).is_file() for name in ('GameAssembly.so','GameAssembly.dll')):raise ValueError('Expected the IL2CPP Combat Master installation')
    if not Path(config['bundle_root']).is_dir():raise ValueError('Combat Master bundle directory missing')
    return config

def game_running(game):
    """Read process executable paths only. No process memory access or injection."""
    game=Path(game).resolve()
    if os.name=='nt':
        import ctypes as c
        from ctypes import wintypes as w
        class Entry(c.Structure):
            _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),('heap',c.c_size_t),('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),('exe',w.WCHAR*260)]
        k=c.WinDLL('kernel32',use_last_error=True)
        k.CreateToolhelp32Snapshot.restype=w.HANDLE;k.OpenProcess.restype=w.HANDLE
        k.Process32FirstW.argtypes=[w.HANDLE,c.POINTER(Entry)];k.Process32NextW.argtypes=[w.HANDLE,c.POINTER(Entry)]
        k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)];k.CloseHandle.argtypes=[w.HANDLE]
        snap=k.CreateToolhelp32Snapshot(2,0)
        if snap==c.c_void_p(-1).value:raise OSError('Cannot enumerate processes safely')
        try:
            e=Entry();e.size=c.sizeof(e);ok=k.Process32FirstW(snap,c.byref(e))
            while ok:
                if 'combatmaster' in e.exe.lower():
                    h=k.OpenProcess(0x1000,False,e.pid)
                    if not h:raise ValueError('Close Combat Master before applying changes')
                    try:
                        buf=c.create_unicode_buffer(32768);size=w.DWORD(len(buf))
                        if not k.QueryFullProcessImageNameW(h,0,buf,c.byref(size)):raise OSError('Cannot inspect game executable path')
                        if Path(buf.value).resolve().parent==game:return True
                    finally:k.CloseHandle(h)
                ok=k.Process32NextW(snap,c.byref(e))
        finally:k.CloseHandle(snap)
        return False
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            exe=(p/'exe').resolve()
            if exe.parent==game and exe.name in ('CombatMaster.x86_64','CombatMaster.exe'):return True
        except OSError:pass
    return False

@contextmanager
def locked(state):
    state.mkdir(parents=True,exist_ok=True)
    # OS locks release automatically after a crash; the lock file itself persists.
    with (state/'lock').open('a+b') as f:
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            f.seek(0)
            if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(f,fcntl.LOCK_UN)

def managed_files(config):
    root=Path(config['bundle_root']);files=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix()
        if not any(fnmatch.fnmatch(rel,pat) for pat in config['bundles']['include']):continue
        with p.open('rb') as f:
            if f.read(8)==b'UnityFS\0':files.append(rel)
    return files

def snapshot(config,state,adopt=None):
    path=state/'state.json'
    if path.exists():
        saved=json.loads(path.read_text())
        if saved['bundle_root']!=config['bundle_root']:raise ValueError('This backup directory belongs to another installation')
        return saved
    root=Path(config['bundle_root']);files=managed_files(config);originals={};current={}
    adoption=json.loads(Path(adopt).read_text()) if adopt else None
    if adoption and adoption['bundle_root']!=str(root):raise ValueError('Adoption game path mismatch')
    if adoption and set(adoption['files'])!=set(files):raise ValueError('Adoption inventory mismatch')
    import UnityPy
    for rel in files:
        source=root/rel;current[rel]=digest(source)
        if adoption:
            row=adoption['files'][rel]
            if row['current']!=current[rel]:raise ValueError('Adoption target changed: '+rel)
            source=Path(row['original'])
            if digest(source)!=row['original_sha256']:raise ValueError('Adoption original changed: '+rel)
        elif rel in ('src/weapons/weapons','src/weapons/attachments'):
            env=UnityPy.load(str(source))
            if any(o.type.name=='GameObject' and o.peek_name().startswith(('MWC_','MWC_Model_')) for o in env.objects):raise ValueError('Existing MWC layer detected. Restore it or import its verified original snapshots before first install.')
            del env;gc.collect()
        dest=state/'originals'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and digest(dest)!=digest(source):raise ValueError('Partial original snapshot conflicts: '+rel)
        if not dest.exists():copy_private(source,dest)
        originals[rel]=digest(dest)
        if originals[rel]!=digest(source):raise ValueError('Snapshot verification failed: '+rel)
    saved={'version':1,'bundle_root':str(root),'build_id':config['expected_build_id'],'originals':originals,'installed':current,'selected':adoption.get('selected',[]) if adoption else []}
    dump(path,saved);return saved

def verify_current(config,state,saved):
    for rel,sha in saved['installed'].items():
        if digest(Path(config['bundle_root'])/rel)!=sha:raise ValueError('Game files changed outside the installer: '+rel+'. Restore/verify the game separately before reinitializing.')
        if digest(state/'originals'/rel)!=saved['originals'][rel]:raise ValueError('Original backup changed: '+rel)

def recover(config,state):
    jp=state/'pending.json'
    if not jp.exists():return
    j=json.loads(jp.read_text());saved=json.loads((state/'state.json').read_text())
    # A committed state plus leftover journal only needs journal cleanup.
    if saved.get('transaction')==j['id']:jp.unlink();return
    for row in reversed(j['files']):
        target=Path(config['bundle_root'])/row['bundle'];actual=digest(target)
        if actual==row['before']:continue
        if actual!=row['after']:raise ValueError('Recovery found an externally changed bundle: '+row['bundle'])
        replace_verified(Path(row['backup']),target,row['after'],row['before'])
    jp.unlink();log('Recovered interrupted transaction; previous selections restored.')

def transaction(config,state,saved,outputs,selected,operator_assignments=None,operator_appearance=None):
    root=Path(config['bundle_root']);identity=uuid.uuid4().hex;undo=state/'transactions'/identity;rows=[]
    for rel,source in sorted(outputs.items()):
        before=saved['installed'][rel];after=digest(source)
        if before==after:continue
        backup=undo/rel;backup.parent.mkdir(parents=True,exist_ok=True);copy_private(root/rel,backup)
        if digest(backup)!=before:raise ValueError('Target changed while preparing transaction')
        rows.append(dict(bundle=rel,source=str(source),backup=str(backup.resolve()),before=before,after=after))
    verify_current(config,state,saved)
    if game_running(root.parents[2]):raise ValueError('Close Combat Master before installing')
    j={'id':identity,'files':rows,'selected':sorted(selected),'operator_assignments':operator_assignments,'operator_appearance':operator_appearance};dump(state/'pending.json',j)
    try:
        for row in rows:
            replace_verified(Path(row['source']),root/row['bundle'],row['before'],row['after']);log('Installed and hash verified: '+row['bundle'])
        updated=copy.deepcopy(saved);updated['selected']=sorted(selected);updated['transaction']=identity
        if operator_assignments is not None:updated['operator_assignments']=copy.deepcopy(operator_assignments)
        if operator_appearance is not None:updated['operator_appearance']=copy.deepcopy(operator_appearance)
        for row in rows:updated['installed'][row['bundle']]=row['after']
        dump(state/'state.json',updated)
    except BaseException:
        recover(config,state);raise
    (state/'pending.json').unlink();return updated

def compose(config,state,saved,selected,addon,operator_assignments=None,tf2='',operator_appearance=None,audiojungle_source=''):
    """Always compose from originals; no stale layer can overwrite another mod."""
    from halftone.pipeline import build_id
    from halftone.assets import scan
    from halftone.patterns import generate
    from halftone.pipeline import apply,verify
    from halftone.materials import finalize
    from halftone.shared import separate_shared
    from halftone.arrays import apply_arrays
    validate_audio_selection(selected,audiojungle_source)
    run=state/'builds'/uuid.uuid4().hex;work=run/'bundles';work.mkdir(parents=True)
    # Copies are private. Builders never receive the actual game path.
    for rel in saved['originals']:
        p=work/rel;p.parent.mkdir(parents=True,exist_ok=True);copy_private(state/'originals'/rel,p)
    c=copy.deepcopy(config);c['bundle_root']=str(work);c['source_overrides']={};c['operator_original_root']=str(state/'originals');c['titanfall2_source_root']=str(state/'operator-imports')
    c['paths']={n:str(run/n) for n in ('reports','output','backups','canonical')}
    if operator_assignments is None:operator_assignments=saved.get('operator_assignments',{})
    from operators.styles import normalize as appearance_defaults
    operator_appearance=appearance_defaults(saved.get('operator_appearance') if operator_appearance is None else operator_appearance,players='players' in selected)
    textures=bool(selected&{'players','weapons','terrain'})
    for name,category in c['categories'].items():category['enabled']=('players' in selected if name=='characters' else 'weapons' in selected if name=='weapons' else 'terrain' in selected)
    if textures:
        log('Scanning original surface assets...');scan(c,c['paths']['reports']);generate(c);apply(c)
        # Seed unchanged bundles too: shared cross-bundle material bindings and arrays
        # can live in bundles with no directly selected Texture2D.
        mp=Path(c['paths']['reports'])/'modifications.json';manifest=json.loads(mp.read_text())
        existing={b['bundle'] for b in manifest['bundles']}
        import hashlib
        sh=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
        for rel in saved['originals']:
            if rel in existing:continue
            p=work/rel;out=Path(c['paths']['output'])/rel;out.parent.mkdir(parents=True,exist_ok=True);copy_private(p,out)
            backup=Path(c['paths']['backups'])/rel;backup.parent.mkdir(parents=True,exist_ok=True);copy_private(p,backup)
            manifest['bundles'].append(dict(bundle=rel,backup=str(backup),source=str(p),source_sha256=digest(p),output=str(out),output_sha256=digest(out),changes=[],checks={},build_id=build_id(c),settings_sha256=sh))
        dump(mp,manifest);finalize(c);separate_shared(c)
        if 'terrain' in selected:apply_arrays(c,ROOT/'config/array-layers.json')
        verify(c)
        manifest=json.loads(mp.read_text())
        for b in manifest['bundles']:copy_private(b['output'],work/b['bundle'])
    return _compose_modules(c,state,saved,selected,addon,operator_assignments,tf2,operator_appearance,run,work,audiojungle_source)


def _compose_modules(c,state,saved,selected,addon,operator_assignments,tf2,operator_appearance,run,work,audiojungle_source=''):
    """Compose visual modules onto the already verified private texture stage."""
    from halftone.pipeline import build_id
    if Path(c['bundle_root']).resolve()!=Path(work).resolve():raise ValueError('Visual module working tree mismatch')
    # Following modules must read the cumulative working bundle tree, not the
    # earlier halftone output paths stored in its report.
    def baseline():
        dump(Path(c['paths']['reports'])/'modifications.json',{'build_id':c['expected_build_id'],'bundles':[dict(bundle=rel,output=str(work/rel),output_sha256=digest(work/rel)) for rel in saved['originals']]})
    def settings(name):return dict(output=str(run/name),backups=str(run/(name+'-backup')),asset_output=str(run/(name+'-assets')))
    def merge(s):
        m=json.loads((Path(s['output'])/'manifest.json').read_text());rows=m.get('files',[m])
        for row in rows:
            rel=row.get('bundle') or ('root/audio' if 'resource_file' in row else 'src/src')
            if digest(Path(row['output']))!=row['output_sha256']:raise ValueError('Module output changed')
            copy_private(row['output'],work/rel)
    source_assets=run/'addon'
    if selected&{'lynx','cat_audio'}:
        if not addon:raise ValueError('Select the locally owned M1A0 Cat Gun workshop archive for Lynx or cat sounds')
        from catgun.import_addon import extract
        extract(addon,source_assets)
    if 'crates' in selected:
        import crate_colors
        log('Building blue crates...');baseline();s=settings('crates');s['color']='#008CFF';crate_colors.build(c,s);merge(s)
    if 'lynx' in selected:
        from catgun.bundle import build as catbuild
        log('Building M1A0 Lynx with original tail...');baseline();s=settings('lynx');s.update(model='m1a0',source_assets=str(source_assets),tail_mode='original',scale=1.,position=[0.,0.,0.],rotation=[0.,.7071067811865476,.7071067811865476,0.]);catbuild(c,s)
        from catgun.operations import verify as catverify
        catverify(c,s);merge(s)
    if selected&{'reticles','iron'}:
        import sight_customization
        log('Building selected sight changes...');s=settings('sights');s.update(mapping=str(ROOT/'config/sight-map.json'),reticles='reticles' in selected,iron='iron' in selected,sources={rel:digest(work/rel) for rel in ('root/root','src/weapons/weapons','src/weapons/attachments')});sight_customization.build(c,s);merge(s)
    if selected&MODELS:
        from weapon_models import bundles
        log('Building selected weapon models...');s=settings('models');s.update(models={n:{'enabled':n in selected} for n in MODELS})
        if 'medigun' in selected:
            from weapon_models.local_tf2 import prepare as medigun_source
            s['models']['medigun']['directory']=str(medigun_source(c,run,tf2))
        s['sources']={rel:digest(work/rel) for rel in bundles.bundle_names(s)};bundles.build(c,s);merge(s)
    if 'sonic_impact' in selected:
        import sonic_impact
        log('Building Sonic impact grenade visuals...');s=settings('sonic-impact');s['source_sha256']=digest(work/sonic_impact.BUNDLE);sonic_impact.build(c,s);merge(s)
    if 'glass' in selected:
        import helicopter_windows
        log('Building helicopter glass...');s=settings('glass');s['source_sha256']=digest(work/'src/src');helicopter_windows.build(c,s);merge(s)
    if 'cat_audio' in selected:
        import cat_audio
        log('Building Lynx cat sounds...');s=settings('audio');s.update(source_assets=str(source_assets),source_sha256=digest(work/'root/audio'));cat_audio.build(c,s);merge(s)
    if 'tf2_medigun_audio' in selected:
        import tf2_audio
        log('Building optional local-TF2 Medigun sounds...');s=settings('tf2-audio');s['source_sha256']=digest(work/'root/audio');tf2_audio.build(c,s,tf2);merge(s)
    if 'audiojungle_medigun' in selected:
        import audiojungle
        log('Building optional local Audiojungle excerpts...');s=settings('audiojungle');s['source_sha256']=digest(work/'root/audio');audiojungle.build(c,s,audiojungle_source);merge(s)
    if 'sky' in selected:
        from skybox import bundles as sky
        log('Building Minecraft-style skies...');s=settings('sky');s.update(size=256,sources={rel:digest(work/rel) for rel in sky.TARGETS});sky.build(c,s);merge(s)
    if 'menu' in selected:
        import menu_background
        log('Building Fishguy menu...');s=settings('menu');s.update(source_sha256=digest(work/'root/root'),image=str(ROOT/'assets/branding/menu-halftone.png'));menu_background.build(c,s);merge(s)
    if operator_appearance['game_customs_magenta']!=('players' in selected):
        from operators.native_colors import build as native_colors,SOURCES as native_color_sources
        log('Building independent native-operator colors...');s=settings('native-colors');s.update(source_sha256=digest(work/'src/thrid_person'),original_root=str(state/'originals'),original_sha256={r:saved['originals'][r] for r in native_color_sources},magenta=operator_appearance['game_customs_magenta'],operator_assignments=operator_assignments);native_colors(c,s);merge(s)
    if operator_assignments:
        from operators.library import prepare as operator_sources
        from operators.bundles import build as operator_build,BUNDLE
        log('Building explicit per-operator replacements...');library=operator_sources(c,operator_assignments,run,tf2,operator_appearance,matching_arms='operator_arms' in selected);s=settings('operators');s.update(assignments=operator_assignments,source_sha256=digest(work/BUNDLE),library=library);operator_build(c,s);merge(s)
        if 'operator_arms' in selected:
            log('Building matching authored first-person arms on native weapon rigs...');s=settings('operator-arms');s.update(first_person=True,assignments=operator_assignments,source_sha256=digest(work/'src/first_person'),library=library);operator_build(c,s);merge(s)
    return {rel:work/rel for rel in saved['originals']}

def validate_frontend(saved,request):
    supported=request.get('supported_mods')
    if not isinstance(supported,list) or not all(isinstance(x,str) for x in supported):
        raise ValueError('Update/reopen the MWC installer: this frontend does not declare its supported mod catalogue')
    missing=set(saved.get('selected',[]))-set(supported)
    if missing:raise ValueError('Outdated installer cannot represent installed mods: '+', '.join(sorted(missing))+'. Reopen the current installer before applying a selection.')
    if saved.get('operator_assignments') and 'operator_assignments' not in request:raise ValueError('Outdated installer cannot represent installed operator assignments; reopen the current installer')
    if saved.get('operator_appearance') and 'operator_appearance' not in request:raise ValueError('Outdated installer cannot represent installed operator colors; reopen the current installer')
    colors=saved.get('operator_appearance',{}).get('model_magenta',{})
    installed_models=set(saved.get('operator_assignments',{}).values())|set(colors)
    if installed_models:
        represented=request.get('supported_operator_models')
        if not isinstance(represented,list) or not all(isinstance(x,str) for x in represented):
            raise ValueError('Outdated installer does not declare its operator model catalogue; reopen the current installer')
        missing=installed_models-set(represented)
        if missing:raise ValueError('Outdated installer cannot represent installed operator models/colors: '+', '.join(sorted(missing)))

def validate_audio_selection(selected,source=''):
    if {'tf2_medigun_audio','audiojungle_medigun'}<=set(selected):
        raise ValueError('Choose either TF2 Medigun sounds or Audiojungle excerpts: both replace the same four Minigun sound slots')
    if 'audiojungle_medigun' in selected:
        from audiojungle import prepare
        prepare(source)


def execute(request):
    game=request.get('game','')
    if not game:
        found=discover()
        if len(found)!=1:raise ValueError('Choose your Combat Master game folder; automatic discovery found '+str(len(found))+' installations')
        game=found[0]
    config=inspect_game(game);state=Path(request['state']).expanduser().resolve()
    root=Path(config['bundle_root'])
    if state==root or root in state.parents or state in root.parents:raise ValueError('Backups must be outside the game bundle tree')
    selected=set(request.get('selected',[]))
    from operators.assignments import validate as validate_operators
    operator_assignments=validate_operators(request.get('operator_assignments',{}))
    if not selected<=IDS:raise ValueError('Unknown mod selection')
    if request['action']=='apply':validate_audio_selection(selected,request.get('audiojungle_source',''))
    if request['action']=='apply' and not request.get('offline_authorized'):raise ValueError('Confirm an offline or explicitly authorized modding environment')
    with locked(state):
        if game_running(Path(config['bundle_root']).parents[2]):raise ValueError('Close Combat Master before applying changes')
        os.chdir(state) # legacy safe_output confines generated files to CWD
        recover(config,state)
        saved=snapshot(config,state,request.get('adopt'));verify_current(config,state,saved)
        from operators.styles import normalize as appearance_defaults
        operator_appearance=appearance_defaults(request.get('operator_appearance',saved.get('operator_appearance')),players='players' in selected)
        if request['action']=='apply':validate_frontend(saved,request)
        if request['action']=='restore':selected=set();operator_assignments={};operator_appearance=appearance_defaults(players=False);outputs={rel:state/'originals'/rel for rel in saved['originals']}
        elif request['action']=='apply':outputs=compose(config,state,saved,selected,request.get('addon',''),operator_assignments,request.get('tf2',''),operator_appearance,request.get('audiojungle_source',''))
        else:raise ValueError('Unknown action')
        result=transaction(config,state,saved,outputs,selected,operator_assignments,operator_appearance)
        log('Complete. Selected mods: '+(', '.join(result['selected']) or 'none (originals restored)'))
        return result
