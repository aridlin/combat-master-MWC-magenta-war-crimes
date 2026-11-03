"""Bake authored base-color/alpha node graphs to their existing UVs.

Trusted Blender only. No external scripts, lighting, or normal maps are baked
into the diffuse. Per-object material copies preserve vertex-color differences.
"""
import bpy,numpy as np


def bake(obj,slot,size=1024):
    original=obj.data.materials[slot]
    if not original or not original.use_nodes:return False
    bsdf=next((n for n in original.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if not bsdf:return False
    base=bsdf.inputs['Base Color'];alpha=bsdf.inputs['Alpha']
    if not base.is_linked or base.links[0].from_node.type=='TEX_IMAGE':return False
    if not obj.data.uv_layers.active:raise ValueError('Material bake needs original authored UVs: '+obj.name)
    mat=original.copy();mat.name=original.name+' baked '+obj.name;obj.data.materials[slot]=mat;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');surface=output.inputs['Surface'];previous=surface.links[0].from_socket if surface.is_linked else bsdf.outputs[0]
    base=bsdf.inputs['Base Color'];alpha=bsdf.inputs['Alpha'];color_socket=base.links[0].from_socket;alpha_socket=alpha.links[0].from_socket if alpha.is_linked else None;alpha_constant=alpha.default_value
    emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1;links.new(emission.outputs[0],surface)
    target=nodes.new('ShaderNodeTexImage');color_image=bpy.data.images.new(mat.name+' diffuse',size,size,alpha=True);target.image=color_image
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=2;scene.render.bake.margin=8
    # Other slots receive independent throwaway targets so Blender never bakes
    # into one of the original authored images while evaluating the whole mesh.
    temporary=[]
    for i,m in enumerate(obj.data.materials):
        if i==slot or not m or not m.use_nodes:continue
        node=m.node_tree.nodes.new('ShaderNodeTexImage');image=bpy.data.images.new('MWC temporary bake target',size,size,alpha=True);node.image=image;m.node_tree.nodes.active=node;temporary.append((m,node,image))
    try:
        nodes.active=target;links.new(color_socket,emission.inputs['Color']);bpy.ops.object.bake(type='EMIT',use_clear=True)
        pixels=np.asarray(color_image.pixels[:],dtype=np.float32).reshape(size,size,4)
        if alpha_socket:
            alpha_image=bpy.data.images.new(mat.name+' alpha bake',size,size,alpha=True);alpha_image.colorspace_settings.name='Non-Color';target.image=alpha_image;nodes.active=target;links.new(alpha_socket,emission.inputs['Color']);bpy.ops.object.bake(type='EMIT',use_clear=True);pixels[:,:,3]=np.asarray(alpha_image.pixels[:],dtype=np.float32).reshape(size,size,4)[:,:,0];bpy.data.images.remove(alpha_image)
        else:pixels[:,:,3]=alpha_constant
        target.image=color_image;color_image.pixels[:]=pixels.ravel();links.new(previous,surface);links.new(target.outputs['Color'],base);links.new(target.outputs['Alpha'],alpha);nodes.remove(emission)
    finally:
        for m,node,image in temporary:m.node_tree.nodes.remove(node);bpy.data.images.remove(image)
    return True
