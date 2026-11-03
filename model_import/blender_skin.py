"""Export existing authored geometry, materials and skin data, without scripts.

Run in trusted Blender with --factory-startup --disable-autoexec. Produces
data-only arrays; no controllers, animation events or gameplay components.
"""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np

p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');p.add_argument('--exclude',action='append',default=[]);p.add_argument('--rigid',action='append',default=[],help='Explicit unweighted object=source bone index');p.add_argument('--bake-materials',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
source=Path(a.input).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
if source.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
elif source.suffix in ('.glb','.gltf'):bpy.ops.import_scene.gltf(filepath=str(source))
elif source.suffix=='.fbx':bpy.ops.import_scene.fbx(filepath=str(source),use_anim=False)
else:raise ValueError('Unsupported character source')
arms=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
if len(arms)!=1:raise ValueError('Expected one authored skeleton')
arm=arms[0];arm.data.pose_position='REST';bpy.context.view_layer.update()
if a.bake_materials:
 sys.path.insert(0,str(Path(__file__).resolve().parent))
 from blender_bake import bake
 for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name):
  if obj.type!='MESH' or obj.name in a.exclude or not obj.vertex_groups:continue
  for slot in range(len(obj.data.materials)):bake(obj,slot)
bone_names=[b.name for b in arm.data.bones];bone_index={name:i for i,name in enumerate(bone_names)}
if len(bone_names)>256:raise ValueError('Character skeleton exceeds current writer bone limit')
inverse_bind=np.asarray([(arm.matrix_world@b.matrix_local).inverted() for b in arm.data.bones],dtype='<f4')
parents=[bone_index[b.parent.name] if b.parent else -1 for b in arm.data.bones]
rigid={name:int(index) for name,index in (x.rsplit('=',1) for x in a.rigid)}
if any(not 0<=index<len(bone_names) for index in rigid.values()):raise ValueError('Rigid attachment bone outside skeleton')
positions=[];normals=[];uv=[];faces=[];face_materials=[];indices=[];weights=[];parts=[];materials=[];mat_index={};excluded=[]

def material_index(mat):
 name=mat.name if mat else '__default__'
 if name in mat_index:return mat_index[name]
 color=list(mat.diffuse_color) if mat else [.8,.8,.8,1.];image=None;alpha_mode='opaque'
 if mat and mat.use_nodes:
  bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if bsdf:
   base=bsdf.inputs['Base Color'];color=list(base.default_value)
   alpha_mode='blend' if bsdf.inputs['Alpha'].is_linked or bsdf.inputs['Alpha'].default_value<.999 else 'opaque'
   if base.is_linked:
    node=base.links[0].from_node
    if node.type!='TEX_IMAGE':raise ValueError('Bake unsupported authored material before skin export: '+mat.name)
    image=node.image;color=[1.,1.,1.,1.]
 record={'name':name,'base_color_linear':color,'alpha_mode':alpha_mode}
 if image and image.size[0]>0:
  pixels=np.asarray(image.pixels[:],dtype='<f4').reshape(image.size[1],image.size[0],image.channels);filename=f'material-{len(materials)}.npy';np.save(out/filename,pixels);record['pixels']=filename
 mat_index[name]=len(materials);materials.append(record);return mat_index[name]

for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name):
 if obj.type!='MESH' or obj.hide_render:continue
 if obj.name in a.exclude:excluded.append(obj.name);continue
 groups={g.index:bone_index[g.name] for g in obj.vertex_groups if g.name in bone_index}
 if not groups and obj.name not in rigid:excluded.append(obj.name);continue
 mesh=obj.data;mesh.calc_loop_triangles();world=obj.matrix_world;normal_matrix=world.to_3x3().inverted().transposed();layer=mesh.uv_layers.active;start=len(positions)
 vertex_skin=[]
 for v in mesh.vertices:
  skin=sorted([(groups[g.group],g.weight) for g in v.groups if g.group in groups and g.weight>1e-7],key=lambda x:-x[1])[:4]
  if obj.name in rigid:skin=[(rigid[obj.name],1.)]
  if not skin:raise ValueError('Unweighted authored vertex: '+obj.name+' '+str(v.index))
  total=sum(w for i,w in skin);vertex_skin.append(([(i) for i,w in skin]+[0]*(4-len(skin)),[w/total for i,w in skin]+[0.]*(4-len(skin))))
 for tri in mesh.loop_triangles:
  mat=mesh.materials[tri.material_index] if tri.material_index<len(mesh.materials) else None;mi=material_index(mat);face=[]
  for li in tri.loops:
   vi=mesh.loops[li].vertex_index;v=mesh.vertices[vi];face.append(len(positions));positions.append(list(world@v.co));normals.append(list((normal_matrix@mesh.corner_normals[li].vector).normalized()));uv.append(list(layer.data[li].uv) if layer else [.5,.5]);bi,bw=vertex_skin[vi];indices.append(bi);weights.append(bw)
  if world.determinant()<0:face[1],face[2]=face[2],face[1]
  faces.append(face);face_materials.append(mi)
 parts.append({'name':obj.name,'first_vertex':start,'vertex_count':len(positions)-start})
if not positions:raise ValueError('No weighted authored character meshes')
np.savez_compressed(out/'source.npz',positions=np.asarray(positions,dtype='<f4'),normals=np.asarray(normals,dtype='<f4'),uv=np.asarray(uv,dtype='<f4'),faces=np.asarray(faces,dtype='<u4'),face_materials=np.asarray(face_materials,dtype='<i4'),bone_indices=np.asarray(indices,dtype='<u2'),bone_weights=np.asarray(weights,dtype='<f4'),inverse_bind=inverse_bind,bone_parents=np.asarray(parents,dtype='<i4'))
(out/'source.json').write_text(json.dumps({'source':source.name,'objects':parts,'materials':materials,'bone_names':bone_names,'bone_parents':parents,'excluded_objects':excluded,'explicit_rigid_attachments':rigid,'vertices':len(positions),'triangles':len(faces),'scripts_executed':False,'in_game_tested':False},indent=2)+'\n')
print('SKIN EXPORTED',len(positions),'vertices',len(faces),'triangles',len(bone_names),'bones; excluded',excluded)
