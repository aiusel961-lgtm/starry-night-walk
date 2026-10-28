"""Second-pass village dressing. Executed inside build-village.py's namespace."""
print('Dressing courtyards, market square and hillside gardens...', flush=True)
D = random.Random(1890)
detail_stats = dict(lanterns=0, marketStalls=0, planters=0, gardenBeds=0,
                    meadowTufts=0, vineyardRows=0, benches=0, fountains=0)
stone_col, wood_col = color('#a7af9a'), color('#716d53')


def lathe(mat, x, y, z, profile, col, sides=12, group='courtyards'):
    mesh = batch(mat, x, z, group)
    for (ra, ya), (rb, yb) in zip(profile, profile[1:]):
        for i in range(sides):
            a, b = i*TAU/sides, (i+1)*TAU/sides
            mesh.face([(x+ra*math.cos(a), y+ya, z+ra*math.sin(a)),
                       (x+rb*math.cos(a), y+yb, z+rb*math.sin(a)),
                       (x+rb*math.cos(b), y+yb, z+rb*math.sin(b)),
                       (x+ra*math.cos(b), y+ya, z+ra*math.sin(b))], tint(col, .9+.12*math.sin(a+.8)))


def clear_ground(x, z, road=4.9, buildings=.7):
    return distance_to_roads(x, z) > road and all(math.hypot(x-a, z-b)>r+buildings for a, b, r in occupied)


def flowering_clump(x, y, z, scale=1, palette=None, group='flowers'):
    palette = palette or ['#b1a5bd', '#7b82b3', '#d5b8bf', '#c4ba86']
    for k in range(5):
        angle=k*2.399+D.uniform(-.3,.3)
        xx=x+math.cos(angle)*.27*scale; zz=z+math.sin(angle)*.27*scale
        hh=D.uniform(.3,.65)*scale
        mesh=batch('brush',xx,zz,group)
        bend=math.cos(angle)*.14*scale
        mesh.face([(xx-.02*scale,y,zz),(xx+bend-.015*scale,y+hh,zz),
                   (xx+bend+.015*scale,y+hh,zz),(xx+.02*scale,y,zz)], color('#77946b'))
        # Two irregular petals cross in space; no flat billboards facing the player.
        for side in (0, math.pi/2):
            w=.085*scale; dx=math.cos(side)*w; dz=math.sin(side)*w
            mesh.face([(xx+bend-dx,y+hh-.035*scale,zz-dz),
                       (xx+bend-dx*.65,y+hh+.13*scale,zz-dz*.65),
                       (xx+bend+dx*.65,y+hh+.13*scale,zz+dz*.65),
                       (xx+bend+dx,y+hh-.035*scale,zz+dz)], color(D.choice(palette)))


def pot(x, z, scale=1, y=None):
    y=height(x,z) if y is None else y
    col=color(D.choice(['#ad8263','#b39671','#a59c7c','#7d9291']))
    lathe('plaster',x,y,z,[(.18*scale,0),(.30*scale,.12*scale),(.38*scale,.51*scale),
          (.34*scale,.62*scale),(.39*scale,.65*scale),(.39*scale,.72*scale),(.29*scale,.72*scale),
          (.27*scale,.59*scale)],col,10)
    ellipsoid('leaves',(x,y+.76*scale,z),(.34*scale,.24*scale,.34*scale),color('#809477'),2,3,7,'gardens')
    flowering_clump(x,y+.73*scale,z,scale)
    detail_stats['planters']+=1


def lantern(x, z, y=None, tall=True, yaw=0):
    y=height(x,z) if y is None else y
    stem=2.9 if tall else 0
    if tall:
        lathe('stone',x,y,z,[(.32,0),(.32,.2),(.19,.4),(.12,.48)],stone_col,8,'lamps')
        box('dark',(x,y+1.6,z),(.10,2.7,.10),color('#435252'),group='lamps')
    cy=y+stem+.3
    box('window',(x,cy,z),(.27,.45,.27),color('#efc178'),yaw,'lamps')
    for sx in [-1,1]:
        for sz in [-1,1]:
            p=transform((sx*.18,0,sz*.18),(x,cy,z),yaw)
            box('dark',p,(.055,.57,.055),color('#465357'),yaw,'lamps')
    box('dark',(x,cy-.3,z),(.48,.10,.48),color('#47565b'),yaw,'lamps',.025)
    lathe('roof',x,cy+.29,z,[(.36,0),(.12,.20),(.025,.25)],color('#677e86'),4,'lamps')
    light_pools.append(dict(x=x,z=z,radius=4.7 if tall else 2.7,strength=.90 if tall else .65))
    if tall:collider(x,z,.35,.35,y,cy+.55,0,'lamp')
    detail_stats['lanterns']+=1


