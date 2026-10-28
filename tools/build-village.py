"""Build the editable Starry Night valley, gardens and market; export game data.

Run with Blender 4.5 LTS --background --factory-startup --python this_file.
Authoring coordinates below use the game's X / up-Y / Z convention. Blender
objects are converted to X / -Z / up-Y once, preserving a right-handed basis.
"""
import bpy
import math
import random
import json
import gzip
import base64
import struct
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'scene'
OUT.mkdir(exist_ok=True)
R = random.Random(1889)
TAU = math.tau
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)


def linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4


def color(s):
    return tuple(linear(int(s[i:i+2], 16) / 255) for i in (1, 3, 5))


def tint(c, strength=1):
    return tuple(min(1, v * strength) for v in c)


def height(x, z):
    def hill(cx, cz, sx, sz, a):
        return a * math.exp(-((x-cx)/sx)**2 - ((z-cz)/sz)**2)
    raw = 1.4 + 1.35*math.sin(x*.035+z*.012) + .95*math.cos(z*.044-x*.009)
    raw += hill(20, 100, 52, 58, 19) + hill(-52, 65, 43, 52, 25)
    raw += hill(102, 7, 61, 98, 14) + hill(-109, -71, 62, 81, 10)
    raw += hill(30, -185, 100, 53, 17) + hill(175, -140, 75, 90, 13)
    plaza = math.exp(-(((x-5)/22)**4 + ((z+22)/23)**4))
    return raw*(1-plaza) + 2.4*plaza


def road_height(x, z):
    return height(x, z) + .12


def lerp(a, b, t):
    return tuple(x+(y-x)*t for x, y in zip(a, b))


def path_samples(points, per_segment=20):
    result = []
    for i in range(len(points)-1):
        a, b, c, d = points[max(0,i-1)], points[i], points[i+1], points[min(len(points)-1,i+2)]
        for j in range(per_segment):
            t = j/per_segment
            result.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in range(2)))
    result.append(tuple(points[-1]))
    return result


MAIN_PATH = [(14,105),(11,87),(14,67),(21,48),(16,28),(3,8),(-7,-7),(0,-17)]
STREETS = [MAIN_PATH,
    [(-7,-7),(-33,-18),(-57,-30),(-79,-61),(-91,-100)],
    [(0,-17),(28,-20),(49,-34),(66,-58),(75,-92),(70,-128)],
    [(6,-43),(7,-65),(1,-88),(-8,-113),(-4,-143)],
    [(-57,-30),(-37,-48),(-16,-62),(7,-65),(34,-64),(66,-58)],
    [(-79,-61),(-62,-81),(-35,-91),(1,-88),(43,-97),(75,-92)],
    [(-48,82),(-43,64),(-33,49),(-11,39),(16,28)],
    [(49,-34),(80,-17),(109,11),(127,48)]]
PATHS = [path_samples(p) for p in STREETS]


def distance_to_roads(x,z):
    return min(math.hypot(x-px,z-pz) for road in PATHS+globals().get('DISTANT_PATHS',[]) for px,pz in road[::3])


material_specs = {
    'plaster': {'texture':'plaster', 'roughness': .92, 'underpaint':'#929689', 'underpaintStrength':.055},
    'roof': {'texture':'slate', 'roughness': .9, 'underpaint':'#798b98', 'underpaintStrength':.035},
    'stone': {'texture':'stone', 'roughness': 1},
    'wallstone': {'texture':'wallstone', 'normal':'wallstone-normal', 'normalScale':.65, 'roughness':1},
    'drywall': {'texture':'drywall', 'normal':'drywall-normal', 'normalScale':.60, 'roughness':1, 'underpaint':'#b2a390', 'underpaintStrength':.085},
    'mortar': {'texture':'drywall', 'roughness':1, 'underpaint':'#99978a', 'underpaintStrength':.048},
    'moss': {'texture':'moss', 'normal':'moss-normal', 'normalScale':.42, 'roughness':1, 'transparent':True, 'underpaint':'#8d9798', 'underpaintStrength':.038},
    'ground_moss': {'texture':'moss', 'normal':'moss-normal', 'normalScale':.42, 'roughness':1, 'transparent':True},
    'damp_earth': {'texture':'earth', 'roughness':1, 'transparent':True},
    'earth': {'texture':'earth', 'roughness': 1},
    'path': {'texture':'path', 'roughness':1},
    'leaves': {'texture':'leaves', 'roughness': 1, 'doubleSided':True},
    'cypress': {'texture':'cypress', 'roughness':1},
    'wood': {'texture':'wood', 'roughness':1},
    'mountain': {'texture':'mountain', 'roughness':1},
    'dark': {'roughness':1},
    'window': {'roughness':.65, 'emission':'#ffc064', 'emissionStrength':1.25},
    'window_far': {'roughness':1, 'emission':'#d5b484', 'emissionStrength':.48},
    'brush': {'texture':'leaves', 'roughness':1, 'doubleSided':True},
    'cloth': {'texture':'plaster', 'roughness':1, 'doubleSided':True},
    'water': {'roughness':.28, 'doubleSided':True},
}
materials = {}
for name, spec in material_specs.items():
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = spec['roughness']
    col = m.node_tree.nodes.new('ShaderNodeVertexColor')
    col.layer_name = 'Pigment'
    if spec.get('transparent'):
        m.surface_render_method='DITHERED'
        m.node_tree.links.new(col.outputs['Alpha'],bsdf.inputs['Alpha'])
    if 'texture' in spec:
        tex = m.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(OUT/'textures'/f"{spec['texture']}.png"))
        tex.image.pack()
        # The current Mix node lets glTF recognize both the RGB pigment and
        # its feathered alpha; legacy MixRGB silently loses COLOR_0 with alpha.
        mix = m.node_tree.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1
        m.node_tree.links.new(col.outputs['Color'], mix.inputs[6])
        m.node_tree.links.new(tex.outputs['Color'], mix.inputs[7])
        m.node_tree.links.new(mix.outputs[2],bsdf.inputs['Base Color'])
    else:
        m.node_tree.links.new(col.outputs['Color'],bsdf.inputs['Base Color'])
    if 'emission' in spec:
        bsdf.inputs['Emission Color'].default_value = (*color(spec['emission']),1)
        bsdf.inputs['Emission Strength'].default_value = spec['emissionStrength']
    if 'normal' in spec:
        relief=m.node_tree.nodes.new('ShaderNodeTexImage')
        relief.image=bpy.data.images.load(str(OUT/'textures'/f"{spec['normal']}.png"))
        relief.image.colorspace_settings.name='Non-Color';relief.image.pack()
        bump=m.node_tree.nodes.new('ShaderNodeNormalMap')
        bump.inputs['Strength'].default_value=spec['normalScale']
        m.node_tree.links.new(relief.outputs['Color'],bump.inputs['Color'])
        m.node_tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    materials[name] = m


