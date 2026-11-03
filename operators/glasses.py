"""Original modeled wraparound shooting glasses, fitted to the inspected Shrek.

Separate curved shield and frame meshes; no branding or claimed manufacturer
model. Design reference: Wiley X Saber Advanced's brow/temples/shield layout.
"""
import numpy as np
from catgun.geometry import Mesh


def spline(points,steps=8):
    points=np.asarray(points,dtype=float);p=np.vstack([points[0],points,points[-1]]);result=[]
    for i in range(1,len(p)-2):
        a,b,c,d=p[i-1:i+3]
        for t in np.linspace(0,1,steps,endpoint=False):result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.asarray(result+[points[-1]])


def create(head_position):
    head=np.asarray(head_position,dtype=float);eye_z=head[2]+.0563
    radius=.225;angle=.68;front_y=head[1]-.302;center_y=front_y+radius
    def point(u,v,back=0):
        theta=(u*2-1)*angle;x=radius*np.sin(theta);y=center_y-radius*np.cos(theta)+back
        top=eye_z+.047-.012*(abs(theta)/angle)**2
        # Swept, rounded outer lens corners rather than a rectangular visor.
        bottom=eye_z-.047+.047*np.exp(-(x/.029)**2)+.060*(abs(theta)/angle)**6
        return np.array([head[0]+x,y,bottom+(top-bottom)*v])
    lens=Mesh();nx,ny=64,10;grids=[]
    for back in (0,.0014):
        grid=[]
        for j in range(ny+1):
            row=[]
            for i in range(nx+1):
                u=i/nx;theta=(u*2-1)*angle;normal=np.array([np.sin(theta),-np.cos(theta),0.])*(1 if back==0 else -1);row.append(len(lens.vertices));lens.vertices.append(point(u,j/ny,back).tolist());lens.normals.append(normal.tolist());lens.uv.append([u,j/ny])
            grid.append(row)
        grids.append(grid)
        for j in range(ny):
            for i in range(nx):
                a,b,c,d=grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i];lens.face(a,b,c);lens.face(a,c,d)
    boundary=[(i,0) for i in range(nx+1)]+[(nx,j) for j in range(1,ny+1)]+[(i,ny) for i in range(nx-1,-1,-1)]+[(0,j) for j in range(ny-1,0,-1)]
    for (i,j),(ii,jj) in zip(boundary,boundary[1:]+boundary[:1]):
        a,b=grids[0][j][i],grids[0][jj][ii];c,d=grids[1][jj][ii],grids[1][j][i];lens.face(a,b,c);lens.face(a,c,d)
    lens.parts=[{'name':'separate rust-tinted curved shield','first_vertex':0,'vertex_count':len(lens.vertices)}]
    frame=Mesh();brow=np.asarray([point(u,1)+[0,.0008,.0018] for u in np.linspace(0,1,65)])
    frame.tube('continuous upper brow',brow,np.full(len(brow),.0042),0,10)
    for side,u in [(-1,0),(1,1)]:
        start=point(u,1)+[0,.001,.001];points=[start,[head[0]+side*.149,head[1]-.223,eye_z+.033],[head[0]+side*.158,head[1]-.16,eye_z+.025],[head[0]+side*.158,head[1]-.10,eye_z+.017],[head[0]+side*.153,head[1]-.061,eye_z+.003],[head[0]+side*.149,head[1]-.040,eye_z-.028]];curve=spline(points)
        frame.tube('telescopic temple '+str(side),curve,np.linspace(.004,.0055,len(curve)),0,10)
        pad=spline([[head[0]+side*.012,front_y+.007,eye_z+.005],[head[0]+side*.019,front_y+.017,eye_z-.009],[head[0]+side*.024,front_y+.024,eye_z-.021]],6)
        frame.tube('flexible nose pad '+str(side),pad,np.full(len(pad),.0035),0,10)
    return frame,lens,{'title':'Original wraparound shooting glasses, rust shield','author':'MWC','license':'MIT','design_reference':'https://www.wileyx.com/products/saber-advanced-309','manufacturer_model_used':False,'separate_shield':True,'head_attachment':True,'in_game_tested':False}
