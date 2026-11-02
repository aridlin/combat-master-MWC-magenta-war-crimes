"""Original code-built meshes, +Y forward / Z up, in metres."""
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from catgun.geometry import Mesh,render

PALETTES={
 'scorpion':[(105,43,22),(44,25,21),(179,78,29),(231,171,80),(12,9,8),(246,224,178),(128,42,21),(157,140,104)],
 'fishing_rod':[(43,53,57),(24,28,30),(157,112,61),(174,187,191),(169,220,219),(211,169,69),(169,48,39),(10,13,15)],
 'nail_gun':[(235,177,27),(29,32,34),(159,169,170),(67,74,78),(193,46,37),(230,229,213),(51,99,132),(204,210,208)],
 'toaster':[(174,182,185),(28,31,33),(151,85,39),(233,190,125),(200,47,35),(32,34,35),(199,156,97),(236,233,219)]}


def box(m,name,center,size,color):
    start=len(m.vertices);c=np.array(center,dtype=float);s=np.array(size)/2
    for axis in range(3):
        for sign in [-1,1]:
            normal=np.zeros(3);normal[axis]=sign;other=[i for i in range(3) if i!=axis];ids=[]
            for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                p=c.copy();p[axis]+=sign*s[axis];p[other[0]]+=a*s[other[0]];p[other[1]]+=b*s[other[1]]
                ids.append(m.vertex(p,normal,color))
            m.face(ids[0],ids[1],ids[2]);m.face(ids[0],ids[2],ids[3])
    m.parts.append({'name':name,'first_vertex':start,'vertex_count':len(m.vertices)-start})


def ring(m,name,center,radius,tube,color,axis='y',segments=32):
    c=np.array(center);pts=[]
    for i in range(segments+1):
        a=2*math.pi*i/segments
        offset={'x':(0,math.cos(a)*radius,math.sin(a)*radius),'y':(math.cos(a)*radius,0,math.sin(a)*radius),'z':(math.cos(a)*radius,math.sin(a)*radius,0)}[axis]
        pts.append(c+offset)
    m.tube(name,pts,[tube]*len(pts),color,8)


def scorpion():
    m=Mesh();m.ellipsoid('armored_body',(0,.045,-.032),(.055,.105,.037),0,12,24)
    m.ellipsoid('head',(0,.150,-.030),(.049,.041,.027),2)
    for i,y in enumerate([-.025,.005,.035,.065,.095]):
        m.ellipsoid('segmented_carapace',(0,y,-.009),(.051,.018,.019),2 if i%2 else 0,8,20)
    for side in [-1,1]:
        for i,y in enumerate([-.018,.028,.073,.115]):
            dy=(i-1.5)*.018
            points=[(side*.037,y,-.045),(side*.080,y+dy,-.055),(side*.127,y+dy-.032,-.083),(side*.145,y+dy-.054,-.090)]
            m.tube('walking_leg',points,[.009,.008,.005,.0015],1,10)
            m.ellipsoid('leg_joint',points[1],(.010,.010,.010),0,6,10)
        m.tube('pincer_arm',[(side*.038,.15,-.035),(side*.068,.205,-.040),(side*.085,.255,-.032)],[.014,.017,.014],0,12)
        m.ellipsoid('claw_palm',(side*.084,.282,-.030),(.029,.045,.020),2,10,20)
        m.tube('outer_pincer',[(side*.103,.297,-.028),(side*.108,.336,-.026),(side*.087,.365,-.027)],[.014,.010,.001],0,12)
        m.tube('inner_pincer',[(side*.066,.303,-.027),(side*.058,.333,-.025),(side*.078,.354,-.027)],[.011,.008,.001],3,12)
        m.ellipsoid('eye',(side*.017,.181,-.006),(.005,.007,.004),4,6,10)
        m.ellipsoid('eye_glint',(side*.017,.184,-.003),(.0015,.002,.001),5,5,8)
    # Low lateral curl; the stinger never rises above the body/sight line.
    points=[(0,-.055,-.036),(-.045,-.102,-.048),(-.092,-.123,-.058),(-.124,-.094,-.066),(-.123,-.043,-.067),(-.093,-.013,-.065)]
    m.tube('low_curled_tail',points,[.019,.017,.014,.011,.009,.006],0,14)
    for p,r in zip(points[1:-1],[.019,.016,.013,.011]):m.ellipsoid('tail_segment',p,(r,r,r*.8),2,6,12)
    m.tube('stinger',[points[-1],(-.078,-.002,-.073),(-.069,.005,-.080)],[.010,.006,.0006],4,12)
    return m