class Mesh:
    def __init__(self, name, mat):
        self.name, self.mat = name, mat
        self.verts, self.faces, self.uv, self.colors = [], [], [], []

    def face(self, verts, col, uv=None):
        n = len(self.verts)
        self.verts.extend(verts)
        self.faces.append(tuple(range(n,n+len(verts))))
        self.colors.extend([col]*len(verts))
        if uv is None:
            # Align the brushwork with the dominant surface plane.
            normal = (Vector(verts[1])-Vector(verts[0])).cross(Vector(verts[2])-Vector(verts[0]))
            axis = max(range(3),key=lambda k:abs(normal[k]))
            axes = (0,2) if axis==1 else (0,1) if axis==2 else (2,1)
            scale = .28 if self.mat in ('stone','plaster') else .43 if self.mat in ('wallstone','drywall','mortar') else 1.3 if self.mat in ('moss','ground_moss') else .18
            uv = [(p[axes[0]]*scale,p[axes[1]]*scale) for p in verts]
        self.uv.extend(uv)


meshes = {}


def batch(mat, x=0, z=0, group='land'):
    cell = 100 if group != 'terrain' else 180
    key = (group,mat,math.floor(x/cell),math.floor(z/cell))
    if key not in meshes:
        meshes[key]=Mesh('_'.join(map(str,key)),mat)
    return meshes[key]


def transform(v, center, yaw):
    x,y,z=v
    co,si=math.cos(yaw),math.sin(yaw)
    return (center[0]+x*co+z*si,center[1]+y,center[2]-x*si+z*co)


def box(mat, center, dims, col, yaw=0, group='village', bevel=0):
    x,y,z=center
    w,h,d=(s*.5 for s in dims)
    b=batch(mat,x,z,group)
    # Chamfered boxes use explicit faces so the game and Blender agree exactly.
    if bevel > 0:
        r=min(bevel,w*.3,h*.3,d*.3)
        ring=[(-w+r,-d), (w-r,-d),(w,-d+r),(w,d-r),(w-r,d),(-w+r,d),(-w,d-r),(-w,-d+r)]
        lower=[transform((a,-h+r,c),center,yaw) for a,c in ring]
        upper=[transform((a,h-r,c),center,yaw) for a,c in ring]
        top=[transform((a*(w-r)/w,h,c*(d-r)/d),center,yaw) for a,c in ring]
        bottom=[transform((a*(w-r)/w,-h,c*(d-r)/d),center,yaw) for a,c in ring]
        for i in range(8):
            j=(i+1)%8
            b.face([lower[i],upper[i],upper[j],lower[j]],tint(col,.86+.13*(i%3)))
            b.face([upper[i],top[i],top[j],upper[j]],tint(col,1.15))
            b.face([bottom[i],lower[i],lower[j],bottom[j]],tint(col,.84))
        b.face(list(reversed(top)),tint(col,1.12))
        b.face(bottom,tint(col,.7))
    else:
        vs=[transform(v,center,yaw) for v in [(-w,-h,-d),(w,-h,-d),(w,h,-d),(-w,h,-d),(-w,-h,d),(w,-h,d),(w,h,d),(-w,h,d)]]
        for f,shade in [((0,3,2,1),.87),((4,5,6,7),1),((0,4,7,3),.92),((1,2,6,5),1.02),((3,7,6,2),1.12),((0,1,5,4),.7)]:
            b.face([vs[i] for i in f],tint(col,shade))


