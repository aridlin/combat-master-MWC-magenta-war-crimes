"""Run only with trusted Blender, --factory-startup --disable-autoexec.

Flatten existing authored mesh objects, preserve UVs/normals and material images,
write portable arrays plus material tiles. Never execute embedded asset scripts.
"""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--texture');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
elif source.suffix in ('.glb','.gltf'):bpy.ops.import_scene.gltf(filepath=str(source))
elif source.suffix=='.fbx':bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
else:raise ValueError('Unsupported source format: '+source.suffix)
for o in bpy.context.scene.objects:
 if o.type=='ARMATURE':o.data.pose_position='REST'
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();materials=[];mat_index={};positions=[];normals=[];uvs=[];faces=[];face_materials=[];parts=[]
def material_index(mat):
 name=mat.name if mat else '__default__'
 if name in mat_index:return mat_index[name]
 color=list(mat.diffuse_color) if mat else [.8,.8,.8,1.];image=None
 if mat and mat.use_nodes:
  bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  emission=next((n for n in mat.node_tree.nodes if n.type=='EMISSION'),None)
  if bsdf:
   base=bsdf.inputs.get('Base Color');color=list(base.default_value)
   if base.is_linked:
    node=base.links[0].from_node
    if node.type!='TEX_IMAGE':raise ValueError('Bake authored material graph before flattening: '+mat.name)
    image=node.image;color=[1.,1.,1.,1.]
  elif emission:
   base=emission.inputs['Color'];color=list(base.default_value)
   if base.is_linked:
    node=base.links[0].from_node
    if node.type!='TEX_IMAGE':raise ValueError('Bake authored unlit graph before flattening: '+mat.name)
    image=node.image;color=[1.,1.,1.,1.]
  else:raise ValueError('Unsupported authored shader; bake before flattening: '+mat.name)
 if a.texture:image=bpy.data.images.load(str(Path(a.texture).resolve()),check_existing=True)
 record={'name':name,'base_color_linear':color}
 if image and image.size[0]>0:
  # Export source pixels as NPY, avoiding color conversion by Blender's save pipeline.
  pix=np.array(image.pixels[:],dtype=np.float32).reshape(image.size[1],image.size[0],image.channels)
  filename=f'material-{len(materials)}.npy';np.save(out/filename,pix);record['pixels']=filename
  if a.texture:record['base_color_linear']=[1.,1.,1.,1.]
 mat_index[name]=len(materials);materials.append(record);return mat_index[name]
for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name):
 if obj.type!='MESH' or obj.hide_render:continue
 evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps);mesh.calc_loop_triangles();world=obj.matrix_world;normal_matrix=world.to_3x3().inverted().transposed();uv=mesh.uv_layers.active;start=len(positions)
 for tri in mesh.loop_triangles:
  mat=mesh.materials[tri.material_index] if tri.material_index<len(mesh.materials) else None;mi=material_index(mat);indices=[]
  for li in tri.loops:
   loop=mesh.loops[li];v=mesh.vertices[loop.vertex_index];pos=world@v.co;normal=(normal_matrix@mesh.corner_normals[li].vector).normalized();indices.append(len(positions));positions.append(list(pos));normals.append(list(normal));uvs.append(list(uv.data[li].uv) if uv else [.5,.5])
  if world.determinant()<0:indices[1],indices[2]=indices[2],indices[1]
  faces.append(indices);face_materials.append(mi)
 parts.append({'name':obj.name,'first_vertex':start,'vertex_count':len(positions)-start});evaluated.to_mesh_clear()
if not positions:raise ValueError('No visible authored mesh geometry')
np.savez_compressed(out/'source.npz',positions=np.asarray(positions,dtype='<f4'),normals=np.asarray(normals,dtype='<f4'),uv=np.asarray(uvs,dtype='<f4'),faces=np.asarray(faces,dtype='<u4'),face_materials=np.asarray(face_materials,dtype='<i4'))
(out/'source.json').write_text(json.dumps({'source':source.name,'objects':parts,'materials':materials,'vertices':len(positions),'triangles':len(faces),'scripts_executed':False},indent=2)+'\n')
print('EXPORTED',len(positions),'vertices',len(faces),'triangles',len(materials),'materials')
