"""Twelve residential silhouettes, shared by the samples and both village LODs.

All placement uses the same rotated footprints as the authored volumes, including
eaves, attached wings, entrance steps and the reserved courtyard.
"""

HOUSE_TYPES = ['longhouse', 'townhouse', 'courtyard', 'annex', 'shop', 'terrace']
HOUSE_LABELS = ['低矮长屋', '窄面两层', 'L 形庭院', '主屋与附房', '店铺住宅', '坡地石基']
building_footprints = []
distant_records = []
district_records = []
window_counts = dict(near=0, nearLit=0, far=0, farLit=0)


def house_plan(w, d, h, style):
    kind, variant = style % 6, (style // 6) % 2
    # ox, oz, width, depth, wall height, roof form, ridge axis, roof rise, floor offset
    if kind == 0:
        mw, md, mh = w*1.38, d*.73, h*.74
        parts = [(0, 0, mw, md, mh, 'hip' if variant else 'gable', 'x', md*.29, 0)]
        if variant: parts.append((-mw*.24, -md*.51, mw*.39, md*.45, mh*.68, 'shed', 'x', .65, 0))
    elif kind == 1:
        mw, md, mh = w*.76, d*.92, max(6.7, h*1.27)
        parts = [(0, 0, mw, md, mh, 'hip' if variant else 'gable', 'z', mw*.35, 0)]
        if variant: parts.append((mw*.57, -md*.20, mw*.26, md*.48, mh*.55, 'shed', 'z', .65, -.18))
    elif kind == 2:
        mw, md, mh = w*.83, d*.77, h*.97
        sign = -1 if variant else 1
        parts = [(0, 0, mw, md, mh, 'gable', 'x' if variant else 'z', min(mw, md)*.34, 0),
                 (sign*mw*.69, md*.23, mw*.44, md*1.27, mh*.63, 'gable', 'z', mw*.21, -.12)]
    elif kind == 3:
        mw, md, mh = w*.94, d*.89, h
        parts = [(0, 0, mw, md, mh, 'gable', 'x' if variant else 'z', min(mw, md)*.35, 0)]
        parts.append(((-1 if variant else 1)*mw*.66, -md*.12, mw*.44, md*.73,
                      mh*.54, 'gable' if variant else 'shed', 'x', mw*.18, -.15))
    elif kind == 4:
        mw, md, mh = w*1.12, d*.81, max(4.4, h*.92)
        parts = [(0, 0, mw, md, mh, 'hip' if variant else 'gable', 'x', md*.32, 0)]
        if variant: parts.append((-mw*.42, -md*.51, mw*.43, md*.47, mh*.73, 'gable', 'z', mw*.15, 0))
    else:
        mw, md, mh = w*.90, d*.84, h*1.06
        parts = [(0, 0, mw, md, mh, 'gable', 'x' if variant else 'z', min(mw, md)*.32, 0),
                 ((-1 if variant else 1)*mw*.59, -md*.12, mw*.36, md*.79,
                  mh*.70, 'shed' if variant else 'gable', 'z', mw*.16, -.72)]
    door_x = -mw*.13 if kind == 4 else mw*.13
    reserved = [(door_x, md/2+.65, 2.0 if kind != 4 else 3.6, 1.5, 'steps')]
    if kind == 2:
        reserved.append(((-1 if variant else 1)*mw*.07, md*.79, mw*.88, md*.70, 'courtyard'))
    if kind == 4:
        reserved.append((0, md/2+.65, mw*.79, 1.45, 'awning'))
    return dict(type=HOUSE_TYPES[kind], label=HOUSE_LABELS[kind], variant=variant,
                template=f'{HOUSE_TYPES[kind]}-{variant+1}', parts=parts, reserved=reserved,
                width=mw, depth=md, height=mh, doorX=door_x)


def plan_footprints(plan, x, z, yaw):
    footprints = []
    for ox, oz, w, d, *rest in plan['parts']:
        px, _, pz = transform((ox, 0, oz), (x, 0, z), yaw)
        footprints.append(dict(x=px, z=pz, hx=w/2+.46, hz=d/2+.46, yaw=yaw, kind='volume'))
    for ox, oz, w, d, kind in plan['reserved']:
        px, _, pz = transform((ox, 0, oz), (x, 0, z), yaw)
        footprints.append(dict(x=px, z=pz, hx=w/2, hz=d/2, yaw=yaw, kind=kind))
    return footprints


def footprint_overlap(a, b, gap=.45):
    def axes(f):
        return [(math.cos(f['yaw']), -math.sin(f['yaw'])), (math.sin(f['yaw']), math.cos(f['yaw']))]
    aa, bb = axes(a), axes(b)
    dx, dz = b['x']-a['x'], b['z']-a['z']
    for ux, uz in aa+bb:
        ra = a['hx']*abs(ux*aa[0][0]+uz*aa[0][1])+a['hz']*abs(ux*aa[1][0]+uz*aa[1][1])
        rb = b['hx']*abs(ux*bb[0][0]+uz*bb[0][1])+b['hz']*abs(ux*bb[1][0]+uz*bb[1][1])
        if abs(dx*ux+dz*uz) >= ra+rb+gap: return False
    return True


def footprint_distance(f, x, z):
    dx, dz = x-f['x'], z-f['z']; co, si = math.cos(f['yaw']), math.sin(f['yaw'])
    return math.hypot(max(0, abs(dx*co-dz*si)-f['hx']), max(0, abs(dx*si+dz*co)-f['hz']))


def clear_house_site(footprints, roads):
    if any(footprint_overlap(a, b) for a in footprints for b in building_footprints): return False
    for f in footprints:
        if any(footprint_distance(f, px, pz) < width/2+.5 for points, width in roads for px, pz in points[::2]): return False
        # Keep the approach to the church and both flanking streets open.
        if footprint_overlap(f, dict(x=5,z=-5,hx=17,hz=13,yaw=0), 0): return False
    return True


def residential_roof(center, w, d, h, rise, yaw, col, wall_col, form, axis, group, simple):
    if axis == 'x': w, d, yaw = d, w, yaw+math.pi/2
    b=batch('roof',center[0],center[2],group)
    def v(x,y,z): return transform((x,y,z),center,yaw)
    hw, hd = w/2+.42, d/2+.44
    if form == 'hip':
        ridge=max(.15,hd-min(w*.52,hd*.78))
        for sign in [-1,1]:
            verts=[v(sign*hw,h,-hd),v(0,h+rise,-ridge),v(0,h+rise,ridge),v(sign*hw,h,hd)]
            if sign == -1: verts.reverse()
            b.face(verts,tint(col,.92 if sign<0 else .78))
            verts=[v(-hw,h,sign*hd),v(hw,h,sign*hd),v(0,h+rise,sign*ridge)]
            if sign<0: verts.reverse()
            b.face(verts,tint(col,1.03 if sign>0 else .83))
        box('roof',v(0,h+rise+.03,0),(.22,.15,ridge*2+.18),col,yaw,group)
    elif form == 'shed':
        b.face([v(-hw,h+rise,-hd),v(-hw,h+rise,hd),v(hw,h,hd),v(hw,h,-hd)],col)
        wall=batch('plaster',center[0],center[2],group)
        wall.face([v(-w/2,h,-d/2),v(-w/2,h,d/2),v(-w/2,h+rise,d/2),v(-w/2,h+rise,-d/2)],wall_col)
        for sign in [-1,1]:
            verts=[v(-w/2,h,sign*d/2),v(w/2,h,sign*d/2),v(-w/2,h+rise,sign*d/2)]
            if sign<0: verts.reverse()
            wall.face(verts,wall_col)
    else:
        if not simple:
            painted_roof(center,w,d,h,rise,yaw,col,group)
            lean=art_random(center[0],center[2],41).uniform(-.13,.13)*w
        else:
            lean=0
            for sign in [-1,1]:
                verts=[v(sign*hw,h,-hd),v(0,h+rise,-hd),v(0,h+rise,hd),v(sign*hw,h,hd)]
                if sign<0: verts.reverse()
                b.face(verts,tint(col,.95 if sign<0 else .80))
        for sign in [-1,1]:
            verts=[v(-w/2,h,sign*d/2),v(w/2,h,sign*d/2),v(lean,h+rise,sign*d/2)]
            if sign<0: verts.reverse()
            batch('plaster',center[0],center[2],group).face(verts,wall_col)
    if form != 'gable':
        for sign in [-1,1]:
            box('roof',v(0,h-.05,sign*hd),(hw*2,.16,.20),tint(col,.75),yaw,group)


def house(x,z,w,d,h,yaw,style=0,district='main',simple=False,record=True):
    plan=house_plan(w,d,h,style); rr=art_random(x,z,991+style)
    group='distant_village' if simple else 'village'
    wall_col=color(rr.choice(['#d9d0b9','#c6c7bc','#d6cab1','#c7beaa','#e0d5bb','#bfc3b9']))
    roof_col=color(rr.choice(['#7d8e98','#8c969b','#6c8394','#8b9494','#738694']))
    if simple:
        wall_col=lerp(wall_col,color('#81939e'),.20)
        roof_col=lerp(roof_col,color('#7a8b9b'),.25)
    footprints=plan_footprints(plan,x,z,yaw)
    mw,md,mh=plan['width'],plan['depth'],plan['height']
    main_corners=[transform((a*mw/2,0,b*md/2),(x,0,z),yaw) for a in [-1,1] for b in [-1,1]]
    floor=max(height(p[0],p[2]) for p in main_corners)+(.45 if plan['type']=='terrace' else .17)
    center=(x,floor,z); volume_records=[]
    for part_index,(ox,oz,pw,pd,ph,form,axis,rise,level) in enumerate(plan['parts']):
        px,_,pz=transform((ox,0,oz),center,yaw)
        corners=[transform((a*pw/2,0,b*pd/2),(px,0,pz),yaw) for a in [-1,1] for b in [-1,1]]
        heights=[height(p[0],p[2]) for p in corners]
        bottom=min(heights)-.16; top=max(floor+level,max(heights)+.12)
        origin=(px,top,pz)
        box('wallstone', (px,(bottom+top)/2,pz),(pw+.12,top-bottom,pd+.12),color('#aaa99b'),yaw,group)
        box('plaster',(px,top+ph/2,pz),(pw,ph,pd),tint(wall_col,1-part_index*.07),yaw,group,0 if simple else .045)
        residential_roof(origin,pw,pd,ph,rise,yaw,roof_col,wall_col,form,axis,group,simple)
        flyable=footprint_overlap(dict(x=px,z=pz,hx=pw/2+.45,hz=pd/2+.45,yaw=yaw),dict(x=0,z=0,hx=184,hz=184,yaw=0),0)
        volume_records.append(dict(x=px,z=pz,width=pw,depth=pd,ground=top,height=ph,rise=rise,roof=form,axis=axis,flyable=flyable))
        if not simple or flyable:
            collider(px,pz,pw+.13,pd+.13,bottom,top+ph,yaw,'distant_house' if simple else 'building')
            if form=='shed':
                collider(px,pz,pw+.88,pd+.88,top+ph-.12,top+ph+rise,yaw,'roof')
            else:
                collider(px,pz,pw+.88,pd+.88,top+ph-.12,top+ph+rise*.5,yaw,'roof')
                rw,rd=(pw,pd) if axis=='z' else (pd,pw)
                roof_yaw=yaw+(math.pi/2 if axis=='x' else 0)
                lean=art_random(px,pz,41).uniform(-.13,.13)*rw if form=='gable' and not simple else 0
                cap=transform((lean*.75,0,0),origin,roof_yaw)
                collider(cap[0],cap[2],(rw+.88)*.5+abs(lean)*.5,rd+.88,top+ph+rise*.5,top+ph+rise+.14,roof_yaw,'roof')
        if part_index and not simple:
            box('wood',transform((0,1.05,pd/2+.045),origin,yaw),(.92,1.95,.07),color('#7e8170'),yaw,group)
        if part_index: continue
        # Street frontage: doors replace a ground-floor window instead of overlapping it.
        floors=2 if ph>6.0 else 1; columns=max(2,round(pw/2.5))
        for side in ([1] if simple else [-1,1]):
            for story in range(1 if simple else floors):
                for k in range(columns):
                    xx=-pw*.32+k*pw*.64/(columns-1); yy=1.75+story*2.65
                    if side==1 and story==0 and abs(xx-plan['doorX'])<1.17: continue
                    lit=rr.random()<(.34 if simple else .49)
                    key='far' if simple else 'near'; window_counts[key]+=1;window_counts[key+'Lit']+=int(lit)
                    box('dark',transform((xx,yy,side*(pd/2+.028)),origin,yaw),(.88,1.21,.055),color('#4a5a60'),yaw,group)
                    box('window_far' if simple and lit else 'window' if lit else 'wood',transform((xx,yy,side*(pd/2+.065)),origin,yaw),(.61,.98,.04),color('#e0c48c') if lit else color('#6c7e79'),yaw,group)
                    if not simple:
                        box('wallstone',transform((xx,yy-.64,side*(pd/2+.12)),origin,yaw),(1.07,.13,.25),wall_col,yaw,group)
                        box('wood',transform((xx,yy,side*(pd/2+.095)),origin,yaw),(.06,.98,.04),color('#6a7065'),yaw,group)
                        if (k+story+style)%3==0:
                            for sign in [-1,1]:box('wood',transform((xx+sign*.59,yy,side*(pd/2+.08)),origin,yaw),(.27,1.13,.08),color('#718277'),yaw,group)
        for side in [-1,1]:
            for k in range(1 if simple else max(2,round(pd/3.1))):
                zz=0 if simple else -pd*.28+k*pd*.56/(max(2,round(pd/3.1))-1)
                # Attached side wings own this part of the facade.
                if any(ox2*side>0 and abs(zz-oz2)<dd/2+.3 for ox2,oz2,ww,dd,*_ in plan['parts'][1:]):continue
                lit=rr.random()<(.34 if simple else .43)
                key='far' if simple else 'near';window_counts[key]+=1;window_counts[key+'Lit']+=int(lit)
                box('dark',transform((side*(pw/2+.03),1.95,zz),origin,yaw),(.06,1.24,.88),color('#4a5a60'),yaw,group)
                box('window_far' if simple and lit else 'window' if lit else 'wood',transform((side*(pw/2+.07),1.95,zz),origin,yaw),(.04,1.0,.62),color('#ddc393') if lit else color('#667b75'),yaw,group)
        dx=plan['doorX']; front=pd/2
        if not simple:
            if plan['type']=='shop' and plan['variant']:
                arch('dark',transform((dx,.04,front+.035),origin,yaw),1.85,2.75,color('#4b5758'),yaw,group)
                arch('wood',transform((dx,.08,front+.065),origin,yaw),1.55,2.52,color('#898170'),yaw,group)
            else:
                box('dark',transform((dx,1.08,front+.035),origin,yaw),(1.39,2.16,.08),color('#465759'),yaw,group)
                box('wood',transform((dx,1.04,front+.085),origin,yaw),(1.12,2.06,.06),color('#89816a'),yaw,group)
                box('wallstone',transform((dx,2.22,front+.13),origin,yaw),(1.61,.18,.29),wall_col,yaw,group)
            # Steps reach the sampled ground even on the steeper terrace sites.
            door_point=transform((dx,0,front+.9),origin,yaw)
            drop=max(.18,top-height(door_point[0],door_point[2])); steps=min(7,max(1,math.ceil(drop/.20)))
            for j in range(steps):
                p=transform((dx,-drop+(j+.5)*drop/steps,front+.98-j*.12),origin,yaw)
                box('wallstone',p,(1.85,drop/steps,.43),color('#bcb8a5'),yaw,group,.035)
                collider(p[0],p[2],1.85,.43,p[1]-drop/steps/2,p[1]+drop/steps/2,yaw,'step')
            if plan['type']=='shop':
                aw=pw*.74
                b=batch('roof',px,pz,group)
                b.face([transform(v,origin,yaw) for v in [(-aw/2,2.87,front),( -aw/2,2.55,front+1.22),(aw/2,2.55,front+1.22),(aw/2,2.87,front)]],tint(roof_col,1.12))
                for sx in [-aw/2+.12,aw/2-.12]:
                    post=transform((sx,1.27,front+1.10),origin,yaw)
                    box('wood',post,(.10,2.55,.10),color('#777a68'),yaw,group)
                    collider(post[0],post[2],.13,.13,top,top+2.55,yaw,'awning_post')
                ap=transform((0,2.7,front+.62),origin,yaw)
                collider(ap[0],ap[2],aw,1.3,top+2.50,top+2.92,yaw,'awning')
            # Small irregular areas of repair, rather than a noisy full-wall overlay.
            for k in range(2):
                xx=(-.38+k*.70)*pw; yy=.42+k*.41
                b=batch('plaster',px,pz,group)
                b.face([transform(v,origin,yaw) for v in [(xx-.30,yy-.16,front+.009),(xx+.36,yy-.13,front+.009),(xx+.27,yy+.31,front+.009),(xx-.23,yy+.21,front+.009)]],tint(wall_col,.88+k*.06))
            if style%3!=1:
                cp=transform((-pw*.24,ph+rise*.65,-pd*.22),origin,yaw)
                box('plaster',cp,(.55,1.25,.58),tint(wall_col,.88),yaw,group)
                box('wallstone',(cp[0],cp[1]+.66,cp[2]),(.72,.14,.75),color('#aaa99c'),yaw,group)
        else:
            box('wood',transform((dx,.95,front+.035),origin,yaw),(.92,1.9,.04),color('#687778'),yaw,group)
    if plan['type']=='courtyard' and not simple:
        # One low boundary on the back of the yard leaves the street entrance open.
        p=transform(((-1 if plan['variant'] else 1)*mw*.05,.38,md*1.09),center,yaw)
        box('wallstone',p,(mw*.69,.76,.42),color('#b7b6a6'),yaw,group,.09)
        collider(p[0],p[2],mw*.69,.42,floor,floor+.76,yaw,'courtyard_wall')
    door=transform((plan['doorX'],0,md/2+.65),center,yaw)
    rec=dict(x=x,z=z,width=mw,depth=md,height=mh,ground=floor,yaw=yaw,style=style,
             type=plan['type'],variant=plan['variant'],template=plan['template'],district=district,
             footprint=footprints,volumes=volume_records,door=[door[0],floor,door[2]],
             flyable=any(v['flyable'] for v in volume_records))
    if record:
        (distant_records if simple else house_records).append(rec)
        building_footprints.extend(footprints)
        radius=max(math.hypot(f['x']-x,f['z']-z)+math.hypot(f['hx'],f['hz']) for f in footprints)
        occupied.append((x,z,radius))
    if not simple and rr.random()<.60:light_pools.append(dict(x=door[0],z=door[2],radius=3.1,strength=.65))
    return rec
