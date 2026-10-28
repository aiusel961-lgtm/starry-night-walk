"""Damp stone, broken moss colonies and terrain-following wall feet.

Executed by village-organic.py. Decoration uses independent seeds and adds no
colliders, preserving the stone layout, flight clearance and village placement.
"""

wall_finish_stats=dict(mossFaces=0,groundPatches=0)

# The lane is raised above the terrain. A small spatial index lets the moss
# follow its shoulder, including the narrow soil bank next to the wall.
_wall_road_cells={}
for road_index,road in enumerate(PATHS):
    half=(5.15 if road_index==0 else 4.2 if road_index<6 else 3.9)*.5
    for a,b in zip(road,road[1:]):
        for ix in range(math.floor((min(a[0],b[0])-half-.4)/8),math.floor((max(a[0],b[0])+half+.4)/8)+1):
            for iz in range(math.floor((min(a[1],b[1])-half-.4)/8),math.floor((max(a[1],b[1])+half+.4)/8)+1):
                _wall_road_cells.setdefault((ix,iz),[]).append((a,b,half))


def wall_ground_height(x,z):
    lift=0
    for a,b,half in _wall_road_cells.get((math.floor(x/8),math.floor(z/8)),[]):
        dx,dz=b[0]-a[0],b[1]-a[1];length2=dx*dx+dz*dz
        if length2<.000001:continue
        t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/length2))
        distance=math.hypot(x-a[0]-dx*t,z-a[1]-dz*t)
        shoulder=max(0,min(1,(half+.4-distance)/.4))
        lift=max(lift,.16*shoulder*shoulder*(3-2*shoulder))
    return height(x,z)+lift


def wall_moisture(x,z):
    return max(0,min(1,.45+.31*math.sin(x*.63+z*.47)+.25*math.sin(z*1.13-x*.71)))


def moss_field(p):
    x,y,z=p;wet=wall_moisture(x,z);above=y-wall_ground_height(x,z)
    edge=.07*math.sin(x*5.3+z*7.1)+.045*math.sin(x*14.1-z*11.7+y*7)
    colonies=.56+.28*math.sin(x*4.7+z*5.9+y*6.3)+.20*math.sin(z*11.3-x*7.9+y*13.2)
    islands=.48+.31*math.sin(x*1.1+z*.92)+.24*math.sin(z*2.7-x*1.5)
    return min((wet-.41)*.7,(islands-.35)*.35,.05+.38*wet*wet-above+edge,(colonies-.54-above*.35)*.5)


def stone_foot_color(p,col):
    x,y,z=p;wet=wall_moisture(x,z)
    foot=max(0,1-max(0,y-wall_ground_height(x,z))/.78)
    large=.98+.035*math.sin(x*1.8+z*1.37+y*2.8)
    return lerp(tint(col,large),color('#747767'),foot*(.13+wet*.14))


def weather_stone_pigment(mesh,vertices,col):
    mesh.colors[-len(vertices):]=[stone_foot_color(p,col) for p in vertices]


def moss_on_stone(vertices,stone_color):
    # Clip the growth field to the actual sculpted face; feather its opacity
    # into the stone, retaining bare islands between individual colonies.
    a,b,c,d=[Vector(p) for p in vertices]
    normal=(b-a).cross(c-a)
    if normal.length<.000001:return
    normal.normalize()
    if normal.y<-.45 or min(p[1]-wall_ground_height(p[0],p[2]) for p in vertices)>.80:return
    width=(d-a).length;rise=(b-a).length
    if width<.08 or rise<.05:return
    nu=max(1,math.ceil(width/.12));nv=max(1,math.ceil(rise/.11))
    def sample(u,v):
        p=(a+(d-a)*u)*(1-v)+(b+(c-b)*u)*v
        return p,moss_field(p)
    samples=[[sample(i/nu,j/nv) for i in range(nu+1)] for j in range(nv+1)]
    for j in range(nv):
        for i in range(nu):
            corners=[samples[j][i],samples[j+1][i],samples[j+1][i+1],samples[j][i+1]]
            for tri in [(0,1,2),(0,2,3)]:
                polygon=[corners[k] for k in tri];clipped=[]
                for k,(p,f) in enumerate(polygon):
                    q,g=polygon[(k+1)%3]
                    if f>=0:clipped.append((p,f))
                    if (f>=0)!=(g>=0):clipped.append((p+(q-p)*(f/(f-g)),0))
                if len(clipped)<3:continue
                if (clipped[1][0]-clipped[0][0]).cross(clipped[2][0]-clipped[0][0]).length<.000015:continue
                center=sum((p for p,_ in clipped),Vector())/len(clipped)
                mesh=batch('moss',center.x,center.z,'wall_growth')
                mesh.face([tuple(p+normal*.006) for p,_ in clipped],stone_color)
                colors=[]
                for p,f in clipped:
                    wet=wall_moisture(p.x,p.z)
                    variation=.5+.5*math.sin(p.x*6.3+p.z*4.1+p.y*5.7)
                    pigment=lerp(color('#929779'),color('#b1a484'),variation*.75+wet*.16)
                    t=min(1,max(0,f/.06));t=t*t*(3-2*t)
                    colors.append((*pigment,t*(.48+.30*variation)))
                mesh.colors[-len(colors):]=colors
                wall_finish_stats['mossFaces']+=len(clipped)-2