def ribbon(points,width,mat,col,raise_y=.14,group='roads'):
    normals=[]
    for j in range(len(points)):
        a,b=points[max(0,j-1)],points[min(len(points)-1,j+1)]
        dx,dz=b[0]-a[0],b[1]-a[1];length=max(.0001,math.hypot(dx,dz))
        normals.append((-dz/length,dx/length))
    for i in range(len(points)-1):
        p,q=points[i],points[i+1]
        dx,dz=q[0]-p[0],q[1]-p[1]
        length=math.hypot(dx,dz)
        if length<.001:continue
        # Three bands soften the edge using ochre/olive pigment, without transparency.
        for a,c in [(-1,-.84),(-.84,.84),(.84,1)]:
            verts=[]
            for pt,s in [(p,a),(q,a),(q,c),(p,c)]:
                nx,nz=normals[i+(1 if pt is q else 0)]
                xx=pt[0]+nx*width*.5*s;zz=pt[1]+nz*width*.5*s
                verts.append((xx,height(xx,zz)+raise_y,zz))
            b=batch(mat,p[0],p[1],group)
            uv=[((s+1)*.5,(i+(1 if pt is q else 0))*.16) for pt,s in [(p,a),(q,a),(q,c),(p,c)]] if mat=='path' else None
            b.face(list(reversed(verts)),tint(col,.90 if abs(a)==1 or c==1 else 1),list(reversed(uv)) if uv else None)
            if group=='lanes' and mat=='path':
                b.colors[-4:]=[lane_pigment(v[0],v[2],s,col) for v,s in zip(reversed(verts),[c,c,a,a])]


print('Building the painted valley...',flush=True)
exec(compile((ROOT/'tools/village-surfaces.py').read_text(encoding='utf-8'),
             str(ROOT/'tools/village-surfaces.py'),'exec'),globals())
# A shared regular heightfield is exported for triangle-exact flight clearance.
GRID_N=225
GRID_SPAN=672
GRID_STEP=GRID_SPAN/(GRID_N-1)
grid=[height(-GRID_SPAN/2+ix*GRID_STEP,-GRID_SPAN/2+iz*GRID_STEP) for iz in range(GRID_N) for ix in range(GRID_N)]
earth_palette=[color(c) for c in ['#556d57','#a4945c','#c2a367','#6f876f','#bba96e']]
for iz in range(GRID_N-1):
    for ix in range(GRID_N-1):
        x=-GRID_SPAN/2+ix*GRID_STEP;z=-GRID_SPAN/2+iz*GRID_STEP
        patch=.5+.33*math.sin(x*.045+z*.029)+.28*math.cos(z*.061-x*.021)
        col=lerp(earth_palette[0],earth_palette[2],max(0,min(1,patch)))
        col=tint(col,.95+R.random()*.07)
        verts=[(x,grid[iz*GRID_N+ix],z),(x,grid[(iz+1)*GRID_N+ix],z+GRID_STEP),(x+GRID_STEP,grid[(iz+1)*GRID_N+ix+1],z+GRID_STEP),(x+GRID_STEP,grid[iz*GRID_N+ix+1],z)]
        terrain_mesh=batch('earth',x,z,'terrain')
        terrain_mesh.face(verts,col)
        terrain_mesh.colors[-4:]=[surface_pigment(p[0],p[2]) for p in verts]

# Sample the very same triangles used by the browser's collision floor.
analytic_height=height
def height(x,z):
    u=max(0,min(GRID_N-1.00001,(x+GRID_SPAN/2)/GRID_STEP))
    v=max(0,min(GRID_N-1.00001,(z+GRID_SPAN/2)/GRID_STEP))
    ix,iz=int(u),int(v);fx,fz=u-ix,v-iz
    a=grid[iz*GRID_N+ix];b=grid[(iz+1)*GRID_N+ix]
    c=grid[(iz+1)*GRID_N+ix+1];d=grid[iz*GRID_N+ix+1]
    return a+(b-a)*fz+(c-b)*fx if fz>=fx else a+(d-a)*fx+(c-d)*fz

for i,p in enumerate(PATHS):
    ribbon(p,5.15 if i==0 else 4.2 if i<6 else 3.9,'path',color('#bfb392'),raise_y=.14+i*.003,group='lanes')
    for side in [-1,1]:
        # Flowing pale wheel ruts are brush strokes, not a paved grid.
        track=[]
        for j,(x,z) in enumerate(p):
            prev=p[max(0,j-1)];nxt=p[min(len(p)-1,j+1)]
            dx,dz=nxt[0]-prev[0],nxt[1]-prev[1];l=max(.01,math.hypot(dx,dz))
            track.append((x-dz/l*side*.94,z+dx/l*side*.94))
        for start in range(0,len(track)-1,9):
            ribbon(track[start:start+6],.12,'path',color('#a9a47d'),raise_y=.17,group='lane_brushes')

# Concentric paving bands interpolate the surface pigments across the plaza.
# Only 480 extra triangles; no new material, draw call or floating decals.
plaza=batch('path',3,-15,'lanes')
for ring in range(6):
    lo,hi=ring/6,(ring+1)/6
    for i in range(48):
        a=i/48*TAU;b=(i+1)/48*TAU
        pts=[(3+15*r*math.cos(t),-15+11*r*math.sin(t)) for r,t in
             ([(0,0),(hi,b),(hi,a)] if ring==0 else [(lo,a),(lo,b),(hi,b),(hi,a)])]
        plaza.face([(x,height(x,z)+.185,z) for x,z in pts],color('#ada68e'))
        plaza.colors[-len(pts):]=[plaza_pigment(x,z) for x,z in pts]