def bench(x,z,yaw=0):
    y=height(x,z)
    def part(local,dims,mat='wood'):
        box(mat,transform(local,(x,y,z),yaw),dims,wood_col if mat=='wood' else stone_col,yaw,'courtyards')
    for sx in [-.95,.95]:part((sx,.35,0),(.25,.7,.66),'stone')
    for i in range(4):part((0,.72,-.29+i*.19),(2.7,.12,.15))
    for sx in [-1,1]:part((sx,1.02,-.36),(.11,.74,.11))
    for yy in [.97,1.23]:part((0,yy,-.36),(2.7,.17,.09))
    collider(x,z,2.7,.9,y,y+1.35,yaw,'bench');detail_stats['benches']+=1


def barrel(x,z,scale=1,y=None):
    y=height(x,z) if y is None else y
    lathe('wood',x,y,z,[(.33*scale,0),(.43*scale,.22*scale),(.46*scale,.55*scale),
          (.40*scale,.95*scale),(.32*scale,1.05*scale),(0,1.05*scale)],color('#9a8969'),12,'market')
    for hh,rr in [(.16,.415),(.82,.427)]:
        lathe('dark',x,y,z,[(rr*scale,hh*scale),(rr*scale,(hh+.065)*scale)],color('#4d6166'),12,'market')


def crate(x,y,z,w=.9,yaw=0):
    for side in [-1,1]:
        for h in [.12,.32,.52]:
            box('wood',transform((0,h,side*.35),(x,y,z),yaw),(w,.15,.08),color('#aa946c'),yaw,'market')
            box('wood',transform((side*(w/2-.05),h,0),(x,y,z),yaw),(.08,.15,.72),color('#8c8263'),yaw,'market')
    for i in range(5):
        xx=x+D.uniform(-w*.3,w*.3);zz=z+D.uniform(-.21,.21)
        ellipsoid('plaster',(xx,y+.50,zz),(.14,.14,.13),color(D.choice(['#bba95d','#9a9164','#aa7d64'])),i,3,6,'market')


def stall(x,z,yaw,colors):
    y=height(x,z);base=(x,y,z)
    for sx in [-1,1]:
        for sz in [-1,1]:
            box('wood',transform((sx*1.8,1.6,sz*1.05),base,yaw),(.12,3.2,.12),wood_col,yaw,'market')
    box('wood',transform((0,1.05,.4),base,yaw),(3.9,.18,1.15),color('#9e906a'),yaw,'market')
    box('wood',transform((0,.59,.9),base,yaw),(3.8,.85,.1),color('#817658'),yaw,'market')
    mesh=batch('cloth',x,z,'market')
    for i in range(10):
        xa=-2+i*.4;xb=xa+.405
        # Sagging cloth forms a roof with a distinct hem.
        for za,zb in [(-1.3,-.55),(-.55,.2),(.2,.85),(.85,1.35)]:
            def v(xx,zz):return transform((xx,3.3-.21*(zz+.2)**2+.035*math.sin(xx*4),zz),base,yaw)
            mesh.face([v(xa,za),v(xa,zb),v(xb,zb),v(xb,za)],color(colors[i%2]))
        mesh.face([v(xa,1.35),transform((xa,2.58,1.35),base,yaw),
                   transform((xb,2.58+.06*math.sin(i),1.35),base,yaw),v(xb,1.35)],color(colors[i%2]))
    for i in range(3):
        p=transform((-1.25+i*1.2,1.15,.4),base,yaw);crate(*p,.9,yaw)
    p=transform((2.7,0,-.3),base,yaw);barrel(p[0],p[2],.9)
    p=transform((-2.5,0,.4),base,yaw);crate(p[0],height(p[0],p[2]),p[2],1,yaw)
    p=transform((-1.7,2.1,1.05),base,yaw);lantern(p[0],p[2],p[1],False,yaw)
    collider(x,z,4.1,2.65,y,y+3.45,yaw,'market')
    detail_stats['marketStalls']+=1


# Place landmarks beside the flight corridor; the church approach stays open.
fx,fz=-9,-19;fy=height(fx,fz)
lathe('stone',fx,fy,fz,[(2.5,.08),(2.5,.25),(2.18,.38),(2.18,.95),
      (2.33,1.04),(2.33,1.18),(1.93,1.18),(1.86,.48)],stone_col,28,'fountain')
lathe('stone',fx,fy,fz,[(.58,.42),(.52,1.0),(.23,1.25),(.23,2.0),(.75,2.15),
      (.79,2.30),(.60,2.35),(.22,2.18),(.13,2.75),(0,2.85)],tint(stone_col,1.1),16,'fountain')
