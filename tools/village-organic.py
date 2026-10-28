"""Sculpted stone, roofs and trees for the reference-driven art pass.

Loaded by build-village.py; all geometry uses the same Y-up authoring space.
"""

FAR_DISTRICTS=[
    ('west-orchard','西坡果园',[(-91,-100),(-113,-134),(-143,-164),(-152,-198)],20),
    ('west-terrace','西侧台地',[(-71,-151),(-90,-179),(-77,-211),(-49,-232)],20),
    ('valley-lane','谷地街巷',[(-4,-143),(3,-166),(-12,-196),(3,-225)],18),
    ('east-hamlet','东坡村落',[(70,-128),(84,-158),(113,-183),(129,-214)],22),
    ('upper-fields','山脚田园',[(-39,-264),(-7,-248),(30,-243),(68,-259)],22),
]

def art_random(x, z, salt=0):
    return random.Random(round(x*1009)+round(z*2003)+salt+91889)


exec(compile((ROOT/'tools/wall-weathering.py').read_text(encoding='utf-8'),
             str(ROOT/'tools/wall-weathering.py'),'exec'),globals())


def sculpted_stone(center, dims, col, yaw=0, group='walls', seed=0, slope=0):
    rr=art_random(center[0],center[2],seed)
    w,h,d=[v*.5 for v in dims]
    # Eight profiles vary the corner radius and asymmetric wear. More rings
    # round the edge while retaining broad, almost planar stone faces.
    profile=seed%8;radius=.12+.018*profile
    corners=[]
    for sx,sz,start in [(1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)]:
        for k in range(3):
            a=math.radians(start+k*45)
            corners.append((sx*(1-radius)+radius*math.cos(a),sz*(1-radius)+radius*math.sin(a)))
    rings=[]
    wear=[rr.uniform(.97,1.025) for _ in corners]
    for j,(yy,shrink) in enumerate([(-h,.92),(-h*.86,.99),(-h*.62,1),(h*.61,1),(h*.84,.99),(h,.93)]):
        ring=[]
        for i,(a,b) in enumerate(corners):
            xx=a*w*shrink*wear[i]
            p=(xx,yy+rr.uniform(-.016,.016)*dims[1]+xx*slope,b*d*shrink*wear[i])
            ring.append(transform(p,center,yaw))
        rings.append(ring)
    mesh=batch('drywall' if group=='walls' else 'stone',center[0],center[2],group)
    for j in range(len(rings)-1):
        for i in range(len(corners)):
            n=(i+1)%len(corners)
            vertices=[rings[j][i],rings[j+1][i],rings[j+1][n],rings[j][n]]
            pigment=tint(col,.94+rr.random()*.08)
            mesh.face(vertices,pigment)
            if group=='walls':
                weather_stone_pigment(mesh,vertices,pigment)
                moss_on_stone(vertices,pigment)
    mesh.face(list(reversed(rings[-1])),tint(col,1.04))
    mesh.face(rings[0],tint(col,.7))


