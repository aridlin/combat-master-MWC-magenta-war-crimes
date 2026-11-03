"""An original, deterministic cat mesh. No downloaded or game geometry."""
import io
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

PALETTE=[(110,116,123),(223,215,198),(47,51,58),(213,162,57),(9,13,17),(201,121,136),(146,134,114),(235,231,219)]


class Mesh:
    def __init__(self): self.vertices=[]; self.normals=[]; self.uv=[]; self.faces=[]; self.parts=[]
    def vertex(self,p,n,color):
        self.vertices.append(tuple(p)); self.normals.append(tuple(n)); self.uv.append(((color+.5)/len(PALETTE),.5))
        return len(self.vertices)-1
    def face(self,a,b,c):
        v=np.array([self.vertices[i] for i in (a,b,c)])
        n=np.array([self.normals[i] for i in (a,b,c)]).mean(axis=0)
        if np.dot(np.cross(v[1]-v[0],v[2]-v[0]),n)<0: b,c=c,b
        self.faces.append((a,b,c))
    def ellipsoid(self,name,center,radii,color,rings=10,segments=20):
        start=len(self.vertices); center=np.array(center); radii=np.array(radii)
        top=self.vertex(center+[0,0,radii[2]],(0,0,1),color)
        ring=[]
        for r in range(1,rings):
            theta=np.pi*r/rings; row=[]
            for s in range(segments):
                phi=2*np.pi*s/segments; unit=np.array([np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),np.cos(theta)])
                normal=unit/radii; normal/=np.linalg.norm(normal)
                row.append(self.vertex(center+radii*unit,normal,color))
            ring.append(row)
        bottom=self.vertex(center-[0,0,radii[2]],(0,0,-1),color)
        for s in range(segments):
            j=(s+1)%segments; self.face(top,ring[0][s],ring[0][j]); self.face(bottom,ring[-1][j],ring[-1][s])
        for a,b in zip(ring[:-1],ring[1:]):
            for s in range(segments):
                j=(s+1)%segments; self.face(a[s],b[s],a[j]); self.face(a[j],b[s],b[j])
        self.parts.append({'name':name,'first_vertex':start,'vertex_count':len(self.vertices)-start})
    def tube(self,name,points,radii,color,segments=10):
        start=len(self.vertices); rows=[]; points=np.array(points,dtype=float)
        for i,p in enumerate(points):
            tangent=points[min(i+1,len(points)-1)]-points[max(0,i-1)]; tangent/=np.linalg.norm(tangent)
            ref=np.array([0.,0.,1.]) if abs(tangent[2])<.9 else np.array([0.,1.,0.])
            u=np.cross(tangent,ref); u/=np.linalg.norm(u); v=np.cross(tangent,u)
            row=[]
            for s in range(segments):
                angle=s*2*np.pi/segments; n=np.cos(angle)*u+np.sin(angle)*v
                row.append(self.vertex(p+radii[i]*n,n,color))
            rows.append(row)
        for a,b in zip(rows[:-1],rows[1:]):
            for i in range(segments):
                j=(i+1)%segments; self.face(a[i],b[i],a[j]); self.face(a[j],b[i],b[j])
        self.parts.append({'name':name,'first_vertex':start,'vertex_count':len(self.vertices)-start})
    def triangle(self,name,points,color):
        a,b,c=np.array(points); n=np.cross(b-a,c-a); n/=np.linalg.norm(n)
        indices=[self.vertex(p,n,color) for p in (a,b,c)]; self.face(*indices)
        self.parts.append({'name':name,'first_vertex':indices[0],'vertex_count':3})
    def arrays(self):
        return (np.asarray(self.vertices,dtype='<f4'),np.asarray(self.normals,dtype='<f4'),
                np.asarray(self.uv,dtype='<f4'),np.asarray(self.faces,dtype='<u4'))