colliders=[]
house_records=[]
light_pools=[]


def collider(x,z,w,d,ymin,ymax,yaw=0,kind='building'):
    colliders.append(dict(x=x,z=z,hx=w/2,hz=d/2,yMin=ymin,yMax=ymax,cos=math.cos(yaw),sin=math.sin(yaw),kind=kind))


exec(compile((ROOT/'tools/village-organic.py').read_text(encoding='utf-8'),
             str(ROOT/'tools/village-organic.py'), 'exec'), globals())

def wall(points, side, tall=False):
    build_drywall(points,side,tall)

# Main lane begins between tall stone walls, opening as the church approaches.
wall(PATHS[0][:66],-1,True);wall(PATHS[0][:66],1,True)
wall(PATHS[0][66:104],-1,False);wall(PATHS[0][66:100],1,False)
wall(PATHS[6],-1,False)
wall(PATHS[1][35:85],1,False)


def roof(center,w,d,h,rise,yaw,col,group='village'):
    painted_roof(center,w,d,h,rise,yaw,col,group)



def arch(mat,center,w,h,col,yaw=0,group='village'):
    # A flat arched opening, framed separately; the facade behind stays solid.
    points=[(-w/2,0,0),(w/2,0,0),(w/2,h-w/2,0)]
    for i in range(1,13):
        a=i*math.pi/12
        points.append((math.cos(a)*w/2,h-w/2+math.sin(a)*w/2,0))
    pts=[transform(v,center,yaw) for v in points]
    b=batch(mat,center[0],center[2],group)
    for i in range(1,len(pts)-1):b.face([pts[0],pts[i],pts[i+1]],col)


exec(compile((ROOT/'tools/village-houses.py').read_text(encoding='utf-8'),
             str(ROOT/'tools/village-houses.py'), 'exec'), globals())


print('Building the church and terraced village...',flush=True)
# Landmark church: long nave, buttresses, arched openings, octagonal spire.
cx,cz=8,-31
base=height(cx,cz)+.3
church_color=color('#d6d2b8')
box('stone',(cx,base+.12,cz),(11,.7,22),color('#b7baa9'),bevel=.12)
box('plaster',(cx,base+4.4,cz),(9.2,8.5,20),church_color,bevel=.08)
roof((cx,base,cz),9.2,20,8.65,4.1,0,color('#667d8e'),'church')
for sign in [-1,1]:
    pts=[(cx-4.6,base+8.65,cz+sign*10),(cx+4.6,base+8.65,cz+sign*10),(cx+art_random(cx,cz,41).uniform(-.13,.13)*9.2,base+12.75,cz+sign*10)]
    if sign==-1:pts.reverse()
    batch('plaster',cx,cz,'church').face(pts,church_color)
    for zz in [-6,-1,4,8]:
        box('stone',(cx+sign*4.8,base+3.1,cz+zz),(.75,6.3,.85),tint(church_color,.9),bevel=.08)
        pos=(cx+sign*4.63,base+3.2,cz+zz-1.8)
        arch('dark',pos,1.35,3.4,color('#354c5a'),sign*math.pi/2,'church')
        arch('window',(pos[0]+sign*.03,pos[1]+.14,pos[2]),.98,3.0,color('#edca85'),sign*math.pi/2,'church')
# The tower sits on the near corner, as in the reference pass.
tx,tz=cx-1,cz+8.5
box('plaster',(tx,base+9.5,tz),(4.7,19,4.9),church_color,bevel=.1)
for y in [1,6.2,12.6,18.8]:
    box('stone',(tx,base+y,tz),(5.05,.27,5.22),color('#b8bcaf'),bevel=.06)
for side in [0,math.pi/2,math.pi,math.pi*1.5]:
    p=transform((0,14.3,2.47),(tx,base,tz),side)
    arch('dark',p,1.6,3.2,color('#2b424c'),side,'church')
    p=transform((0,14.45,2.5),(tx,base,tz),side)
    arch('window',p,1.12,2.7,color('#d5b367'),side,'church')
    box('stone',transform((0,15.8,2.57),(tx,base,tz),side),(.12,2.8,.19),church_color,side,'church')
arch('dark',(tx,base+.1,tz+2.48),2.55,4.5,color('#30464c'),0,'church')
arch('wood',(tx,base+.15,tz+2.51),2.14,4.1,color('#807556'),0,'church')
# Recessed entrance surround and two slim corner piers articulate the existing
# facade with the same stone batch; the doorway remains fully visible.
for side in [-1,1]:
    box('stone',(tx+side*2.22,base+6.7,tz+2.50),(.22,11.3,.17),color('#b9b4a0'),group='church')
for i in range(12):
    a=i*math.pi/12;b=(i+1)*math.pi/12
    batch('stone',tx,tz,'church').face([
        (tx+math.cos(a)*1.43,base+3.28+math.sin(a)*1.43,tz+2.56),
        (tx+math.cos(b)*1.43,base+3.28+math.sin(b)*1.43,tz+2.56),
        (tx+math.cos(b)*1.23,base+3.28+math.sin(b)*1.23,tz+2.56),
        (tx+math.cos(a)*1.23,base+3.28+math.sin(a)*1.23,tz+2.56)],color('#b8ad94'))