def build_drywall(points, side, tall=False):
    lengths=[0]
    for p,q in zip(points,points[1:]):lengths.append(lengths[-1]+math.dist(p,q))
    rr=art_random(points[0][0],points[0][1],int(side*13)+(5 if tall else 0))
    def along(s):
        s=max(0,min(lengths[-1]-.0001,s));i=0
        while i<len(lengths)-2 and lengths[i+1]<s:i+=1
        p,q=points[i],points[i+1];l=max(.0001,lengths[i+1]-lengths[i]);t=(s-lengths[i])/l
        dx,dz=(q[0]-p[0])/l,(q[1]-p[1])/l
        offset=3.15 if tall else 2.9
        return p[0]+(q[0]-p[0])*t-dz*offset*side,p[1]+(q[1]-p[1])*t+dx*offset*side,math.atan2(-dz,dx)
    def top(s):
        # Open the main sightline without making every wall low. The smooth
        # dip also drives the mortar, coping and collision height together.
        z=along(s)[1]
        dip=.65*math.exp(-((z-79)/22)**4) if tall else 0
        return (3.05-dip if tall else 1.25)+.13*math.sin(s*.42)+.075*math.sin(s*1.21)
    def seam(row,s,rows):
        return top(s)*row/rows+(.075*math.sin(s*.67+row*1.9)+.025*math.sin(s*1.43-row) if 0<row<rows else 0)
    parent=min(range(len(PATHS)),key=lambda i:min(math.dist(points[0],p) for p in PATHS[i])+min(math.dist(points[-1],p) for p in PATHS[i])) if PATHS else -1
    def clear_junction(lo,hi):
        for at in [lo,(lo+hi)*.5,hi]:
            x,z,_=along(at)
            for i,road in enumerate(PATHS):
                if i==parent:continue
                clearance=(5.15 if i==0 else 4.2)*.5+1.0
                if any(math.hypot(x-px,z-pz)<clearance for px,pz in road[::2]):return False
        return True
    # Warm grey mortar sits just below the stone face; the joints stay shallow.
    for s in [i*.85 for i in range(math.ceil(lengths[-1]/.85))]:
        l=min(.87,lengths[-1]-s);x,z,yaw=along(s+l/2);y=height(x,z);h=top(s)
        if not clear_junction(s,s+l):continue
        box('mortar',(x,y+h*.5-.06,z),(l+.12,h+.08,.99),color('#898779'),yaw,'walls')
        collider(x,z,l+.15,1.03,y-.2,y+h+.21,yaw,'wall')
    rows=5 if tall else 2
    for row in range(rows):
        s=-rr.uniform(0,.85)
        while s<lengths[-1]:
            length=rr.uniform(.55,1.82);lo=max(0,s);hi=min(lengths[-1],s+length)
            if hi-lo>.17 and clear_junction(lo,hi):
                at=(lo+hi)/2;x,z,yaw=along(at)
                bottom,upper=seam(row,at,rows),seam(row+1,at,rows);rh=upper-bottom
                col=color(rr.choice(['#aaa699','#95998f','#b6afa0','#92968c','#aaa99c','#a39e8f','#b5b0a2','#9d9d90']))
                ax,az,_=along(lo);bx,bz,_=along(hi)
                slope=(height(bx,bz)-height(ax,az)+(seam(row,hi,rows)+seam(row+1,hi,rows)-seam(row,lo,rows)-seam(row+1,lo,rows))*.5)/(hi-lo)
                sculpted_stone((x,height(x,z)+(bottom+upper)*.5,z),(hi-lo-.012,rh*.995,1.04+rr.random()*.08),col,yaw+rr.uniform(-.012,.012),'walls',row*73+int(at*100),slope)
            s+=length
    s=0
    while s<lengths[-1]:
        length=min(rr.uniform(.72,1.32),lengths[-1]-s)
        if length>.12 and clear_junction(s,s+length):
            x,z,yaw=along(s+length/2)
            ax,az,_=along(s);bx,bz,_=along(s+length)
            sculpted_stone((x,height(x,z)+top(s)+.08,z),(length-.012,.23+rr.random()*.07,1.13),color(rr.choice(['#b4aea0','#a29f91','#bab5a7'])),yaw,'walls',int(s*71),(height(bx,bz)-height(ax,az))/length)
        s+=length
    # Irregular soil islands anchor the wall without a continuous stripe.
    for j in range(0,len(points)-1,4):
        s=lengths[j];x,z,yaw=along(s)
        for face in [-1,1]:
            if rr.random()<.43:continue
            p=transform((0,0,face*.65),(x,0,z),yaw)
            verts=[]
            for a,b in [(-.6,-.13),(-.31,.25),(.59,.16),(.44,-.19)]:
                q=transform((a*rr.uniform(.7,1.3),0,b),p,yaw);verts.append((q[0],height(q[0],q[2])+.035,q[2]))
            batch('earth',x,z,'verges').face(verts,color(rr.choice(['#a39b79','#8f9679','#aba286'])))
    growth=art_random(points[0][0],points[0][1],11903+int(side))
    s=.25
    while s<lengths[-1]-.25:
        if clear_junction(s-.2,s+.2):
            x,z,yaw=along(s)
            for face in [-1,1]:ground_moss_patch(x,z,yaw,face,growth)
        s+=growth.uniform(.95,1.75)


def painted_roof(center,w,d,h,rise,yaw,col,group='village'):
    mesh=batch('roof',center[0],center[2],group);rr=art_random(center[0],center[2],41)
    halfw=w/2+.44;halfd=d/2+.45;lean=rr.uniform(-.13,.13)*w
    def vertex(side,t,z):
        x=side*halfw*(1-t)+lean*t
        y=h+rise*t-.13*math.sin(t*math.pi)+.07*math.sin(z*.9+center[0])
        return transform((x,y,z),center,yaw)
    for side in [-1,1]:
        for j in range(6):
            za=-halfd+j*halfd/3;zb=za+halfd/3
            for k in range(3):
                a,b=k/3,(k+1)/3
                verts=[vertex(side,a,za),vertex(side,b,za),vertex(side,b,zb),vertex(side,a,zb)]
                uvs=[(a*halfw*.23,za*.21),(b*halfw*.23,za*.21),(b*halfw*.23,zb*.21),(a*halfw*.23,zb*.21)]
                if side==-1:verts.reverse();uvs.reverse()
                mesh.face(verts,tint(col,(1 if side==-1 else .81)*(.94+rr.random()*.1)),uvs)
        box('wood',transform((side*halfw,h-.14,0),center,yaw),(.20,.26,halfd*2+.10),color('#575e59'),yaw,group)
        # A solid ragged fascia shades the facade directly under the eaves.
        box('roof',transform((side*(halfw-.16),h-.04,0),center,yaw),(.38,.17,halfd*2),tint(col,.72),yaw,group)
    for j in range(max(3,round(d/.72))):
        z=-halfd+(j+.5)*halfd*2/max(3,round(d/.72))
        box('roof',transform((lean,h+rise+.05,z),center,yaw),(.28,.17,.78),tint(col,1.13),yaw,group,.025)


