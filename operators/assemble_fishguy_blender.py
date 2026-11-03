"""Assemble a reviewable Fishguy from existing body and sardine meshes.

Trusted Blender only. Retains the body's rig, cuts the original human head,
and weights a separate, vertically oriented stylized sardine head to Head.
This is an assembly prototype; Combat Master rig/animation acceptance follows.
"""
import argparse,json,sys,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix

p=argparse.ArgumentParser();p.add_argument('body');p.add_argument('body_texture');p.add_argument('sardine_obj');p.add_argument('output');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(Path(a.body).resolve()),use_anim=False)
armature=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH');armature.data.pose_position='REST';armature.animation_data_clear();bpy.context.view_layer.update()
for m in body.data.materials:
 m.use_nodes=True;bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.7;tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(Path(a.body_texture).resolve()),check_existing=True);m.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])

def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.8
 return m

head_name=next(b.name for b in armature.data.bones if b.name.endswith(':Head'))
neck=armature.matrix_world@armature.data.bones[head_name].head_local
cut=neck.z-.016
bm=bmesh.new();bm.from_mesh(body.data);before=len(bm.verts)
local=body.matrix_world.inverted()@Vector((0,0,cut));normal=body.matrix_world.to_3x3().transposed()@Vector((0,0,1))
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=local,plane_no=normal,clear_outer=True,clear_inner=False)
bm.to_mesh(body.data);bm.free();body.data.update();deleted=before-len(body.data.vertices)
# Extend the existing clothing over the original authored leg topology. The
# original belt/shorts and original shoes remain; no primitive body substitute.
denim=material('Fishguy blue jeans',(.025,.075,.20));body.data.materials.append(denim);denim_index=len(body.data.materials)-1
leg_groups={g.index for g in body.vertex_groups if g.name.endswith(('UpLeg','Leg'))}
for polygon in body.data.polygons:
 influence=sum(sum(g.weight for g in body.data.vertices[i].groups if g.group in leg_groups) for i in polygon.vertices)/len(polygon.vertices)
 z=sum((body.matrix_world@body.data.vertices[i].co).z for i in polygon.vertices)/len(polygon.vertices)
 lateral=sum(abs((body.matrix_world@body.data.vertices[i].co).y) for i in polygon.vertices)/len(polygon.vertices)
 if influence>.55 or (-.435<z<-.10 and lateral<.15):polygon.material_index=denim_index
leg_axes=[]
for side in ('Left','Right'):
 knee=next(b for b in armature.data.bones if b.name.endswith(':'+side+'Leg'));ankle=next(b for b in armature.data.bones if b.name.endswith(':'+side+'Foot'));leg_axes.append((armature.matrix_world@knee.head_local,armature.matrix_world@ankle.head_local))
for v in body.data.vertices:
 influence=sum(g.weight for g in v.groups if g.group in leg_groups)
 world=body.matrix_world@v.co
 if -.435<world.z<-.16 and (influence>.35 or abs(world.y)<.15):
  # Loose denim allowance around each existing authored calf. Retain vertices,
  # topology and skin, rather than adding a rigid tube over an animated leg.
  knee,ankle=min(leg_axes,key=lambda points:abs(points[1].y-world.y));t=max(0.,min(1.,(world.z-knee.z)/(ankle.z-knee.z)));center=knee.lerp(ankle,t);radial=Vector((world.x-center.x,world.y-center.y,0));radius=radial.length
  if radius>1e-7:
   allowance=.010+.010*math.sin(math.pi*t);radial*=min(1.9,(radius+allowance)/radius);world.x=center.x+radial.x;world.y=center.y+radial.y
  v.co=body.matrix_world.inverted()@world

# Data-only OBJ import: authored sardine outline/topology, no MTL, scripts or
# external file execution. The source mesh is 98 vertices / 163 triangles.
vertices=[];faces=[]
for line in Path(a.sardine_obj).read_text().splitlines():
 fields=line.split()
 if not fields:continue
 if fields[0]=='v':vertices.append(tuple(map(float,fields[1:4])))
 elif fields[0]=='f':faces.append(tuple(int(x.split('/')[0])-1 for x in fields[1:]))