water=batch('water',fx,fz,'fountain')
for i in range(40):
    a=i/40*TAU;b=(i+1)/40*TAU
    water.face([(fx,fy+.83,fz),(fx+1.94*math.cos(b),fy+.83,fz+1.94*math.sin(b)),
                (fx+1.94*math.cos(a),fy+.83,fz+1.94*math.sin(a))],color('#789ca5'))
    if i%10==0:
        xx=fx+math.cos(a)*.66;zz=fz+math.sin(a)*.66
        water.face([(xx-.025,fy+2.2,zz),(xx+.13,fy+.84,zz+.08),
                    (xx+.20,fy+.84,zz+.08),(xx+.025,fy+2.2,zz)],color('#b7cdbe'))
collider(fx,fz,4.65,4.65,fy,fy+1.2,0,'fountain');collider(fx,fz,1.3,1.3,fy+1.2,fy+2.85,0,'fountain')
detail_stats['fountains']=1
bench(-11,-12,-.6);bench(22,-14,1.55);bench(-24,54,-.3)
stall(-19,-2,.35,['#a9b4a4','#647d79'])
stall(22,-6,-.85,['#c6b392','#8d7d6b'])
stall(-18,-27,1.2,['#acb0b3','#6c8093'])
for x,z,s in [(-14,-13,1.4),(-5,-24,1.3),(15,-18,1.5),(24,-10,1.4),(-22,1,1.6),(-26,55,1.4)]:pot(x,z,s)
for x,z in [(-15,-11),(18,-13),(-16,-25),(26,1),(17,6)]:lantern(x,z)
# Broad, overlapping baked bounce guides the eye toward the entrance. These
# are painted light pools, not extra real-time lights or shadow passes.
light_pools.extend([
    dict(x=7,z=-19.1,radius=5.8,strength=1.40),
    dict(x=5.8,z=-15.5,radius=4.1,strength=.64),
    dict(x=2.8,z=-11.8,radius=3.7,strength=.42),
    dict(x=-.8,z=-8.3,radius=3.2,strength=.27),
])

# Lanterns along alternating sides of the stone approach.
for j in range(5,118,13):
    p=PATHS[0][j];a=PATHS[0][j-1];b=PATHS[0][j+1]
    dx,dz=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dz);side=1 if j%2 else -1
    x=p[0]-dz/l*side*4.55;z=p[1]+dx/l*side*4.55
    if -5<z<17 and -3<x<9:continue
    lantern(x,z)

# Door lanterns, window boxes and climbers give individual street fronts detail.
for i,house in enumerate(house_records):
    x,z,w,d,y,yaw=(house[k] for k in ['x','z','width','depth','ground','yaw'])
    base=(x,y,z)
    if i%2==0:
        p=transform((w*.32,1.85,d/2+.25),base,yaw);lantern(p[0],p[2],p[1],False,yaw)
    for side in [-1,1] if i<34 else [1]:
        p=transform((-w*.30,0,side*(d/2+.85)),base,yaw)
        if distance_to_roads(p[0],p[2])>2.5:pot(p[0],p[2],.85+D.random()*.45)
        if i%3!=2:
            p=transform((-w*.31,1.12,side*(d/2+.37)),base,yaw)
            box('wood',p,(1.20,.3,.42),color('#7c7b59'),yaw,'courtyards')
            for k in range(3):
                q=transform((-.4+k*.4,.17,0),p,yaw);flowering_clump(*q,.60,group='flowers')
    if i%3==0:
        for k in range(9):
            p=transform((w*.40+.11*math.sin(k),.45+k*.48,d/2+.15),base,yaw)
            ellipsoid('leaves',p,(.37,.36,.25),color('#64816e'),k,3,6,'gardens')


def fence(points):
    for x,z in points:
        y=height(x,z);box('wood',(x,y+.73,z),(.14,1.48,.14),color('#7a7e62'),group='gardens')
    for p,q in zip(points,points[1:]):
        for hh in [.52,1.03]:branch((p[0],height(*p)+hh,p[1]),(q[0],height(*q)+hh,q[1]),.065,.065,color('#949075'),'gardens')