def make_cat(scale=1.0):
    m=Mesh()
    m.ellipsoid('torso',(0,.18,.015),(.079,.225,.082),0,12,24)
    m.ellipsoid('cream_belly',(0,.175,-.033),(.069,.195,.055),1)
    m.ellipsoid('dark_saddle',(0,.17,.067),(.073,.178,.037),2)
    m.ellipsoid('neck',(0,.365,.041),(.065,.082,.07),0)
    m.ellipsoid('head',(0,.43,.075),(.077,.073,.073),0,12,24)
    for side in (-1,1):
        m.ellipsoid('cheek',(side*.026,.486,.055),(.031,.022,.027),1)
        m.ellipsoid('eye',(side*.037,.490,.098),(.018,.008,.015),3,8,16)
        m.ellipsoid('vertical_pupil',(side*.037,.497,.098),(.004,.003,.012),4,8,12)
        m.ellipsoid('eye_highlight',(side*.032,.500,.103),(.003,.0015,.003),7,6,8)
        for y in (.045,.32):
            m.ellipsoid('leg',(side*.055,y,-.069),(.025,.043,.068),0)
            m.ellipsoid('paw',(side*.056,y+.018,-.125),(.029,.043,.023),1)
        x=side*.052
        front=[(x-side*.031,.455,.122),(x+side*.028,.443,.127),(x+side*.013,.43,.215)]
        back=[(px,py-.022,pz) for px,py,pz in front]
        m.triangle('ear_front',front,0); m.triangle('ear_back',back[::-1],2)
        for i in range(3):
            j=(i+1)%3; m.triangle('ear_edge',[front[i],back[i],front[j]],0);m.triangle('ear_edge',[front[j],back[i],back[j]],0)
        center=np.mean(front,axis=0); inner=[center+(np.array(p)-center)*.64+np.array([0,.001,0]) for p in front]
        m.triangle('ear_pink',inner,5)
        # Whiskers are geometry, attached to the face, not screen overlays.
        for dz in (-.013,0,.013):
            m.tube('whisker',[(side*.027,.501,.058+dz),(side*.09,.495,.062+dz),(side*.137,.48,.069+dz)], [.0012,.0009,.00035],7,6)
    m.ellipsoid('nose',(0,.508,.065),(.011,.007,.008),5,8,12)
    m.tube('tail',[(0,-.023,.03),(.015,-.10,.025),(.055,-.18,.075),(.09,-.20,.13),(.105,-.17,.17)], [.023,.022,.020,.016,.008],0,12)
    if scale!=1:
        m.vertices=[tuple(np.array(v)*scale) for v in m.vertices]
    return m


def palette_image():
    image=Image.new('RGB',(256,32))
    draw=ImageDraw.Draw(image)
    for i,color in enumerate(PALETTE): draw.rectangle((i*32,0,(i+1)*32-1,31),fill=color)
    return image


def export(mesh,directory,texture=None,prefix="cat",description="Original MWC cat mesh, Z up, +Y muzzle direction"):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    v,n,uv,f=mesh.arrays(); coat=texture if texture is not None else palette_image();coat.save(directory/(prefix+'-palette.png'))
    with (directory/(prefix+'.obj')).open('w') as stream:
        stream.write('# '+description+'\nmtllib '+prefix+'.mtl\nusemtl CatCoat\n')
        for p in v: stream.write('v '+' '.join(map(str,p))+'\n')
        for p in uv: stream.write('vt '+' '.join(map(str,p))+'\n')
        for p in n: stream.write('vn '+' '.join(map(str,p))+'\n')
        for face in f: stream.write('f '+' '.join(f'{int(i)+1}/{int(i)+1}/{int(i)+1}' for i in face)+'\n')
    (directory/(prefix+'.mtl')).write_text('newmtl CatCoat\nKd 1 1 1\nKs 0.08 0.08 0.08\nNs 12\nmap_Kd '+prefix+'-palette.png\n')
    # GLB uses standard Y-up coordinates; the Unity-native OBJ remains Z-up.
    gv=v[:,[0,2,1]].copy();gv[:,2]*=-1;gn=n[:,[0,2,1]].copy();gn[:,2]*=-1
    image_io=io.BytesIO();coat.save(image_io,format='PNG')
    blobs=[gv.tobytes(),gn.tobytes(),uv.tobytes(),f.tobytes(),image_io.getvalue()]
    binary=bytearray(); views=[]
    for blob in blobs:
        while len(binary)%4: binary.append(0)
        views.append({'buffer':0,'byteOffset':len(binary),'byteLength':len(blob)})
        binary.extend(blob)
    document={'asset':{'version':'2.0','generator':'Combat Master MWC original procedural '+prefix},
        'buffers':[{'byteLength':len(binary)}],'bufferViews':views,
        'accessors':[{'bufferView':0,'componentType':5126,'count':len(v),'type':'VEC3','min':gv.min(axis=0).tolist(),'max':gv.max(axis=0).tolist()},
                     {'bufferView':1,'componentType':5126,'count':len(n),'type':'VEC3'},
                     {'bufferView':2,'componentType':5126,'count':len(uv),'type':'VEC2'},
                     {'bufferView':3,'componentType':5125,'count':f.size,'type':'SCALAR'}],
        'images':[{'bufferView':4,'mimeType':'image/png'}],'samplers':[{'magFilter':9729,'minFilter':9729}],
        'textures':[{'source':0,'sampler':0}],
        'materials':[{'name':'CatCoat','pbrMetallicRoughness':{'baseColorTexture':{'index':0},'metallicFactor':0,'roughnessFactor':.8}}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2},'indices':3,'material':0}]}],
        'nodes':[{'mesh':0,'name':'MWC_'+prefix}],'scenes':[{'nodes':[0]}],'scene':0}
    js=json.dumps(document,separators=(',',':')).encode();js+=b' '*((-len(js))%4);binary+=b'\0'*((-len(binary))%4)
    glb=struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(binary))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    (directory/(prefix+'.glb')).write_bytes(glb)
    stats={'vertices':len(v),'triangles':len(f),'bounds_min':v.min(axis=0).tolist(),'bounds_max':v.max(axis=0).tolist(),'parts':mesh.parts,'source':description}
    (directory/'mesh-info.json').write_text(json.dumps(stats,indent=2)+'\n')
    return stats