for i in range(5):box('stone',(tx,base-.06-i*.09,tz+2.7+i*.35),(3.7+i*.25,.22,.5),color('#bab69b'),group='church')
# Rose window: inset round disk and simple stone tracery.
for i in range(24):
    a=i*TAU/24;b=(i+1)*TAU/24
    batch('window',tx,tz,'church').face([(tx,base+8.9,tz+2.51),(tx+math.cos(a)*.76,base+8.9+math.sin(a)*.76,tz+2.51),(tx+math.cos(b)*.76,base+8.9+math.sin(b)*.76,tz+2.51)],color('#dfbc72'))
box('stone',(tx,base+8.9,tz+2.55),(.10,1.6,.09),church_color,group='church')
box('stone',(tx,base+8.9,tz+2.55),(1.6,.10,.09),church_color,group='church')
for i in range(8):
    a=i*TAU/8+math.pi/8;b=(i+1)*TAU/8+math.pi/8
    pts=[(tx+math.cos(a)*3.05,base+19,tz+math.sin(a)*3.05),(tx,base+28.5,tz),(tx+math.cos(b)*3.05,base+19,tz+math.sin(b)*3.05)]
    batch('roof',tx,tz,'church').face(pts,tint(color('#6c8793'),.77+i*.035))
box('wood',(tx,base+29.3,tz),(.12,2.1,.12),color('#acb5a4'),group='church')
box('wood',(tx,base+29.7,tz),(1.0,.12,.12),color('#acb5a4'),group='church')
collider(cx,cz,10.1,21.5,base-.4,base+12.6,0,'church')
collider(tx,tz,5.1,5.1,base,base+19,0,'tower')
collider(tx,tz,4,4,base+19,base+23.6,0,'spire')
collider(tx,tz,1.8,1.8,base+23.6,base+30.4,0,'spire')

# Full silhouettes are reserved before any mesh is built.
occupied=[(cx,cz,15)]
building_footprints.append(dict(x=cx,z=cz,hx=6.0,hz=12.0,yaw=0,kind='church'))
placement_roads=[(road,5.15 if i==0 else 4.2) for i,road in enumerate(PATHS)]
placement_roads.extend((path_samples(points,24),3.0) for _,_,points,_ in FAR_DISTRICTS)
near_layout=random.Random(20261022)
for road_index in [1,2,3,4,5]:
    road=PATHS[road_index]
    for j in range(6,len(road)-4,9):
        x,z=road[j];p=road[max(0,j-2)];q=road[min(len(road)-1,j+2)]
        dx,dz=q[0]-p[0],q[1]-p[1];l=math.hypot(dx,dz)
        for side in [-1,1]:
            style=(len(house_records)*5+road_index*2)%12
            if math.hypot(x-3,z+15)<31: style=4 if len(house_records)%2 else 7
            w=near_layout.uniform(5.3,7.7);d=near_layout.uniform(5.9,8.4);h=near_layout.uniform(4.9,6.5)
            plan=house_plan(w,d,h,style)
            front=max([oz+pd/2+.45 for ox,oz,pw,pd,*_ in plan['parts']]+[oz+pd/2 for ox,oz,pw,pd,kind in plan['reserved']])
            setback=front+3.1
            xx=x-dz/l*side*setback;zz=z+dx/l*side*setback
            yaw=math.atan2(dz/l*side,-dx/l*side)+near_layout.uniform(-.055,.055)
            fp=plan_footprints(plan,xx,zz,yaw)
            if not clear_house_site(fp,placement_roads):continue
            house(xx,zz,w,d,h,yaw,style,f'street-{road_index}')
# A second, sparse row follows the nearest street; the church remains framed by gaps.
for i in range(190):
    x=near_layout.uniform(-88,85);z=near_layout.uniform(-144,-30)
    w=near_layout.uniform(4.7,6.7);d=near_layout.uniform(5.4,7.2);h=near_layout.uniform(4.4,5.9)
    style=(i*5+3)%12;plan=house_plan(w,d,h,style)
    nearest=min(((math.hypot(x-px,z-pz),ri,j) for ri,road in enumerate(PATHS[1:6],1) for j,(px,pz) in enumerate(road[::3])),key=lambda v:v[0])
    if nearest[0]>22:continue
    ri,j=nearest[1],nearest[2]*3;road=PATHS[ri];p=road[max(0,j-1)];q=road[min(len(road)-1,j+1)]
    dx,dz=q[0]-p[0],q[1]-p[1];side=1 if (x-p[0])*(-dz)+(z-p[1])*dx>0 else -1
    yaw=math.atan2(dz*side,-dx*side)+near_layout.uniform(-.08,.08)
    fp=plan_footprints(plan,x,z,yaw)
    if not clear_house_site(fp,placement_roads):continue
    house(x,z,w,d,h,yaw,style,f'street-{ri}-outer')