faces=[face for face in faces if all(i<94 for i in face)] # exclude original pectoral fins, not part of the head
mesh=bpy.data.meshes.new('Authored sardine head');mesh.from_pydata(vertices,[],faces);mesh.update();fish=bpy.data.objects.new('Fishguy sardine head',mesh);bpy.context.collection.objects.link(fish)
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(-2.8,0,0),plane_no=(1,0,0),clear_outer=True,clear_inner=False)
cut_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x+2.8)<1e-5 for v in e.verts)]
if cut_edges:bmesh.ops.holes_fill(bm,edges=cut_edges,sides=0)
bm.to_mesh(mesh);bm.free();mesh.update()
palette=[material('Sardine navy',(.018,.06,.12)),material('Sardine blue',(.04,.18,.36)),material('Sardine silver',(.46,.62,.78)),material('Sardine white',(.82,.89,.94))]
for m in palette:mesh.materials.append(m)
for poly in mesh.polygons:
 y=sum(mesh.vertices[v].co.y for v in poly.vertices)/len(poly.vertices)
 x=sum(mesh.vertices[v].co.x for v in poly.vertices)/len(poly.vertices)
 poly.material_index=0 if y>1.05 or (x<-4.55 and .30<y<.46) else 1 if y>.78 else 2 if y>.40 else 3;poly.use_smooth=False
mesh.calc_loop_triangles();source_triangles=[[mesh.vertices[i].co.copy() for i in p.vertices] for p in mesh.loop_triangles]
def surface_z(x,y,side):
 values=[]
 for triangle in source_triangles:
  aa,bb,cc=triangle;den=(bb.y-cc.y)*(aa.x-cc.x)+(cc.x-bb.x)*(aa.y-cc.y)
  if abs(den)<1e-9:continue
  u=((bb.y-cc.y)*(x-cc.x)+(cc.x-bb.x)*(y-cc.y))/den;v=((cc.y-aa.y)*(x-cc.x)+(aa.x-cc.x)*(y-cc.y))/den
  if min(u,v,1-u-v)>=-1e-5:values.append(u*aa.z+v*bb.z+(1-u-v)*cc.z)
 if not values:raise ValueError('Eye ring lies outside the authored sardine surface')
 return (max(values) if side>0 else min(values))+side*.035
rotation=Matrix(((0,0,1),(0,1,0),(-1,0,0)));scale=.10
center_y=(min(v.co.y for v in mesh.vertices)+max(v.co.y for v in mesh.vertices))/2
anchor=Vector((neck.x,neck.y,cut-.006))
def fit(v):
 v=Vector(v);v.y=(v.y-center_y)*1.2;v.z*=2.2;v.x+=2.8
 return rotation@v*scale+anchor
for v in mesh.vertices:v.co=fit(v.co)

def attach(obj):
 group=obj.vertex_groups.new(name=head_name);group.add(list(range(len(obj.data.vertices))),1.,'REPLACE');mod=obj.modifiers.new('Follow preserved head bone','ARMATURE');mod.object=armature
attach(fish)
# Separate modeled eye rings keep the flat-shaded sardine readable at gameplay
# distance. These embellish the real fish mesh; they do not replace its shape.
eye_materials=[material('Eye outline',(.008,.018,.035)),material('Eye iris',(.88,.64,.13)),material('Eye pupil',(.005,.008,.014))]
for side in (-1,1):
 verts=[];polys=[];mi=[];rings=[]
 for radius in (.28,.225,.12):
  ring=[]
  for k in range(20):
   theta=k*2*math.pi/20;x=-3.57+math.cos(theta)*radius;y=.65+math.sin(theta)*radius;ring.append(len(verts));verts.append(tuple(fit((x,y,surface_z(x,y,side)))))
  rings.append(ring)
 for j in range(2):
  for k in range(20):polys.append((rings[j][k],rings[j][(k+1)%20],rings[j+1][(k+1)%20],rings[j+1][k]));mi.append(j)
 polys.append(tuple(rings[2]));mi.append(2)
 e=bpy.data.meshes.new('Sardine eye');e.from_pydata(verts,[],polys);e.update();obj=bpy.data.objects.new('Fishguy eye '+str(side),e);bpy.context.collection.objects.link(obj)
 for m in eye_materials:e.materials.append(m)
 for poly,index in zip(e.polygons,mi):poly.material_index=index
 attach(obj)

body.name='Fishguy muscular body and jeans';armature.name='Fishguy preserved body skeleton'
for image in bpy.data.images:
 if image.source=='FILE' and image.has_data:image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(out))
bpy.ops.export_scene.gltf(filepath=str(out.with_suffix('.glb')),export_format='GLB',export_animations=False)
report={'status':'assembled prototype; not installed or tested in-game','human_head_vertices_removed':deleted,'body_vertices':len(body.data.vertices),'sardine_head_vertices':len(mesh.vertices),'head_bone':head_name,'preserved_body_bones':len(armature.data.bones),'head_separate':True,'style':'Flat-shaded blue/silver/white sardine, modeled yellow eye rings, blue jeans','sources':{'body':'https://github.com/andrisgauracs/bodybuilder_unity (MIT declared in README; existing AI-assisted model)','sardine':'https://github.com/atkonn/jinbei3d (Apache 2.0; QSDN Inc. and Atsushi Konno 2011)'},'remaining':['Combat Master rig fitting','Clothing seam and neck transition review','Gameplay animation and helicopter acceptance']}
out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