def fishing_rod():
    m=Mesh()
    m.tube('cork_grip',[(0,-.205,-.012),(0,-.185,-.012),(0,-.02,-.012),(0,.005,-.012)],[.014,.016,.016,.012],2,20)
    for y in np.linspace(-.175,-.035,9):ring(m,'grip_wrap',(0,y,-.012),.016,.0012,1,'y',20)
    m.tube('carbon_rod',[(0,-.01,-.008),(0,.12,-.006),(0,.29,-.004),(0,.46,-.002),(0,.63,0),(0,.76,.004)],[.009,.007,.0055,.004,.0025,.0012],0,16)
    for y in [.10,.26,.43,.59,.72]:
        ring(m,'guide_mount',(0,y,-.003),.006,.0015,5,'y',16)
        ring(m,'line_guide',(0,y,-.018),.008,.0012,3,'y',20)
    m.tube('fishing_line',[(0,-.005,-.026),(0,.10,-.018),(0,.26,-.018),(0,.43,-.018),(0,.59,-.018),(0,.72,-.018),(0,.76,.004)],[.00045]*7,4,6)
    box(m,'reel_seat',(.029,-.035,-.034),(.044,.058,.017),1)
    m.tube('reel_axle',[(.016,-.035,-.041),(.075,-.035,-.041)],[.008,.008],3,16)
    for x in [.033,.066]:ring(m,'reel_flange',(x,-.035,-.041),.030,.004,3,'x',32)
    m.tube('reel_spool',[(.035,-.035,-.041),(.064,-.035,-.041)],[.024,.024],4,24)
    m.tube('crank',[(.075,-.035,-.041),(.083,-.065,-.060),(.100,-.065,-.060)],[.004,.004,.004],3,12)
    m.ellipsoid('crank_knob',(.104,-.065,-.060),(.010,.007,.007),1)
    m.tube('butt_cap',[(0,-.211,-.012),(0,-.202,-.012)],[.016,.016],1,20)
    return m


def nail_gun():
    m=Mesh()
    box(m,'yellow_housing',(0,.055,-.024),(.078,.165,.074),0)
    m.ellipsoid('rear_motor_cap',(0,-.030,-.024),(.038,.022,.035),1,10,20)
    box(m,'motor_panel',(0,.045,.016),(.062,.110,.010),3)
    for y in np.linspace(-.002,.091,8):box(m,'top_vent',(0,y,.022),(.045,.003,.002),1)
    m.tube('steel_nozzle',[(0,.127,-.010),(0,.215,-.010)],[.014,.010],2,20)
    m.tube('nose_tip',[(0,.211,-.010),(0,.230,-.010)],[.013,.013],3,20)
    for side in [-1,1]:m.tube('contact_safety',[(side*.017,.135,-.026),(side*.017,.229,-.026),(side*.007,.239,-.019)],[.003]*3,7,8)
    box(m,'rubber_grip',(0,-.024,-.095),(.042,.054,.095),1)
    for z in np.linspace(-.129,-.066,6):box(m,'grip_rib',(0,-.053,z),(.040,.004,.004),3)
    box(m,'trigger',(0,.018,-.063),(.013,.008,.021),4)
    box(m,'nail_magazine',(0,.075,-.100),(.027,.195,.032),3)
    box(m,'magazine_bottom',(0,.075,-.119),(.030,.191,.007),2)
    for y in np.linspace(.012,.150,13):box(m,'nail_strip',(.0145,y,-.101),(.002,.0025,.022),7)
    box(m,'brand_plate',(.040,.063,-.015),(.002,.060,.024),5)
    for y in [.045,.060,.075]:box(m,'plate_mark',(.0415,y,-.015),(.001,.006,.014),1)
    m.ellipsoid('mode_button',(-.041,.092,-.020),(.004,.009,.009),4,6,12)
    return m


def toaster():
    m=Mesh();box(m,'toaster_body',(0,.066,-.045),(.118,.245,.103),0)
    for side in [-1,1]:
        m.ellipsoid('rounded_side',(side*.056,.066,-.044),(.011,.116,.047),0,10,20)
        for y in [-.031,.164]:box(m,'rubber_foot',(side*.040,y,-.104),(.022,.025,.016),5)
    box(m,'top_panel',(0,.066,.010),(.113,.232,.010),7)
    # Bread stays low and to either side of the sight line.
    for side in [-1,1]:
        x=side*.027
        box(m,'bread_slot',(x,.066,.016),(.023,.174,.004),1)
        box(m,'toast_crust',(x,.066,.027),(.017,.145,.026),2)
        box(m,'bread_crumb',(x,.066,.030),(.018,.130,.018),3)
        for y in [-.022,.004,.030,.056,.082,.108,.134]:
            m.ellipsoid('toast_pore',(x+side*.0093,y,.030),(.0006,.002,.002),6,5,8)
    box(m,'lever_track',(.064,.070,-.036),(.003,.009,.070),1)
    box(m,'red_lever',(.074,.070,-.033),(.024,.025,.012),4)
    m.tube('browning_dial',[(.061,.132,-.061),(.072,.132,-.061)],[.014,.014],1,20)
    m.tube('dial_pointer',[(.073,.132,-.061),(.074,.137,-.052)],[.0015,.0015],7,8)
    for y in [.006,.033]:m.ellipsoid('control_button',(.067,y,-.060),(.004,.008,.008),7,6,12)
    # Low profile outlet marks the original muzzle direction, without a new
    # projectile or moved effect node.
    box(m,'front_outlet',(0,.195,-.020),(.030,.020,.026),1)
    box(m,'front_trim',(0,.206,-.020),(.036,.004,.031),6)
    return m


BUILDERS={'scorpion':scorpion,'fishing_rod':fishing_rod,'nail_gun':nail_gun,'toaster':toaster}


def make_model(name):return BUILDERS[name]()


def palette(name):
    image=Image.new('RGB',(256,32));draw=ImageDraw.Draw(image)
    for i,color in enumerate(PALETTES[name]):draw.rectangle((i*32,0,(i+1)*32-1,31),fill=color)
    return image


def export_model(name,directory):
    from catgun.geometry import export
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True);mesh=make_model(name)
    stats=export(mesh,directory,texture=palette(name),prefix=name,description='Original MWC '+name+' mesh, Z up, +Y muzzle direction')
    render(mesh,directory/'preview.png',texture=palette(name),label=name.replace('_',' ')+' | original mesh | software preview, not in-game')
    return stats
