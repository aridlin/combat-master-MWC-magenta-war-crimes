"""CPU reference render for local authored assets; run in trusted Blender."""
import argparse,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector

p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--azimuth',type=float,default=-65);p.add_argument('--unskinned',action='store_true');p.add_argument('--glasses');p.add_argument('--head',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=Path(a.source).resolve();out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.is_dir():
 meta=json.loads((source/'source.json').read_text());d=np.load(source/('source.npz' if (source/'source.npz').exists() else 'mesh.npz'),allow_pickle=False);label=meta.get('id','Fitted character')
 mesh=bpy.data.meshes.new(label);mesh.from_pydata(d['positions'].tolist(),[],d['faces'].tolist());mesh.update();obj=bpy.data.objects.new(label,mesh)
 if meta.get('coordinate_system')!='z_up':obj.rotation_euler[0]=math.pi/2
 bpy.context.collection.objects.link(obj)
 layer=mesh.uv_layers.new(name='UVMap')
 for polygon,mi in zip(mesh.polygons,d['face_materials']):
  polygon.material_index=next(n for n,m in enumerate(meta['materials']) if m.get('index',n)==mi);polygon.use_smooth=True
  for li in polygon.loop_indices:
   u,v=d['uv'][mesh.loops[li].vertex_index];layer.data[li].uv=(u,v if (source/'source.npz').exists() else 1-v)
 for mat in meta['materials']:
  m=bpy.data.materials.new(mat['name']);m.use_nodes=True;bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.65;bsdf.inputs['Base Color'].default_value=mat.get('base_color_linear',[1.,1.,1.,1.])
  if 'image' in mat or 'pixels' in mat:
   tex=m.node_tree.nodes.new('ShaderNodeTexImage')
   if 'image' in mat:tex.image=bpy.data.images.load(str(source/mat['image']))
   else:
    pixels=np.load(source/mat['pixels'],allow_pickle=False);im=bpy.data.images.new(mat['name'],width=pixels.shape[1],height=pixels.shape[0],alpha=True);im.pixels[:]=pixels.ravel();tex.image=im
   m.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
   m.node_tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
  if mat.get('transparent'):
   bsdf.inputs['Roughness'].default_value=mat.get('roughness',.15);bsdf.inputs['IOR'].default_value=1.49
   if mat.get('alpha_mode')=='blend':
    # Native URP alpha blending is not refractive glass transmission.
    bsdf.inputs['Transmission Weight'].default_value=0.
    if mat.get('cull_backfaces'):
     geometry=m.node_tree.nodes.new('ShaderNodeNewGeometry');mask=m.node_tree.nodes.new('ShaderNodeMath');mask.operation='SUBTRACT';mask.inputs[0].default_value=1;alpha=m.node_tree.nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY';alpha.inputs[1].default_value=mat.get('base_color_linear',[1,1,1,1])[3];m.node_tree.links.new(geometry.outputs['Backfacing'],mask.inputs[1]);m.node_tree.links.new(mask.outputs[0],alpha.inputs[0]);m.node_tree.links.new(alpha.outputs[0],bsdf.inputs['Alpha'])
    if not mat.get('casts_shadow',True):
     lightpath=m.node_tree.nodes.new('ShaderNodeLightPath');shadow=m.node_tree.nodes.new('ShaderNodeMath');shadow.operation='SUBTRACT';shadow.inputs[0].default_value=1;combine=m.node_tree.nodes.new('ShaderNodeMath');combine.operation='MULTIPLY';combine.inputs[0].default_value=mat.get('base_color_linear',[1,1,1,1])[3]
     if mat.get('cull_backfaces'):m.node_tree.links.new(alpha.outputs[0],combine.inputs[0])
     m.node_tree.links.new(lightpath.outputs['Is Shadow Ray'],shadow.inputs[1]);m.node_tree.links.new(shadow.outputs[0],combine.inputs[1]);m.node_tree.links.new(combine.outputs[0],bsdf.inputs['Alpha'])
   else:bsdf.inputs['Transmission Weight'].default_value=.65
  mesh.materials.append(m)
 mesh.normals_split_custom_set([tuple(d['normals'][loop.vertex_index]) for loop in mesh.loops])
elif source.suffix.lower() in ('.glb','.gltf'):
 bpy.ops.import_scene.gltf(filepath=str(source))
 for obj in bpy.context.scene.objects:
  if obj.type=='ARMATURE':obj.data.pose_position='REST'
elif source.suffix.lower()=='.fbx':
 bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
 texture=source.with_name('body-texture.png')
 if texture.exists():
  for obj in bpy.context.scene.objects:
   if obj.type=='ARMATURE':obj.data.pose_position='REST'
   if obj.type=='MESH':
    for m in obj.data.materials:
     m.use_nodes=True;bsdf=m.node_tree.nodes.get('Principled BSDF');tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(texture),check_existing=True);m.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
else:raise ValueError('Unsupported preview input')
if a.unskinned:
 for obj in bpy.context.scene.objects:
  for modifier in obj.modifiers:
   if modifier.type=='ARMATURE':modifier.show_render=False;modifier.show_viewport=False
if a.glasses:
 for name in ('frame','shield'):
  arrays=np.load(Path(a.glasses)/(name+'.npz'),allow_pickle=False);me=bpy.data.meshes.new('Shooting glasses '+name);me.from_pydata(arrays['positions'].tolist(),[],arrays['faces'].tolist());me.update();ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
  for poly in me.polygons:poly.use_smooth=True
  me.normals_split_custom_set([tuple(arrays['normals'][loop.vertex_index]) for loop in me.loops]);m=bpy.data.materials.new(name);m.use_nodes=True;bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.012,.016,.020,1) if name=='frame' else (.32,.095,.035,1);bsdf.inputs['Roughness'].default_value=.55 if name=='frame' else .13
  if name=='shield':bsdf.inputs['Transmission Weight'].default_value=.65;bsdf.inputs['Alpha'].default_value=.60;bsdf.inputs['IOR'].default_value=1.49
  me.materials.append(m)
bpy.context.view_layer.update();points=[o.matrix_world@Vector(c) for o in bpy.context.scene.objects if o.type=='MESH' for c in o.bound_box];lo=Vector(tuple(min(p[n] for p in points) for n in range(3)));hi=Vector(tuple(max(p[n] for p in points) for n in range(3)));center=(lo+hi)/2;span=max(hi-lo)
if a.head:
 index=next(i for i,name in enumerate(meta['bone_names']) if name.endswith('Head_M'));head=np.linalg.inv(d['inverse_bind'])[index,:3,3];center=Vector(head)+Vector((0,-.10,.075));span=.52
angle=math.radians(a.azimuth);camera=bpy.data.cameras.new('Reference camera');camera.clip_end=max(1000,span*20);camera.clip_start=min(.01,span/10000);cam=bpy.data.objects.new('Reference camera',camera);bpy.context.collection.objects.link(cam);cam.location=center+Vector((math.cos(angle),math.sin(angle),.16))*span*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=span*1.2
scene=bpy.context.scene;scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=12;scene.render.threads_mode='FIXED';scene.render.threads=2
for name,offset,power,size in [('Key',(2,-3,4),450,3),('Fill',(-2,2,2),250,3)]:
 light=bpy.data.lights.new(name,'AREA');light.energy=power*span*span;light.shape='DISK';light.size=size*span;ob=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(ob);ob.location=center+Vector(offset)*span;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
scene.world=bpy.data.worlds.new('Reference world');scene.world.color=(.25,.25,.25);scene.render.resolution_x=480;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(out);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=str(out.with_suffix('.blend')))
bpy.ops.render.render(write_still=True)