def branching_olive(x,z,s=1):
    rr=art_random(x,z,823);y=height(x,z);lean=rr.uniform(-.42,.42)*s
    hero=(x,z) in [(-7,51),(34,40),(-14,-16),(28,-1),(-25,-17),(-59,63),(-31,76),(49,20)]
    trunk=[(x,y,z),(x+lean,y+1.25*s,z-.18*s),(x+lean*.3,y+2.7*s,z+.10*s)]
    for i in range(2):branch(trunk[i],trunk[i+1],(.37-i*.1)*s,(.25-i*.07)*s,color('#777f72'))
    cols=[color(c) for c in ['#688b86','#8ca59a','#5b827f','#b0bb9d','#7e9c86']]
    crown=rr.uniform(0,TAU)
    for k in range(7):
        a=k*2.399+crown;reach=rr.uniform(1.30,2.42)*s
        if hero:
            a+=.31*math.sin(k*2.7+crown)
            reach*=1.16 if k%3==0 else .81 if k%3==1 else 1.04
        middle=(x+math.cos(a)*reach*.55,y+(2.6+rr.random()*.6)*s,z+math.sin(a)*reach*.55)
        tip=(x+math.cos(a)*reach,y+(3.5+rr.uniform(-.55,.95))*s,z+math.sin(a)*reach)
        branch(trunk[2],middle,.17*s,.10*s,color('#899080'));branch(middle,tip,.10*s,.035*s,color('#9aa18a'))
        for j in range((1 if k in (1,4) else 2) if hero else 3):
            angle=a+j*2.2;cx=tip[0]+math.cos(angle)*.60*s;cz=tip[2]+math.sin(angle)*.60*s;cy=tip[1]+rr.uniform(-.18,.30)*s
            scale=(rr.uniform(.78,1.42)*s,rr.uniform(.23,.46)*s,rr.uniform(.38,.69)*s) if hero else (rr.uniform(.60,.9)*s,rr.uniform(.42,.72)*s,rr.uniform(.58,.88)*s)
            ellipsoid('leaves',(cx,cy,cz),scale,cols[(k+j)%len(cols)],k*3+j,4,7,'groves')
            if j:branch(middle,(cx,cy,cz),.045*s,.015*s,color('#a1a590'))
            b=batch('brush',cx,cz,'leaf_marks')
            for mark in range(16):
                theta=rr.random()*TAU;phi=rr.uniform(.2,2.5)
                p=Vector((cx+math.sin(phi)*math.cos(theta)*scale[0]*1.07,cy+math.cos(phi)*scale[1],cz+math.sin(phi)*math.sin(theta)*scale[2]*1.07))
                direction=Vector((math.cos(theta)*.19*s,rr.uniform(.09,.28)*s,math.sin(theta)*.19*s));across=Vector((-math.sin(theta)*.055*s,0,math.cos(theta)*.055*s))
                b.face([tuple(p-direction),tuple(p+across),tuple(p+direction*.8),tuple(p-across)],cols[(k+j+mark+1)%len(cols)])
    collider(x,z,.70*s,.70*s,y,y+2.7*s,0,'trunk')


