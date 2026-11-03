"""Independent color control for unreplaced native operator renderers.

Clone pristine materials/albedos into the private operator bundle. Shared game
materials/textures stay unchanged, including arms, weapons and custom models.
External material references are remapped by CAB identity, never path-ID alone.
"""
import copy,gc,hashlib,json
from pathlib import Path
import UnityPy
from bundle_utils import digest,inventory
from catgun.bundle import new_object
from halftone.assets import key,dump
from halftone.encoding import apply_pattern
from halftone.materials import TINTS
from .bundles import BUNDLE

SOURCES=(BUNDLE,'src/src','root/root')
ALBEDOS={'_BaseMap','_MainTex','_BaseColorMap','_Albedo'}


def build(config,settings):
    source=Path(config['bundle_root'])/BUNDLE;original_root=Path(settings['original_root']);out=Path(settings['output']);backup=Path(settings['backups'])/BUNDLE
    if digest(source)!=settings['source_sha256']:raise ValueError('Native color baseline changed')
    for rel in SOURCES:
        if digest(original_root/rel)!=settings['original_sha256'][rel]:raise ValueError('Pristine color source changed: '+rel)
    if (out/'manifest.json').exists():raise ValueError('Choose a fresh native color output')
    from installer.mwc_installer.engine import copy_private
    copy_private(source,backup);env=UnityPy.load(str(backup));before=inventory(env);objects={key(o.assets_file.name,o.path_id):o for o in env.objects};old=list(env.objects)
    pristine=UnityPy.load(*(str(original_root/r) for r in SOURCES));originals={key(o.assets_file.name,o.path_id):o for o in pristine.objects};asset=next(o.assets_file for o in old if o.type.name=='SkinnedMeshRenderer');external_names=[e.name for e in asset.externals]
    material_template=next(o for o in old if o.type.name=='Material');texture_template=next(o for o in old if o.type.name=='Texture2D');cloned_materials={};cloned_textures={};added=[];changes={};tex_checks=[]
    def destination_ref(owner,ref):
        if not ref['m_PathID']:return {'m_FileID':0,'m_PathID':0}
        name=owner.name if ref['m_FileID']==0 else owner.externals[ref['m_FileID']-1].name
        if name==asset.name:return {'m_FileID':0,'m_PathID':ref['m_PathID']}
        if name not in external_names:
            if ref['m_FileID']==0:
                # A source CAB is already a reviewed dependency of thrid_person.
                raise ValueError('Source CAB is not a native operator dependency: '+name)
            asset.externals.append(copy.deepcopy(owner.externals[ref['m_FileID']-1]));external_names.append(name)
        return {'m_FileID':external_names.index(name)+1,'m_PathID':ref['m_PathID']}
    def original_object(owner,ref):
        name=owner.name if ref['m_FileID']==0 else owner.externals[ref['m_FileID']-1].name
        obj=originals.get(key(name,ref['m_PathID']))
        if obj is None:raise ValueError('Pristine operator dependency is unavailable: '+key(name,ref['m_PathID']))
        return obj
    def remap(owner,value):
        if isinstance(value,dict):
            if set(value)>={'m_FileID','m_PathID'}:return destination_ref(owner,value)
            return {k:remap(owner,v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return type(value)(remap(owner,v) for v in value)
        return value
    def texture(original):
        identifier=key(original.assets_file.name,original.path_id)
        if identifier in cloned_textures:return cloned_textures[identifier]
        if original.type.name!='Texture2D':raise ValueError('Native operator albedo needs an explicit codec: '+original.type.name)
        obj=new_object(texture_template,'MWC-native-color-texture-'+identifier,objects);tex=original.read();raw=tex.get_image_data()
        # UnityPy's typetree spelling is version dependent; use the typed writer
        # after copying metadata so streamed compressed mip bytes remain exact.
        obj.save_typetree(original.read_typetree());t=obj.read();t.m_Name='MWC_NativeColor_'+tex.m_Name;t.image_data=raw;t.m_StreamData.path='';t.m_StreamData.offset=t.m_StreamData.size=0;t.save()
        if settings['magenta']:
            t=obj.read();apply_pattern(t,config['categories']['characters']['color'],config['generation'])
        else:tex_checks.append((obj.path_id,hashlib.sha256(raw).hexdigest()))
        cloned_textures[identifier]=obj.path_id;added.append(key(asset.name,obj.path_id));return obj.path_id
    def material(original):
        identifier=key(original.assets_file.name,original.path_id)
        if identifier in cloned_materials:return cloned_materials[identifier]
        tree=original.read_typetree();result=remap(original.assets_file,tree);result['m_Name']='MWC_NativeColor_'+tree['m_Name']
        source_slots=dict(tree['m_SavedProperties']['m_TexEnvs'])
        for slot,value in result['m_SavedProperties']['m_TexEnvs']:
            pointer=source_slots[slot]['m_Texture']
            if slot in ALBEDOS and pointer['m_PathID']:value['m_Texture']={'m_FileID':0,'m_PathID':texture(original_object(original.assets_file,pointer))}
        if settings['magenta']:
            for slot,color in result['m_SavedProperties']['m_Colors']:
                if slot in TINTS:color['r']=color['g']=color['b']=1.
            result['m_SavedProperties']['m_Floats']=[(slot,0. if slot=='EnableCamo' else value) for slot,value in result['m_SavedProperties']['m_Floats']]
        obj=new_object(material_template,'MWC-native-color-material-'+identifier,objects);obj.save_typetree(result);cloned_materials[identifier]=obj.path_id;added.append(key(asset.name,obj.path_id));return obj.path_id
    targets=json.loads((Path(__file__).resolve().parents[1]/'config/operator-targets.json').read_text())['operators'];skipped=set(settings.get('operator_assignments',{}));native_cab=asset.name
    for target in targets:
        if target['id'] in skipped:continue
        for row in target['renderers']:
            oid=key(native_cab,int(row['path_id']));obj=objects[oid];tree=obj.read_typetree();pristine_renderer=originals[oid];original_tree=pristine_renderer.read_typetree();materials=[{'m_FileID':0,'m_PathID':material(original_object(pristine_renderer.assets_file,p))} if p['m_PathID'] else p for p in original_tree['m_Materials']];tree['m_Materials']=materials;obj.save_typetree(tree);changes[oid]=materials
    expected=copy.deepcopy(before)
    for oid in list(changes)+added:
        obj=objects[oid];expected[(obj.assets_file.name,obj.path_id)]={'type':obj.type.name,'sha256':hashlib.sha256(obj.data).hexdigest()}
    destination=out/BUNDLE;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(env.file.save(packer='lz4'));del env;gc.collect();checked=UnityPy.load(str(destination));after={key(o.assets_file.name,o.path_id):o for o in checked.objects}
    if inventory(checked)!=expected:raise ValueError('Native operator color serialization mismatch')
    for obj in old:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid not in changes and obj.get_raw_data()!=after[oid].get_raw_data():raise ValueError('Unrelated native color asset changed')
    baseline=UnityPy.load(str(backup))
    for obj in baseline.objects:
        oid=key(obj.assets_file.name,obj.path_id)
        if oid in changes:
            tree=obj.read_typetree();tree['m_Materials']=changes[oid]
            if tree!=after[oid].read_typetree():raise ValueError('Native color exceeded renderer material whitelist')
    for pid,sha in tex_checks:
        if hashlib.sha256(after[key(native_cab,pid)].read().get_image_data()).hexdigest()!=sha:raise ValueError('Restored original albedo mip bytes changed')
    report={'files':[{'bundle':BUNDLE,'output':str(destination.resolve()),'backup':str(backup.resolve()),'source_sha256':digest(backup),'output_sha256':digest(destination)}],'magenta':settings['magenta'],'native_renderers':len(changes),'materials_cloned':len(cloned_materials),'textures_cloned':len(cloned_textures),'verification':{'all_other_original_objects_byte_exact':True,'only_owned_renderer_material_bindings_changed':True,'pristine_albedo_mip_bytes_exact':not settings['magenta'],'replaced_models_excluded':sorted(skipped)},'in_game_tested':False};dump(out/'manifest.json',report);return report
