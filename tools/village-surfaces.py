"""Continuous terrain and paving pigments; loaded by build-village.py.

Reuse the terrain vertices and path batches. A small road index keeps the
shoulder colors continuous across chunks without introducing decal cards.
"""

_surface_cells={}
for road in PATHS:
    for a,b in zip(road,road[1:]):
        for ix in range(math.floor((min(a[0],b[0])-9)/12),math.floor((max(a[0],b[0])+9)/12)+1):
            for iz in range(math.floor((min(a[1],b[1])-9)/12),math.floor((max(a[1],b[1])+9)/12)+1):
                _surface_cells.setdefault((ix,iz),[]).append((a,b))


def surface_road_distance(x,z):
    best=25.0
    for a,b in _surface_cells.get((math.floor(x/12),math.floor(z/12)),[]):
        dx,dz=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/max(.00001,dx*dx+dz*dz)))
        best=min(best,math.hypot(x-a[0]-dx*t,z-a[1]-dz*t))
    return best


_soil=color('#a5997c')
_grass=color('#72846a')
_wet=color('#7b806d')
_gravel=color('#b0b09c')


def surface_pigment(x,z):
    field=max(0,min(1,.49+.28*math.sin(x*.068+z*.037)+.22*math.cos(z*.115-x*.046)))
    pigment=lerp(_grass,_soil,field)
    wet=max(0,.40+.34*math.sin(z*.21+x*.12)+.26*math.cos(x*.18-z*.10))
    pigment=lerp(pigment,_wet,wet*.25)
    distance=surface_road_distance(x,z)
    shoulder=math.exp(-((distance-3.1)/1.8)**2)*.45
    return lerp(pigment,_gravel,shoulder)


def lane_pigment(x,z,side,col):
    grain=.5+.24*math.sin(x*.87+z*.61)+.18*math.cos(z*.39-x*.71)
    pigment=lerp(col,_gravel,.13+grain*.23)
    edge=max(0,(abs(side)-.72)/.28)
    return lerp(pigment,surface_pigment(x,z),edge*.40)


def plaza_pigment(x,z):
    # Worn pale paving joins the doorway to the main approach. Quiet patches
    # of damp soil and grass occupy the sides, with no near-black polygons.
    t=max(0,min(1,((x-7)*-8+(z+19)*12)/208))
    path_distance=math.hypot(x-(7-8*t),z-(-19+12*t))
    paving=math.exp(-(path_distance/3.3)**2)
    pigment=lerp(color('#a39d84'),color('#bbb6a3'),paving*.85)
    damp=math.exp(-((x+3)/5.5)**2-((z+14)/4.5)**2)
    pigment=lerp(pigment,color('#848875'),damp*.42)
    edge=max(0,min(1,(math.hypot((x-3)/15,(z+15)/11)-.70)/.30))
    pigment=lerp(pigment,surface_pigment(x,z),edge*.6)
    return tint(pigment,.97+.04*math.sin(x*.8+z*.55))


def conform_ground_surfaces():
    """Clip thin ground paint to the heightfield's exact cell diagonals.

    Sampling only a road quad's four corners lets its interior cross the
    hillside. Interpolate UVs, pigments and the intended lift at each cut;
    existing batches/materials and collision terrain remain unchanged.
    """
    stats=dict(sourceFaces=0,fittedFaces=0)

    def clip(poly,distance):
        result=[]
        for p,q in zip(poly,poly[1:]+poly[:1]):
            a,b=distance(p),distance(q)
            if a>=-1e-9:result.append(p)
            if (a>0)!=(b>0) and abs(a-b)>1e-12:
                t=a/(a-b);result.append(tuple(u+(v-u)*t for u,v in zip(p,q)))
        clean=[]
        for p in result:
            if not clean or math.hypot(p[0]-clean[-1][0],p[1]-clean[-1][1])>1e-7:clean.append(p)
        if len(clean)>1 and math.hypot(clean[0][0]-clean[-1][0],clean[0][1]-clean[-1][1])<1e-7:clean.pop()
        return clean

    for key,source in list(meshes.items()):
        if key[0] not in ('lanes','lane_brushes','fields','distant_roads','gardens','verges') or source.mat not in ('path','earth'):continue
        fitted=Mesh(source.name,source.mat)
        for face in source.faces:
            stats['sourceFaces']+=1
            poly=[]
            for i in face:
                x,y,z=source.verts[i]
                poly.append((x,z,y-height(x,z),*source.uv[i],*source.colors[i]))
            xlo,xhi=min(p[0] for p in poly),max(p[0] for p in poly)
            zlo,zhi=min(p[1] for p in poly),max(p[1] for p in poly)
            for ix in range(math.floor((xlo+GRID_SPAN/2)/GRID_STEP),math.floor((xhi+GRID_SPAN/2)/GRID_STEP)+1):
                x0=-GRID_SPAN/2+ix*GRID_STEP
                for iz in range(math.floor((zlo+GRID_SPAN/2)/GRID_STEP),math.floor((zhi+GRID_SPAN/2)/GRID_STEP)+1):
                    z0=-GRID_SPAN/2+iz*GRID_STEP
                    cell=poly
                    for distance in [lambda p:p[0]-x0,lambda p:x0+GRID_STEP-p[0],lambda p:p[1]-z0,lambda p:z0+GRID_STEP-p[1]]:
                        cell=clip(cell,distance)
                        if len(cell)<3:break
                    if len(cell)<3:continue
                    for side in [-1,1]:
                        part=clip(cell,lambda p:side*((p[1]-z0)-(p[0]-x0)))
                        if len(part)<3:continue
                        area=abs(sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(part,part[1:]+part[:1])))
                        if area<1e-8:continue
                        fitted.face([(p[0],height(p[0],p[1])+p[2],p[1]) for p in part],part[0][5:],[(p[3],p[4]) for p in part])
                        fitted.colors[-len(part):]=[p[5:] for p in part]
                        stats['fittedFaces']+=1
        meshes[key]=fitted
    print('Ground surface fitting:',json.dumps(stats),flush=True)
    return stats