def flame_cypress(x,z,h,w,hero=False):
    rr=art_random(x,z,781);y=height(x,z);group='hero' if hero else 'groves'
    lobes=11 if hero else 6;rings=42 if hero else 22;sides=13 if hero else 8
    cols=[color(c) for c in ['#49685e','#678374','#4e746a','#688271','#51786e']]
    branch((x,y,z),(x+w*.28,y+h*.75,z-w*.10),w*.26,w*.055,color('#566657'),group)
    for k in range(lobes):
        phase=k*2.399+(rr.uniform(-.27,.27) if hero else 0);scale=1 if k==0 else rr.uniform(.36,.88) if hero else rr.uniform(.40,.92)
        start=0 if k==0 else rr.uniform(.00,.19)
        reach=0 if k==0 else (rr.uniform(.32,.76) if hero else rr.uniform(.20,.65))*w
        bx=x+math.cos(phase)*reach;bz=z+math.sin(phase)*reach
        radius=w*(.58 if hero and k==0 else .67 if k==0 else rr.uniform(.13,.22) if hero else rr.uniform(.15,.25))
        lh=h*scale;bottom=y+h*start
        def surface(t,a,raised=0):
            bend=math.sin(t*6.5+phase*.28)*t*w*.30 + (t**2)*w*.20*math.cos(phase)
            zz=math.sin(t*7.1+phase)*t*w*.21
            shape=max(.008,math.sin(math.pi*(.035+t*.965))**.67)*(1-t*.52)
            fluted=1+.22*math.sin(a*3+t*20+phase)+.13*math.cos(a*5-t*34)
            r=radius*shape*fluted+raised
            return (bx+bend+math.cos(a+t*.55)*r,bottom+lh*t,bz+zz+math.sin(a+t*.55)*r)
        mesh=batch('cypress',x,z,group)
        for j in range(rings):
            for i in range(sides):
                a=i/sides*TAU;b=(i+1)/sides*TAU;t=j/rings;u=(j+1)/rings
                mesh.face([surface(t,a),surface(u,a),surface(u,b),surface(t,b)],tint(cols[k%len(cols)],.86+rr.random()*.22),[(i/sides,t*2.2),(i/sides,u*2.2),((i+1)/sides,u*2.2),((i+1)/sides,t*2.2)])
        b=batch('brush',x,z,'hero_brushes' if hero else 'leaf_marks')
        for j in range(140 if hero else 19):
            t=rr.uniform(.05,.94);a=rr.random()*TAU;length=rr.uniform(.008,.035);width=rr.uniform(.018,.07)
            pigment=color(rr.choice(['#93a080','#b5af78','#749c9a','#c9bb88','#8ca9a1']))
            for f in range(3):
                lo=t+length*f/3;hi=t+length*(f+1)/3;aa=a+.09*math.sin(lo*18+phase)
                b.face([surface(lo,aa-width,.045),surface(hi,aa-width*.6,.045),surface(hi,aa+width*.6,.045),surface(lo,aa+width,.045)],tint(pigment,.90+rr.random()*.20))
    # Only the woody core is solid; outer foliage can be brushed past in flight.
    collider(x,z,w*.78,w*.78,y,y+h*.85,0,'cypress')


def paint_road_edges():
    rr=random.Random(12889)
    for road_index,path in enumerate(PATHS[:7]):
        for j in range(1,len(path)-1):
            x,z=path[j];p,q=path[j-1],path[j+1];dx,dz=q[0]-p[0],q[1]-p[1];l=max(.01,math.hypot(dx,dz));dx/=l;dz/=l
            for side in [-1,1]:
                xx=x-dz*side*(2.47 if road_index==0 else 2.05);zz=z+dx*side*(2.47 if road_index==0 else 2.05)
                if distance_to_roads(xx,zz)<1.75 or ((xx-3)/16)**2+((zz+15)/12)**2<1:continue
                if j%3==0:
                    sculpted_stone((xx,height(xx,zz)+.06,zz),(rr.uniform(.18,.38),rr.uniform(.13,.24),rr.uniform(.15,.3)),color(rr.choice(['#849e9b','#c2b384','#a0a68b'])),rr.random()*TAU,'verges',j+side)
                for k in range(0 if j%4 else rr.randint(1,3)):
                    ox=xx+rr.uniform(-.14,.14);oz=zz+rr.uniform(-.14,.14);y=height(ox,oz)+.04;hh=rr.uniform(.18,.44)
                    mesh=batch('brush',ox,oz,'verges')
                    mesh.face([(ox-.045,y,oz),(ox-.075+dx*.12,y+hh*.7,oz+dz*.12),(ox+dx*.25,y+hh,oz+dz*.25),(ox+.045,y,oz)],color(rr.choice(['#7e956b','#b4ac6d','#a1a976'])))
            # Broken strokes sit on the lane, following its actual tangent.
            for k in range(4):
                offset=rr.uniform(-2.25,2.25);xx=x-dz*offset;zz=z+dx*offset
                width=rr.uniform(.04,.15);length=rr.uniform(.12,.43);verts=[]
                for a,b in [(-width,0),(-width*.7,length), (width*.4,length*1.08),(width,.04)]:
                    px=xx+dx*b-dz*a;pz=zz+dz*b+dx*a
                    verts.append((px,height(px,pz)+.205,pz))
                batch('path',xx,zz,'lane_brushes').face(list(reversed(verts)),color(rr.choice(['#b2a589','#c4b798','#a2ab9b','#a6aa96','#c6bda1'])))