def ellipsoid(mat,center,scale,col,seed=0,rings=6,sides=10,group='groves'):
    b=batch(mat,center[0],center[2],group)
    def point(j,i):
        phi=j/rings*math.pi;theta=i/sides*TAU
        noise=1+.085*math.sin(theta*3+phi*5+seed)+.055*math.cos(theta*5-phi*3+seed)
        return (center[0]+math.sin(phi)*math.cos(theta)*scale[0]*noise,center[1]+math.cos(phi)*scale[1],center[2]+math.sin(phi)*math.sin(theta)*scale[2]*noise)
    for j in range(rings):
        for i in range(sides):
            pts=[point(j,i),point(j+1,i),point(j+1,i+1),point(j,i+1)]
            shade=.86+.22*R.random()+.12*(1-j/rings)
            # Triangle fans avoid zero-area pole triangles in exported geometry.
            if j==0:pts=pts[:3]
            elif j==rings-1:pts=[pts[0],pts[1],pts[3]]
            b.face(list(reversed(pts)),tint(col,shade),[(i/sides,j/rings), (i/sides,(j+1)/rings),((i+1)/sides,(j+1)/rings),((i+1)/sides,j/rings)][:len(pts)])


def branch(a,b,r1,r2,col,group='groves'):
    v=Vector(b)-Vector(a);axis=v.normalized();right=axis.cross(Vector((0,0,1)))
    if right.length<.01:right=axis.cross(Vector((1,0,0)))
    right.normalize();up=axis.cross(right)
    mesh=batch('wood',a[0],a[2],group)
    for i in range(7):
        def p(c,r,k):return tuple(Vector(c)+(right*math.cos(k*TAU/7)+up*math.sin(k*TAU/7))*r)
        mesh.face([p(a,r1,i+1),p(b,r2,i+1),p(b,r2,i),p(a,r1,i)],tint(col,.85+i*.04))


def olive(x,z,s=1):
    branching_olive(x,z,s)



def cypress(x,z,h,w,hero=False):
    flame_cypress(x,z,h,w,hero)

distant_house_count=far_village()

print('Sculpting cypresses, olive groves and field brushwork...',flush=True)
cypress(-50,65,37.5,4.9,True)
cypress(-54,66,24,2.6,True)
for x,z,h,w in [(-20,46,18,2.5),(35,53,17,2.2),(-33,-2,16,2.0),(31,-8,15,1.8),(-13,-48,17,2.1),(55,-71,18,1.9),(-66,-45,20,2.2)]:cypress(x,z,h,w)
for i in range(65):
    x=R.uniform(-165,165);z=R.uniform(-180,130)
    if (-24<x<45 and 38<z<120) or (-12<x<26 and -28<z<10):continue
    if distance_to_roads(x,z)<6 or any(math.hypot(x-a,z-b)<r+3 for a,b,r in occupied):continue
    cypress(x,z,R.uniform(10,19),R.uniform(1.3,2.1))
for x,z,s in [(-7,51,1.5),(34,40,1.4),(-14,-16,1.35),(28,-1,1.15),(-25,-17,1.1),(-59,63,1.6),(-31,76,1.25),(49,20,1.4)]:olive(x,z,s)
for i in range(240):
    x=R.uniform(-170,170);z=R.uniform(-170,130)
    if -12<x<26 and -28<z<10:continue
    if distance_to_roads(x,z)<5 or math.hypot(x+43,z-65)<10 or any(math.hypot(x-a,z-b)<r+2.8 for a,b,r in occupied):continue
    olive(x,z,R.uniform(.7,1.3))

# Terraced fields give the slopes long, curved, directional color strokes.
for field in [(-100,43,45,38),(75,61,36,40),(-113,-122,38,30),(119,-96,38,40),(-13,129,70,25)]:
    x,z,w,d=field
    for row in range(16):
        pts=[(x-w/2+w*j/24,z-d/2+row*d/16+2.5*math.sin(j/24*math.pi+row*.13)) for j in range(25)]
        ribbon(pts,R.uniform(.5,1.2),'earth',color(R.choice(['#9eab8b','#c1af7f','#708d83','#d1c08e'])),.07,'fields')
# Sparse stones and low clumps around the lane, instead of repeated triangular grass.
for road in PATHS[:7]:
    for j in range(2,len(road)-2,2):
        x,z=road[j];p,q=road[j-1],road[j+1];dx,dz=q[0]-p[0],q[1]-p[1];l=max(.01,math.hypot(dx,dz))
        side=R.choice([-1,1]);offset=R.uniform(3.3,5.6)
        xx=x-dz/l*side*offset;zz=z+dx/l*side*offset;y=height(xx,zz)
        if R.random()<.5:ellipsoid('stone',(xx,y+.15,zz),(.25,.21,.20),color('#a7ac98'),j,3,5,'verges')
        for k in range(3):
            b=batch('brush',xx,zz,'verges');hh=R.uniform(.13,.4);ww=R.uniform(.035,.10)
            b.face([(xx-ww,y,zz),(xx+.13,y+hh,zz+.04),(xx+ww,y,zz)],color(R.choice(['#9caa7a','#bcba86','#69877b'])))

paint_road_edges()

# Add the second-pass scene dressing with the same coordinates and mesh exporter.
exec(compile((ROOT/'tools/village-details.py').read_text(encoding='utf-8'),
             str(ROOT/'tools/village-details.py'), 'exec'), globals())