# Walled flower terraces create foreground depth beside the cypress lookout.
for cx,cz,w,d in [(-10,63,21,15),(-16,-18,8,6),(27,5,11,8),(-30,86,18,10),(46,3,13,10)]:
    detail_stats['gardenBeds']+=1
    for row in range(4):
        zz=cz-d/2+row*d/4
        pts=[(cx-w/2+j*w/28,zz+1.5*math.sin(j/28*math.pi)) for j in range(29)]
        clean=[p for p in pts if clear_ground(*p)]
        for p,q in zip(clean,clean[1:]):
            if math.dist(p,q)>w/14:continue
            ribbon([p,q],.75,'earth',color('#777f68'),.075,'gardens')
        for j,(xx,zz) in enumerate(pts):
            if not clear_ground(xx,zz):continue
            for offset in [-.25,.2]:
                flowering_clump(xx,height(xx,zz+offset)+.08,zz+offset,1.25,
                    ['#8b89b1','#a5a7d0','#c7b5bf'] if row%2 else ['#c5b47a','#d0bd85','#a6aa72'])
    points=[(cx-w/2+j*w/9,cz+d*.6+1.3*math.sin(j/9*math.pi)) for j in range(10)]
    if all(clear_ground(*p,4.9,1.5) for p in points):
        fence(points)
        for p,q in zip(points,points[1:]):
            dx,dz=q[0]-p[0],q[1]-p[1];xx=(p[0]+q[0])/2;zz=(p[1]+q[1])/2
            yy=height(xx,zz)
            box('stone',(xx,yy+.35,zz),(math.hypot(dx,dz),.7,.6),stone_col,math.atan2(-dz,dx),'gardens',.07)
            collider(xx,zz,math.hypot(dx,dz),.6,yy,yy+.7,math.atan2(-dz,dx),'garden_wall')

# Vineyard on the right hill, with lower bushes following the contour.
for row in range(7):
    zz=51+row*3.9
    points=[]
    for j in range(15):
        xx=53+j*2.5;z=zz+2*math.sin(j/14*math.pi)
        if not clear_ground(xx,z,5,1):continue
        yy=height(xx,z);points.append((xx,z))
        ellipsoid('leaves',(xx,yy+.65,z),(1.04,.69,.63),color(D.choice(['#73856a','#8c9772','#a3a277'])),row+j,4,7,'vineyard')
        if j%3==0:box('wood',(xx,yy+.85,z),(.12,1.7,.12),wood_col,group='vineyard')
    for p,q in zip(points,points[1:]):
        if math.dist(p,q)<3.8:branch((p[0],height(*p)+.9,p[1]),(q[0],height(*q)+.9,q[1]),.035,.035,wood_col,'vineyard')
    detail_stats['vineyardRows']+=1

# Patches cluster around landforms and the roadside instead of uniform scatter.
patches=[(-12,69,30,21),(-27,31,20,14),(38,44,19,24),(2,27,17,11),
         (-50,83,27,18),(-24,108,35,16),(54,7,26,25),(-51,5,27,24),
         (88,92,26,18),(-96,-13,32,20),(16,-147,50,15)]
grass_colors=[color(c) for c in ['#8d9e6a','#bac184','#7e986e','#c3b77e','#6c8972']]
for pc,(cx,cz,rx,rz) in enumerate(patches):
    for i in range(1400 if pc<6 else 650):
        a=D.random()*TAU;r=math.sqrt(D.random());x=cx+math.cos(a)*rx*r;z=cz+math.sin(a)*rz*r
        # Per-patch density varies in broad organic islands with open soil between.
        density=.58+.22*math.sin(x*.22+z*.13)+.18*math.sin(z*.34)
        if D.random()>density or not clear_ground(x,z,4.6,.65):continue
        y=height(x,z);s=D.uniform(.6,1.35);col=D.choice(grass_colors);mesh=batch('brush',x,z,'meadow')
        for k in range(4):
            a=D.random()*TAU;dx=math.cos(a);dz=math.sin(a);ww=.055*s;hh=D.uniform(.28,.8)*s
            mesh.face([(x-dz*ww,y,z+dx*ww),(x+dx*.20*s-dz*ww*.45,y+hh*.60,z+dz*.20*s+dx*ww*.45),
                       (x+dx*.36*s,y+hh,z+dz*.36*s),(x+dz*ww,y,z-dx*ww)],tint(col,.85+D.random()*.3))
        if i%7==0:flowering_clump(x,y,z,.75,D.choice([['#d1bc78','#b3a36f'],['#a8a5c5','#838bad']]))
        detail_stats['meadowTufts']+=1
    for i in range(34):
        a=D.random()*TAU;r=D.random();x=cx+math.cos(a)*rx*r;z=cz+math.sin(a)*rz*r
        if not clear_ground(x,z,5.7,1):continue
        y=height(x,z);s=D.uniform(.65,1.6)
        ellipsoid('leaves',(x,y+.4*s,z),(1.1*s,.62*s,.8*s),color(D.choice(['#73826a','#8c976f','#a09d75'])),i,4,8,'gardens')
        if i%5==0:ellipsoid('stone',(x+1.2,y+.22,z),(.65,.45,.48),color('#a5ac99'),i,4,7,'gardens')

print('Village detail counts:',json.dumps(detail_stats),flush=True)