def far_village():
    global DISTANT_PATHS
    rr=random.Random(73812)
    districts=FAR_DISTRICTS
    routes=[path_samples(p,24) for _,_,p,_ in districts]
    DISTANT_PATHS=routes
    all_roads=placement_roads+[(r,3.0) for r in routes]
    for di,((district,label,controls,target),road) in enumerate(zip(districts,routes)):
        ribbon(road,3.0,'path',color('#aaa98e'),.13,'distant_roads')
        placed=0
        # Try both banks, then an irregular second row. Spacing follows arc
        # length so the town does not become a Cartesian scatter or roof band.
        distances=[0]
        for p,q in zip(road,road[1:]):distances.append(distances[-1]+math.dist(p,q))
        for row in range(3):
            stations=[];distance=5+row*2
            while distance<distances[-1]-4:
                stations.append(distance);distance+=rr.uniform(8.8,12.8)
            for station in stations:
                j=min(range(len(road)),key=lambda i:abs(distances[i]-station))
                x,z=road[j];p=road[max(0,j-1)];q=road[min(len(road)-1,j+1)]
                dx,dz=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dz);dx/=length;dz/=length
                for side in [-1,1]:
                    if placed>=target:break
                    if row and (j<10 or j>len(road)-10) and rr.random()<.5:continue
                    style=(placed*5+di*3+row)%12
                    w=rr.uniform(4.6,6.1);d=rr.uniform(5.1,6.7);h=rr.uniform(4.1,5.6)
                    plan=house_plan(w,d,h,style)
                    front=max([oz+pd/2+.5 for ox,oz,pw,pd,*_ in plan['parts']]+[oz+pd/2 for ox,oz,pw,pd,_ in plan['reserved']])
                    offset=front+2.4+row*11.5+rr.uniform(0,1.0)
                    xx=x-dz*side*offset;zz=z+dx*side*offset
                    if abs(xx)>180 or zz < -285:continue
                    yaw=math.atan2(dz*side,-dx*side)+rr.uniform(-.10,.10)
                    footprints=plan_footprints(plan,xx,zz,yaw)
                    if not clear_house_site(footprints,all_roads):continue
                    house(xx,zz,w,d,h,yaw,style,district,True)
                    placed+=1
        # A few shared lights describe the settlement instead of every facade.
        for j in [len(road)//3,len(road)*2//3]:
            x,z=road[j];light_pools.append(dict(x=x,z=z,radius=3.5,strength=.48))
        district_records.append(dict(id=district,label=label,road=controls,count=placed))
    # Low, inexpensive orchard silhouettes in the gaps preserve visible dark land.
    for cx,cz,rx,rz in [(-116,-222,18,20),(39,-195,16,25),(-40,-185,11,16),(133,-244,19,13)]:
        for i in range(11):
            a=rr.random()*TAU;r=math.sqrt(rr.random());x=cx+math.cos(a)*rx*r;z=cz+math.sin(a)*rz*r
            if any(footprint_distance(f,x,z)<3.0 for f in building_footprints):continue
            if any(math.dist((x,z),p)<4 for road,_ in all_roads for p in road[::3]):continue
            y=height(x,z);scale=rr.uniform(.85,1.3)
            box('wood',(x,y+1.3*scale,z),(.27,2.6*scale,.27),color('#718078'),group='distant_groves')
            for k in range(3):
                ellipsoid('leaves',(x+(k-1)*.9*scale,y+(2.8+.23*(k%2))*scale,z+math.sin(k*2.3)*.65),
                          (1.35*scale,.67*scale,1.1*scale),color(['#718e85','#829a8a','#8c9e8d'][k]),i+k,3,6,'distant_groves')
            if abs(x)<184 and abs(z)<184:collider(x,z,.35,.35,y,y+2.6*scale,0,'trunk')
        for row in range(5):
            pts=[(cx-rx+2*rx*j/16,cz-rz+row*rz*.37+1.5*math.sin(j*.19)) for j in range(17)]
            for p,q in zip(pts,pts[1:]):
                if any(footprint_distance(f,*p)<2 or footprint_distance(f,*q)<2 for f in building_footprints):continue
                if any(math.dist(p,s)<3.0 for road,_ in all_roads for s in road[::3]):continue
                ribbon([p,q],.65,'earth',color('#829486'),.07,'fields')
    return len(distant_records)