# Offset ridges descend into an open valley behind the village.
for layer,radius,base_y,amplitude,palette in [(0,348,-8,55,['#365975','#487189','#5a8296']),(1,440,-14,94,['#4d7794','#6c95ac','#81a5b7']),(2,535,-20,119,['#7598b2','#96b3c4','#b0c5cf'])]:
    count=240
    for i in range(count):
        angles=[i/count*TAU,(i+1)/count*TAU]
        peaks=[]
        for a in angles:
            valley_angle=-math.pi/2+.16-layer*.19
            delta=math.atan2(math.sin(a-valley_angle),math.cos(a-valley_angle))
            valley=1-(.64-layer*.08)*math.exp(-(delta/(.30+layer*.075))**2)
            top=base_y+amplitude*(.64+.23*math.sin(a*(4+layer)+layer*1.3)+.16*math.sin(a*9+.8+layer)+.055*math.sin(a*23))*valley
            peaks.append(top)
        b=batch('mountain',math.cos(angles[0])*radius,math.sin(angles[0])*radius,'ridges')
        col=lerp(color(palette[0]),color(palette[1]),.5+.35*math.sin(angles[0]*5+layer))
        profile=[(-110,0),(-71,.24),(-35,.68),(0,1),(42,.48),(95,0)]
        for j in range(len(profile)-1):
            verts=[];uvs=[]
            for k,r in [(1,j),(1,j+1),(0,j+1),(0,j)]:
                offset,h=profile[r];a=angles[k]
                rad=radius+offset+(16*math.sin(a*3+layer*1.4)+7*math.sin(a*11+layer))*h
                yy=base_y+(peaks[k]-base_y)*h+math.sin(a*19+layer+r*.8)*2.2*h*(1-h)
                verts.append((math.cos(a)*rad+layer*17-12,yy,math.sin(a)*rad-layer*21))
                uvs.append((a*radius*.018,r*.24))
            b.face(verts,tint(col,.85+.13*profile[j+1][1]+.06*math.sin(angles[0]*31+layer+j*.7)),uvs)

print('Writing Blender meshes and portable geometry...',flush=True)
surface_finish=conform_ground_surfaces()
collections={}
geometry_records=[]
blobs=[]
offset=0


def pack_array(values, code, components):
    global offset
    while offset%4:blobs.append(b'\0');offset+=1
    raw=struct.pack('<'+str(len(values))+code,*values)
    record={'offset':offset,'length':len(values),'type':code,'components':components}
    blobs.append(raw);offset+=len(raw)
    return record


for key, m in meshes.items():
    if not m.faces:continue
    mesh=bpy.data.meshes.new(m.name)
    mesh.from_pydata([(x,-z,y) for x,y,z in m.verts],[],m.faces)
    mesh.materials.append(materials[m.mat])
    uv=mesh.uv_layers.new(name='Brush UV')
    pigment=mesh.color_attributes.new(name='Pigment',type='FLOAT_COLOR',domain='CORNER')
    # Adding a color layer reallocates CustomData. Reacquire the UV RNA handle
    # before writing it; using the earlier handle corrupts the color layer.
    uv=mesh.uv_layers['Brush UV']
    color_components=4 if material_specs[m.mat].get('transparent') else 3
    for loop in mesh.loops:
        uv.data[loop.index].uv=m.uv[loop.vertex_index]
        rgba=m.colors[loop.vertex_index]
        pigment.data[loop.index].color=rgba if len(rgba)==4 else (*rgba,1)
    mesh.update()
    assert all(0 <= channel <= 1 for sample in list(mesh.color_attributes['Pigment'].data)[::127] for channel in sample.color), m.name
    ob=bpy.data.objects.new(m.name,mesh)
    group=key[0]
    if group not in collections:
        collection=bpy.data.collections.new(group.replace('_',' ').title())
        bpy.context.scene.collection.children.link(collection);collections[group]=collection
    collections[group].objects.link(ob)
    mesh.calc_loop_triangles()
    # Export from the Blender mesh, using actual loop normals / UV / colors.
    positions=[];normals=[];uvs=[];cols=[];indices=[]
    for v in mesh.vertices:positions.extend((v.co.x,v.co.z,-v.co.y))
    smooth = m.mat in ('leaves','cypress','mountain','wallstone','drywall','moss','ground_moss','damp_earth') or key[0]=='terrain'
    if smooth:
        averaged = {}
        for poly in mesh.polygons:
            for vi in poly.vertices:
                v=mesh.vertices[vi]
                key_pos=tuple(round(c,4) for c in v.co)
                if key_pos not in averaged:averaged[key_pos]=Vector((0,0,0))
                averaged[key_pos]+=poly.normal
        custom=[]
        for v in mesh.vertices:
            n=averaged[tuple(round(c,4) for c in v.co)].normalized()
            normals.extend((n.x,n.z,-n.y));custom.append(n)
        mesh.normals_split_custom_set([custom[loop.vertex_index] for loop in mesh.loops])
    else:
        for v in mesh.vertices:normals.extend((v.normal.x,v.normal.z,-v.normal.y))
    # Setting custom normals also reallocates CustomData; refresh both handles.
    uv=mesh.uv_layers['Brush UV']
    pigment=mesh.color_attributes['Pigment']
    # Each builder face owns its vertices; loop data is unambiguous per vertex.
    uv_by_vertex=[None]*len(mesh.vertices);col_by_vertex=[None]*len(mesh.vertices)
    for loop in mesh.loops:
        uv_by_vertex[loop.vertex_index]=tuple(uv.data[loop.index].uv)
        col_by_vertex[loop.vertex_index]=tuple(pigment.data[loop.index].color[:color_components])
    for v in uv_by_vertex:uvs.extend(v)
    for c in col_by_vertex:cols.extend(round(max(0,min(1,v))*255) for v in c)
    assert all(math.isfinite(v) and 0<=v<=1 for c in col_by_vertex for v in c), m.name
    for tri in mesh.loop_triangles:indices.extend(tri.vertices)
    geometry_records.append(dict(name=m.name,material=m.mat,group=group,
        position=pack_array(positions,'f',3),normal=pack_array(normals,'f',3),
        uv=pack_array(uvs,'f',2),color=pack_array(cols,'B',color_components),index=pack_array(indices,'I',1)))

