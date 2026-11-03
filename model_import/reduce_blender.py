"""Reduce an existing static visual, retaining authored materials and silhouette.

Trusted Blender only, --factory-startup --disable-autoexec. Never creates a
replacement shape. Produces a separate GLB and measured conversion report.
"""
import argparse,json,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--triangles',type=int,default=6000);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not 100<=a.triangles<=20000:raise ValueError('Review an explicit 100–20000 triangle target')
source=Path(a.source).resolve();out=Path(a.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source))
if any(o.type=='ARMATURE' for o in bpy.context.scene.objects):raise ValueError('Static reduction requires explicit pose baking for a skinned source')
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render];before=0;counts={};areas={}
for o in meshes:o.data.calc_loop_triangles();counts[o.name]=len(o.data.loop_triangles);before+=counts[o.name];areas[o.name]=sum(t.area for t in o.data.loop_triangles)
ratio=min(1.,a.triangles/max(before,1));bounds=[]
for o in meshes:
 low=[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)];high=[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)];bounds.append({'name':o.name,'before_bounds':[low,high]});bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 # Some OBJ-derived GLBs split every triangle into independent vertices.
 # Decimating that disconnected soup deletes isolated faces, creating holes.
 # Weld coincident positions within this authored object first; loop UV seams
 # and the original surface are retained, with no cross-object welding.
 bm=bmesh.new();bm.from_mesh(o.data);weld_before=len(bm.verts);span=max(max(v.co[i] for v in bm.verts)-min(v.co[i] for v in bm.verts) for i in range(3));bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=max(span*1e-7,1e-9));bounds[-1]['vertices_before_weld']=weld_before;bounds[-1]['vertices_after_weld']=len(bm.verts);bm.to_mesh(o.data);bm.free();o.data.update()
 if counts[o.name]>64:
  modifier=o.modifiers.new('Reviewed static decimation','DECIMATE');modifier.ratio=min(1.,max(64/counts[o.name],ratio));modifier.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
 o.data.calc_loop_triangles();bounds[-1]['triangles']=len(o.data.loop_triangles);bounds[-1]['after_bounds']=[[min((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)],[max((o.matrix_world@v.co)[i] for v in o.data.vertices) for i in range(3)]]
 ratio_area=sum(t.area for t in o.data.loop_triangles)/max(areas[o.name],1e-20);bounds[-1]['surface_area_ratio']=ratio_area
 if not .75<ratio_area<1.25:raise ValueError('Reduction lost or inflated too much authored surface: '+o.name)
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',export_animations=False,export_skins=False,export_apply=True)
report={'source':source.name,'source_triangles':before,'target_budget':a.triangles,'result_triangles':sum(x['triangles'] for x in bounds),'objects':bounds,'authored_geometry_reduced_not_replaced':True,'in_game_tested':False};out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