def render(mesh,path,eye=(.9,.8,.45),width=1000,height=700,texture=None,label=None,target=None):
    """Small deterministic shaded preview, explicitly not a game screenshot."""
    v,n,uv,faces=mesh.arrays(); eye=np.asarray(eye,dtype=float);target=np.asarray([0,.17,.025] if target is None else target,dtype=float);tex=np.asarray(texture.convert('RGB')) if texture is not None else None
    forward=target-eye;forward/=np.linalg.norm(forward);right=np.cross(forward,[0,0,1]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    projected=np.stack([(v-target)@right,(v-target)@up,(v-eye)@forward],axis=1)
    scale=min((width-80)/np.ptp(projected[:,0]),(height-100)/np.ptp(projected[:,1]))
    p=projected.copy();center_xy=(projected[:,:2].min(axis=0)+projected[:,:2].max(axis=0))/2
    p[:,0]=width/2+(p[:,0]-center_xy[0])*scale;p[:,1]=height/2-(p[:,1]-center_xy[1])*scale
    zbuffer=np.full((height,width),np.inf);pixels=np.full((height,width,3),(28,34,42),dtype=np.uint8)
    light=np.array([.25,.1,.96]);light/=np.linalg.norm(light)
    for face in faces:
        a,b,c=p[face];ns=n[face]
        if np.dot(ns.mean(axis=0),eye-v[face].mean(axis=0))<=0: continue
        x0,x1=max(0,int(np.floor(min(a[0],b[0],c[0])))),min(width-1,int(np.ceil(max(a[0],b[0],c[0]))))
        y0,y1=max(0,int(np.floor(min(a[1],b[1],c[1])))),min(height-1,int(np.ceil(max(a[1],b[1],c[1]))))
        if x1<x0 or y1<y0: continue
        x,y=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-10: continue
        w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
        w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w2=1-w0-w1
        depth=w0*a[2]+w1*b[2]+w2*c[2];region=zbuffer[y0:y1+1,x0:x1+1]
        mask=(w0>=0)&(w1>=0)&(w2>=0)&(depth<region)
        normal=w0[...,None]*ns[0]+w1[...,None]*ns[1]+w2[...,None]*ns[2];normal/=np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-8)
        diffuse=.23+.77*np.maximum(0,normal@light)
        if texture is None:
            base=np.array(PALETTE[min(len(PALETTE)-1,int(uv[face[0],0]*len(PALETTE)))])/255
            base=base[None,None,:]
        else:
            pixels_uv=w0[...,None]*uv[face[0]]+w1[...,None]*uv[face[1]]+w2[...,None]*uv[face[2]]
            tx=np.clip((pixels_uv[...,0]*tex.shape[1]).astype(int),0,tex.shape[1]-1)
            ty=np.clip(((1-pixels_uv[...,1])*tex.shape[0]).astype(int),0,tex.shape[0]-1)
            base=tex[ty,tx]/255
        shade=np.rint(np.clip(base*diffuse[...,None],0,1)*255).astype(np.uint8)
        pixels[y0:y1+1,x0:x1+1][mask]=shade[mask];region[mask]=depth[mask]
    image=Image.fromarray(pixels);d=ImageDraw.Draw(image)
    d.text((20,18),label or 'MWC Lynx cat | generated mesh preview — not in-game',fill='white')
    image.save(path)