def terrain_pigment(x,z):
    # Match the existing soil at the edge instead of stamping dark oval cards.
    if 'surface_pigment' in globals():return surface_pigment(x,z)
    if 'earth_palette' not in globals():return color('#9b9b84')
    patch=.5+.33*math.sin(x*.045+z*.029)+.28*math.cos(z*.061-x*.021)
    return tint(lerp(earth_palette[0],earth_palette[2],max(0,min(1,patch))),.985)


def ground_moss_patch(x,z,yaw,face,rr):
    wet=wall_moisture(x,z)
    if wet<.43 or rr.random()>.68:return
    length=rr.uniform(.22,.78);width=rr.uniform(.16,.36)
    center=transform((rr.uniform(-.2,.2),0,face*(.50+width*.28)),(x,0,z),yaw)
    phase=rr.random()*TAU;n=18
    shape=[1+rr.uniform(-.28,.20) for _ in range(n)]
    for mat,expand,lift in [('damp_earth',1.42,.017),('ground_moss',1,.045)]:
        rings=[];cols=[]
        for t in [0,.45,1]:
            ring=[];pigments=[]
            for k in range(n):
                angle=k*TAU/n
                p=transform((math.cos(angle)*length*.5*shape[k]*expand*t,0,
                             math.sin(angle)*width*.5*shape[k]*expand*t),center,yaw)
                ring.append((p[0],wall_ground_height(p[0],p[2])+.006+lift*(1-t*t),p[2]))
                earth=terrain_pigment(p[0],p[2])
                if mat=='damp_earth':pigment=(*tint(earth,.78+.22*t),.55*(1-t))
                else:
                    moss=lerp(color('#8b9162'),color('#a69b6c'),.45+.35*math.sin(k*2.1+phase))
                    pigment=(*moss,.72 if t==0 else .52 if t<1 else 0)
                pigments.append(pigment)
            rings.append(ring);cols.append(pigments)
        mesh=batch(mat,x,z,'wall_growth')
        for j in range(2):
            for k in range(n):
                q=(k+1)%n
                points=[rings[j][k],rings[j+1][q],rings[j+1][k]] if j==0 else [rings[j][k],rings[j][q],rings[j+1][q],rings[j+1][k]]
                pigments=[cols[j][k],cols[j+1][q],cols[j+1][k]] if j==0 else [cols[j][k],cols[j][q],cols[j+1][q],cols[j+1][k]]
                mesh.face(points,pigments[0]);mesh.colors[-len(pigments):]=pigments
    # Low rounded clumps bridge the wall and soil at a few irregular points.
    for k in range(rr.randint(1,3)):
        p=transform((rr.uniform(-length*.30,length*.30),0,face*rr.uniform(-.06,width*.25)),center,yaw)
        r=rr.uniform(.035,.085);rings=[]
        for t,scale in [(0,1),(.6,.78),(1,.18)]:
            rings.append([(p[0]+math.cos(side*TAU/8)*r*scale,
                           wall_ground_height(p[0],p[2])+.016+r*.48*t,
                           p[2]+math.sin(side*TAU/8)*r*scale) for side in range(8)])
        mesh=batch('ground_moss',x,z,'wall_growth')
        for j in range(2):
            for side in range(8):
                q=(side+1)%8
                mesh.face([rings[j][side],rings[j+1][side],rings[j+1][q],rings[j][q]],color('#99966b'))
        mesh.face(list(reversed(rings[-1])),color('#9d9b70'))
    wall_finish_stats['groundPatches']+=1