# Useful named cameras in the editable project and corresponding game bookmarks.
views=[
    dict(id='lane',name='石巷起飞',position=[11.2,height(11.2,82)+1.8,82],target=[17,height(17,55)+1.3,55]),
    dict(id='church',name='教堂前方',position=[-8,height(-8,7)+2.25,7],target=[22,13,-30]),
    dict(id='overlook',name='丝柏俯瞰',position=[-32,59,91],target=[5,24,-50]),
    dict(id='village',name='屋顶之间',position=[42,19,-10],target=[-12,8,-72]),
]
for view in views:
    camera=bpy.data.cameras.new(view['name'])
    # Match the game's vertical FOV at the review's 16:9 aspect ratio.
    camera.sensor_fit='VERTICAL';camera.sensor_height=24
    camera.lens=12/math.tan(math.radians(79)*.5)
    ob=bpy.data.objects.new(view['name'],camera);bpy.context.scene.collection.objects.link(ob)
    p=view['position'];t=view['target'];ob.location=(p[0],-p[2],p[1]);target=Vector((t[0],-t[2],t[1]))
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
    if view['id']=='overlook':bpy.context.scene.camera=ob
world=bpy.data.worlds.new('Blue night ambient');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(*color('#6989b5'),1)
world.node_tree.nodes['Background'].inputs[1].default_value=.32
if (OUT/'textures/night-sky.png').exists():
    env=world.node_tree.nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(OUT/'textures/night-sky.png'));env.image.pack()
    world.node_tree.links.new(env.outputs['Color'],world.node_tree.nodes['Background'].inputs[0])
bpy.context.scene.world=world
sun_data=bpy.data.lights.new('Moonlight','SUN');sun_data.energy=1.7;sun_data.angle=.15
sun=bpy.data.objects.new('Moonlight',sun_data);bpy.context.scene.collection.objects.link(sun);sun.rotation_euler=(.65,-.35,-.5)
sun_data.color=(.84,.90,1)
bpy.context.scene.render.engine='CYCLES'
bpy.context.scene.cycles.samples=24
bpy.context.scene.render.resolution_x=1280;bpy.context.scene.render.resolution_y=720
bpy.context.scene.view_settings.view_transform='AgX'
bpy.context.scene['Reference']='a7e33feb6fab21da6a49aba23d5d15f1.mp4; 20.1 seconds'
bpy.context.scene['Game export']='starry-village.js, generated from Blender loop geometry; X / Y-up / Z'
bpy.context.scene['Scope']='Composition pass v5: 79-degree views, warm church approach, side framing, broken moss and surface pigments'
metadata=dict(version=1,title='Starry Night / inhabited valley v5',revision='composition-and-warm-depth',wallFinish=wall_finish_stats,surfaceFinish=surface_finish,materials=material_specs,meshes=geometry_records,
    colliders=colliders,houses=house_records,distantHouses=distant_records,districts=district_records,houseTypes=HOUSE_TYPES,windowCounts=window_counts,streets=STREETS,views=views,lightPools=light_pools,
    terrain=dict(n=GRID_N,span=GRID_SPAN,heights=pack_array(grid,'f',1)),
    stats=dict(meshes=len(geometry_records),houses=len(house_records),distantHouses=distant_house_count,triangles=sum(m['index']['length']//3 for m in geometry_records),colliders=len(colliders),details=detail_stats))
binary=b''.join(blobs)
textures={name:base64.b64encode((OUT/'textures'/f'{name}.png').read_bytes()).decode() for name in {spec[key] for spec in material_specs.values() for key in ('texture','normal') if key in spec}}
payload=dict(metadata=metadata,binary=base64.b64encode(gzip.compress(binary,compresslevel=6)).decode(),textures=textures)
(OUT/'starry-village.js').write_text('/* Generated by Blender 4.5 LTS. Local-file compatible; no network requests. */\nwindow.STARRY_VILLAGE='+json.dumps(payload,separators=(',',':'))+';\n',encoding='utf-8')
(OUT/'scene-manifest.json').write_text(json.dumps({k:v for k,v in metadata.items() if k not in ('meshes','terrain')},ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'starry-village.blend'))
print('Exporting standard GLB...',flush=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'starry-village.glb'),export_format='GLB',export_cameras=True,export_lights=True,export_yup=True,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_attributes=False,export_vertex_color='NAME',export_vertex_color_name='Pigment',export_all_vertex_colors=False)
print(json.dumps(dict(status='complete',blender=bpy.app.version_string,mesh_count=len(geometry_records),house_count=len(house_records),raw_bytes=len(binary),compressed_bytes=len(gzip.compress(binary)),source=str(OUT/'starry-village.blend'))),flush=True)
