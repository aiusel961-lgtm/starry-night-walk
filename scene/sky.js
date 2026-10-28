/* Original spherical brushwork, advected by a continuous flow map. The two
   overlapping flow phases crossfade without accumulating stretch or a reset. */
window.createLivingSky=async function(THREE,renderer,config,clock,pointScale){
  const TAU=Math.PI*2,W=4096,H=2048;
  let seed=3271889;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const wrap=u=>((u%1)+1)%1;
  const canvas=(w,h)=>Object.assign(document.createElement('canvas'),{width:w,height:h});
  // Compose connected cloud ribbons before adding texture. Their two curls
  // remain inside the three principal views; the rest of the dome is quieter.
  // Coordinates use equirectangular UVs, with twice the metric scale along U.
  const tracks=[
    {width:.014,gain:1,points:[[.035,.425],[.10,.425],[.158,.416],[.194,.391],[.230,.359],[.274,.363],[.297,.392],[.282,.425],[.249,.431],[.231,.413],[.238,.394],[.256,.391],[.268,.404],[.259,.416],[.247,.409]]},
    {width:.012,gain:.80,points:[[.287,.444],[.327,.435],[.353,.413],[.366,.380],[.391,.372],[.412,.396],[.405,.427],[.380,.437],[.365,.422],[.369,.401],[.389,.397],[.397,.415]]},
    {width:.011,gain:.57,points:[[.48,.402],[.55,.379],[.60,.369],[.647,.385],[.666,.414],[.646,.438],[.621,.426],[.622,.405],[.642,.401],[.648,.415]]},
    {width:.009,gain:.48,points:[[.75,.429],[.81,.401],[.856,.378],[.893,.388],[.908,.420],[.888,.437],[.865,.423],[.873,.405],[.888,.413]]},
    {width:.008,gain:.38,points:Array.from({length:81},(_,i)=>{const u=i/80;return [u,.466+.008*Math.sin(u*TAU*5)+.004*Math.cos(u*TAU*11)];})}
  ];
  function curve(points,t){
    const at=clamp(t,0,.999999)*(points.length-1),i=Math.floor(at),f=at-i;
    const a=points[Math.max(0,i-1)],b=points[i],c=points[i+1],d=points[Math.min(points.length-1,i+2)];
    return [0,1].map(k=>.5*(2*b[k]+(-a[k]+c[k])*f+(2*a[k]-5*b[k]+4*c[k]-d[k])*f*f+(-a[k]+3*b[k]-3*c[k]+d[k])*f*f*f));
  }
  const bins=Array.from({length:64*32},()=>[]);
  for(const track of tracks){
    track.samples=Array.from({length:(track.points.length-1)*18+1},(_,i)=>curve(track.points,i/((track.points.length-1)*18)));
    for(let i=0;i<track.samples.length-1;i++){
      const a=track.samples[i],b=track.samples[i+1],dx=(b[0]-a[0])*2,dy=b[1]-a[1],length=Math.hypot(dx,dy);
      if(length<1e-8)continue;
      const progress=i/(track.samples.length-1),taper=track===tracks[tracks.length-1]?1:1-.65*clamp((progress-.45)/.55,0,1);
      const breadth=(.83+.22*Math.sin(i*.041)+.13*Math.cos(i*.117))*taper;
      const segment={x:a[0]*2,y:a[1],dx,dy,l2:length*length,tx:dx/length,ty:dy/length,width:track.width*breadth,gain:track.gain*(.80+.20*Math.sin(i*.053+.5))};
      const margin=track.width*4;
      for(let by=Math.max(0,Math.floor((Math.min(a[1],b[1])-margin)*32));by<=Math.min(31,Math.floor((Math.max(a[1],b[1])+margin)*32));by++){
        for(let bx=Math.floor((Math.min(a[0],b[0])-margin*.5)*64);bx<=Math.floor((Math.max(a[0],b[0])+margin*.5)*64);bx++){
          if(bx>=0&&bx<64)bins[by*64+bx].push(segment);
        }
      }
    }
  }
  const atlasW=768,atlasH=384,atlas=new Float32Array(atlasW*atlasH*3);
  for(let iy=0;iy<atlasH;iy++)for(let ix=0;ix<atlasW;ix++){
    const u=ix/atlasW,v=iy/atlasH;
    let nearest=Infinity,best=null,density=0;
    for(const s of bins[Math.min(31,Math.floor(v*32))*64+Math.min(63,Math.floor(u*64))]){
      const x=u*2-s.x,y=v-s.y,t=clamp((x*s.dx+y*s.dy)/s.l2,0,1),distance=(x-s.dx*t)**2+(y-s.dy*t)**2;
      if(distance<nearest){nearest=distance;best=s;}
      density=Math.max(density,Math.exp(-distance/(s.width*s.width))*s.gain);
    }
    let dx=1,dy=.12*Math.sin(u*TAU*3+v*13)+.07*Math.sin(u*TAU*7-v*21);
    for(const [cx,cy,r]of [[.350,.302,.062],[.450,.312,.095],[.80,.28,.055]]){
      const x=(wrap(u-cx+.5)-.5)*2,y=v-cy,weight=Math.exp(-(x*x+y*y)/(r*r))*1.6;
      dx-=y/r*weight;dy+=x/r*weight;
    }
    if(best){
      const follow=Math.exp(-nearest/(best.width*best.width*7));
      dx=dx*(1-follow)+best.tx*follow;dy=dy*(1-follow)+best.ty*follow;
    }
    const length=Math.max(.01,Math.hypot(dx,dy)),index=(iy*atlasW+ix)*3;
    atlas[index]=dx/length*.5;atlas[index+1]=dy/length;atlas[index+2]=density;
  }
  function sample(u,v,channel){
    const x=wrap(u)*atlasW,y=clamp(v,0,.99999)*atlasH,ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
    const a=(iy*atlasW+ix)*3+channel,b=(iy*atlasW+(ix+1)%atlasW)*3+channel;
    const c=(Math.min(iy+1,atlasH-1)*atlasW+ix)*3+channel,d=(Math.min(iy+1,atlasH-1)*atlasW+(ix+1)%atlasW)*3+channel;
    return (atlas[a]*(1-fx)+atlas[b]*fx)*(1-fy)+(atlas[c]*(1-fx)+atlas[d]*fx)*fy;
  }
  const field=(u,v)=>[sample(u,v,0),sample(u,v,1)];
  const cloudDensity=(u,v)=>clamp(sample(u,v,2)*(.92+.10*Math.sin(u*TAU*35+v*91)),0,1);
  const paint=canvas(W,H),ctx=paint.getContext('2d');
  const gradient=ctx.createLinearGradient(0,0,0,H);
  for(const [p,c] of [[0,'#091b36'],[.16,'#193f71'],[.31,'#244f88'],[.44,'#285387'],[.52,'#263e5b'],[1,'#101e37']])gradient.addColorStop(p,c);
  ctx.fillStyle=gradient;ctx.fillRect(0,0,W,H);ctx.lineCap='round';
  // A broad blue underpainting supports the strokes, without flattening their
  // negative spaces into a uniform field of pale specks.
  const under=canvas(2048,1024),uc=under.getContext('2d'),pixels=uc.createImageData(2048,1024);
  for(let y=30;y<525;y++)for(let x=0;x<2048;x++){
    const u=x/2048,v=y/1024,d=cloudDensity(u,v);
    const grain=.5+.23*Math.sin(u*TAU*18+y*.101)+.14*Math.sin(u*TAU*56-y*.087)+.08*Math.sin(u*TAU*140+y*.61);
    const strength=clamp(d*(.72+grain*.28),0,1),i=(y*2048+x)*4;
    pixels.data[i]=48+strength*100;pixels.data[i+1]=87+strength*91;pixels.data[i+2]=140+strength*49;
    pixels.data[i+3]=Math.round(clamp(d*.70,0,.75)*255);
  }
  uc.putImageData(pixels,0,0);ctx.drawImage(under,0,0,W,H);
  function stroke(u,v,length,width,color,alpha,ridge=false,direction=null){
    const points=[[u*W,v*H]];
    for(let k=0;k<6;k++){
      const f=direction||field(u,v),l=Math.max(.00001,Math.hypot(f[0]*W,f[1]*H));
      u+=f[0]/l*length/6;v+=f[1]/l*length/6;points.push([u*W,v*H]);
    }
    const sides=[];
    for(let k=0;k<points.length;k++){
      const a=points[Math.max(0,k-1)],b=points[Math.min(points.length-1,k+1)],dx=b[0]-a[0],dy=b[1]-a[1],l=Math.max(.01,Math.hypot(dx,dy));
      const taper=k===0?.56:k===points.length-1?.28:1;
      const half=width*.5*taper*(.65+random()*.65);sides.push([-dy/l*half,dx/l*half]);
    }
    alpha*=clamp((.515-v)/.04,0,1);
    for(const offset of [-W,0,W]){
      if(points[0][0]+offset<-length||points[0][0]+offset>W+length)continue;
      ctx.fillStyle=color;ctx.globalAlpha=alpha;ctx.beginPath();
      for(let k=0;k<points.length;k++)ctx.lineTo(points[k][0]+offset+sides[k][0],points[k][1]+sides[k][1]);
      for(let k=points.length-1;k>=0;k--)ctx.lineTo(points[k][0]+offset-sides[k][0],points[k][1]-sides[k][1]);
      ctx.closePath();ctx.fill();
      if(ridge){
        ctx.strokeStyle='#e5dfb6';ctx.globalAlpha=alpha*.30;ctx.lineWidth=.5+width*.09;
        ctx.beginPath();ctx.moveTo(points[0][0]+offset,points[0][1]);
        for(let k=1;k<points.length;k++)ctx.lineTo(points[k][0]+offset+sides[k][0]*.32,points[k][1]+sides[k][1]*.32);ctx.stroke();
      }
    }
  }
  const colors=['#152e59','#21477d','#315e98','#4879ad','#759dbb','#a5bec8','#c8d2c4','#e3dfb8'];
  // Longer grouped strokes keep a visible direction. Bright pigment is
  // concentrated along the connected ribbons instead of scattered everywhere.
  for(let i=0;i<44000;i++){
    const u=random(),v=.065+random()*.435,d=cloudDensity(u,v);
    const col=clamp(Math.floor(random()*2.6+d*1.8),0,4);
    stroke(u,v,10+random()*31,2+random()*4.1,colors[col],.54+random()*.35,random()<.15);
  }
  for(let i=0;i<41000;i++){
    const u=random(),v=.08+random()*.407,d=cloudDensity(u,v);
    if(random()>.045+d*.88)continue;
    const col=clamp(Math.floor(1+random()*1.9+d*4.4),1,7);
    stroke(u,v,16+random()*39,2.1+random()*5.2,colors[col],.60+random()*.34,true);
  }
  // Hand-laid parallel brush bundles define the S-shaped cloud and curled
  // ends. Each mark has an irregular taper; dark lanes remain between bundles.
  for(const track of tracks){
    for(let strand=-6;strand<=6;strand++){
      for(let j=2;j<track.samples.length-2;j+=3+Math.floor(random()*4)){
        if(random()<.22+.16*Math.sin(j*.12+strand))continue;
        const p=track.samples[j],q=track.samples[j+1],dx=(q[0]-p[0])*2,dy=q[1]-p[1],l=Math.hypot(dx,dy);
        const progress=j/(track.samples.length-1),taper=track===tracks[tracks.length-1]?1:1-.65*clamp((progress-.45)/.55,0,1);
        const offset=(strand/6+Math.sin(j*.35+strand)*.085)*track.width*(.83+.22*Math.sin(j*.041)+.13*Math.cos(j*.117))*taper;
        const u=p[0]-dy/l*offset*.5,v=p[1]+dx/l*offset;
        const pale=Math.abs(strand)<3,chosen=pale?3+Math.floor(random()*4):2+Math.floor(random()*3);
        stroke(u,v,(14+random()*34)*Math.max(.45,taper),1.7+random()*3.2,colors[chosen],(.58+random()*.34)*track.gain,pale,[dx/l*.5,dy/l]);
      }
    }
  }
  ctx.globalAlpha=1;
  const colorMap=new THREE.CanvasTexture(paint);colorMap.colorSpace=THREE.SRGBColorSpace;
  colorMap.flipY=false;colorMap.wrapS=THREE.RepeatWrapping;
  colorMap.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
  const fw=512,fh=256,flowData=new Uint8Array(fw*fh*4);
  for(let y=0;y<fh;y++)for(let x=0;x<fw;x++){
    const f=field(x/fw,y/fh),i=(y*fw+x)*4;
    flowData[i]=Math.round((f[0]*.5+.5)*255);flowData[i+1]=Math.round((f[1]*.5+.5)*255);flowData[i+2]=0;flowData[i+3]=255;
  }
  const flowMap=new THREE.DataTexture(flowData,fw,fh,THREE.RGBAFormat);
  flowMap.wrapS=THREE.RepeatWrapping;flowMap.minFilter=flowMap.magFilter=THREE.LinearFilter;flowMap.needsUpdate=true;
  const root=new THREE.Group();root.name='Living painted sky';root.frustumCulled=false;
  const material=new THREE.ShaderMaterial({
    uniforms:{uPaint:{value:colorMap},uFlow:{value:flowMap},uTime:clock,uSpeed:{value:config.SKY_FLOW_SPEED},uStrength:{value:config.SKY_FLOW_STRENGTH}},
    side:THREE.BackSide,depthWrite:false,depthTest:true,fog:false,
    vertexShader:'varying vec3 vDirection;void main(){vDirection=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:`
      uniform sampler2D uPaint,uFlow;uniform float uTime,uSpeed,uStrength;varying vec3 vDirection;
      void main(){
        vec3 d=normalize(vDirection);vec2 uv=vec2(atan(d.z,d.x)/6.28318530718+.5,.5-asin(clamp(d.y,-1.,1.))/3.14159265359);
        vec2 velocity=(texture2D(uFlow,uv).rg*2.-1.)*uStrength;
        velocity*=smoothstep(.04,.12,uv.y)*(1.-smoothstep(.46,.51,uv.y));
        float phase=fract(uTime*uSpeed*.042),other=fract(phase+.5),blend=abs(phase-.5)*2.;
        vec3 a=texture2D(uPaint,uv-velocity*(phase-.5)).rgb;
        vec3 b=texture2D(uPaint,uv-velocity*(other-.5)).rgb;
        vec3 color=mix(a,b,blend);
        color=mix(color,vec3(dot(color,vec3(.2126,.7152,.0722))),.075)*.84;
        float highCloud=.5+.25*sin(d.x*19.+d.z*11.)+.16*sin(d.x*41.-d.z*23.);
        vec3 zenith=vec3(.012,.035,.09)+vec3(.009,.018,.022)*highCloud;
        color=mix(zenith,color,smoothstep(.04,.18,uv.y));
        gl_FragColor=vec4(color,1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`
  });
  const dome=new THREE.Mesh(new THREE.SphereGeometry(590,64,32),material);dome.name='Flowing impasto curls';dome.renderOrder=-20;dome.frustumCulled=false;root.add(dome);
  const sphere=(u,v,r=515)=>new THREE.Vector3(Math.cos((u-.5)*TAU)*Math.sin(v*Math.PI)*r,Math.cos(v*Math.PI)*r,Math.sin((u-.5)*TAU)*Math.sin(v*Math.PI)*r);
  // Keep the high-elevation stars as small points. Their large halos can
  // clip against the top edge and read as blurry circular patches.
  const special=[[.142,.412,.78],[.198,.431,1.10],[.300,.389,.82],[.335,.447,.76],[.288,.340,.45],[.416,.453,.86],[.434,.286,.87],[.350,.302,.91],[.56,.25,.38],[.718,.386,1.02],[.80,.28,.88],[.945,.428,.76]];
  const positions=[],sizes=[],phases=[],starColors=[];
  for(let i=0;i<520;i++){
    const u=random(),v=Math.acos(.08+.92*random())/Math.PI,large=i<special.length;
    const uv=large?special[i]:[u,v,1],p=sphere(uv[0],uv[1]);positions.push(...p.toArray());
    sizes.push(large?5.8*uv[2]:.45+random()*1.3);phases.push(random()*TAU);
    starColors.push(...new THREE.Color(i%5===0?'#b3cce1':large?'#ffe6ac':'#d4dcda').toArray());
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));g.setAttribute('aSize',new THREE.Float32BufferAttribute(sizes,1));g.setAttribute('aPhase',new THREE.Float32BufferAttribute(phases,1));g.setAttribute('color',new THREE.Float32BufferAttribute(starColors,3));
  const sm=new THREE.ShaderMaterial({uniforms:{uTime:clock,uPointScale:pointScale},vertexColors:true,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,
    vertexShader:`attribute float aSize,aPhase;uniform float uTime,uPointScale;varying vec3 vColor;varying float vAlpha;
      void main(){vec4 p=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*p;gl_PointSize=clamp(aSize*uPointScale/max(1.,-p.z),1.,20.);vColor=color;vAlpha=.83+.12*sin(uTime*.48+aPhase);}`,
    fragmentShader:`varying vec3 vColor;varying float vAlpha;void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p),a=exp(-r*9.)+.18*exp(-r*2.8);if(a<.015)discard;gl_FragColor=vec4(vColor*1.12,a*vAlpha);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const stars=new THREE.Points(g,sm);stars.name='Distant stars';stars.frustumCulled=false;stars.renderOrder=-16;root.add(stars);
  function haloTexture(){
    const c=canvas(256,256),x=c.getContext('2d');
    const glow=x.createRadialGradient(128,128,12,128,128,121);glow.addColorStop(0,'#efd075aa');glow.addColorStop(.32,'#e6cc7b77');glow.addColorStop(.62,'#bcc9aa28');glow.addColorStop(1,'#8faeb900');x.fillStyle=glow;x.fillRect(0,0,256,256);
    for(let ring=9;ring>=0;ring--)for(let i=0;i<40;i++){
      if(random()<.10+ring*.018)continue;
      const a=i/40*TAU+ring*.17,r=11+ring*9+5*Math.sin(a*3+ring*.38)+(random()-.5)*7,end=a+.045+random()*.15;
      const palette=ring<4?['#eed482','#f9e4a2','#c2b66d']:ring<7?['#ccce9d','#a6baac','#e1d9a4']:['#7e9eb0','#b8c7b1','#4c7f9e'];
      x.strokeStyle=palette[Math.floor(random()*3)];x.globalAlpha=.40+random()*.46;x.lineWidth=3.2+random()*4.6;x.lineCap='round';x.beginPath();x.arc(128,128,Math.max(2,r),a,end);x.stroke();
    }
    x.globalAlpha=.95;x.fillStyle='#f7d975';x.beginPath();
    for(let i=0;i<24;i++){const a=i/24*TAU,r=24+random()*7;x.lineTo(128+Math.cos(a)*r,128+Math.sin(a)*r);}x.closePath();x.fill();
    for(let i=0;i<18;i++){const a=random()*TAU,r=random()*18;x.strokeStyle=i%3?'#ffe9a4':'#bcac60';x.lineWidth=2+random()*3;x.beginPath();x.moveTo(128+Math.cos(a)*r,128+Math.sin(a)*r);x.lineTo(132+Math.cos(a)*r,132+Math.sin(a)*r);x.stroke();}
    const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;return t;
  }
  const haloMaps=Array.from({length:4},haloTexture),halos=[];
  for(let i=0;i<special.length;i++){
    const [u,v,s]=special[i];
    const zenithStar=i===4||i===6||i===8;
    const m=new THREE.SpriteMaterial({map:haloMaps[i%4],transparent:true,depthWrite:false,fog:false,opacity:zenithStar?0:.95});
    const sprite=new THREE.Sprite(m);sprite.position.copy(sphere(u,v,510));sprite.scale.set(75*s,75*s,1);sprite.name='Painted star halo '+i;sprite.renderOrder=-15;
    root.add(sprite);halos.push(sprite);
  }
  const moonCanvas=canvas(512,512),mc=moonCanvas.getContext('2d');
  const glow=mc.createRadialGradient(246,256,50,246,256,247);glow.addColorStop(0,'#edc96c88');glow.addColorStop(.52,'#e1c87536');glow.addColorStop(.85,'#b5c5a30d');glow.addColorStop(1,'#b5c5a300');mc.fillStyle=glow;mc.fillRect(0,0,512,512);
  for(let ring=0;ring<9;ring++)for(let i=0;i<72;i++){
    if(random()<.21)continue;const a=i/72*TAU+ring*.12,r=119+ring*11+7*Math.sin(a*4+ring*.3)+(random()-.5)*8;
    mc.strokeStyle=['#ddc16e','#e9d99b','#bcbf97','#779da9'][Math.min(3,Math.floor(ring*.4))];mc.globalAlpha=.25+random()*.43;mc.lineWidth=3+random()*5;mc.lineCap='round';mc.beginPath();mc.arc(246,256,r,a,a+.035+random()*.08);mc.stroke();
  }mc.globalAlpha=1;
  const disc=canvas(512,512),dc=disc.getContext('2d');dc.fillStyle='#e7bd5a';dc.beginPath();dc.arc(246,256,129,0,TAU);dc.fill();dc.save();dc.clip();
  for(let i=0;i<1350;i++){
    const x=115+random()*263,y=124+random()*265;
    dc.strokeStyle=['#f6d780','#d6aa4e','#ffebaa','#b99b4b'][i%4];dc.globalAlpha=.52+random()*.35;dc.lineWidth=2+random()*4;
    dc.beginPath();dc.moveTo(x,y);dc.quadraticCurveTo(x-6,y+6,x-3,y+8+random()*15);dc.stroke();
  }dc.restore();dc.globalAlpha=1;dc.globalCompositeOperation='destination-out';dc.beginPath();dc.arc(309,225,128,0,TAU);dc.fill();mc.drawImage(disc,0,0);
  const moonMap=new THREE.CanvasTexture(moonCanvas);moonMap.colorSpace=THREE.SRGBColorSpace;
  const moonUV=[.450,.312];
  const moon=new THREE.Sprite(new THREE.SpriteMaterial({map:moonMap,transparent:true,depthWrite:false,fog:false,opacity:1}));moon.name='Painted crescent moon';moon.position.copy(sphere(...moonUV,505));moon.scale.set(181,181,1);moon.renderOrder=-14;root.add(moon);
  return {root,particleLayers:[stars],paintCanvas:paint,moonCanvas,moonUV,version:'impasto-sky-v6-theme',resolution:[W,H],
    staticPanorama(){
      const c=canvas(W,H),x=c.getContext('2d');x.filter='saturate(92.5%) brightness(92%)';x.drawImage(paint,0,0);x.filter='none';
      function stamp(image,u,v,size,distance){const ph=size/distance/Math.PI*H,pw=ph/Math.max(.2,Math.sin(v*Math.PI));for(const shift of [-W,0,W])x.drawImage(image,u*W+shift-pw/2,v*H-ph/2,pw,ph);}
      for(let i=0;i<special.length;i++){
        if(i===4||i===6||i===8)continue;
        const [u,v,s]=special[i];x.globalAlpha=.95;stamp(haloMaps[i%4].image,u,v,75*s,510);
      }
      x.globalAlpha=1;stamp(moonCanvas,...moonUV,181,505);return c;
    },
    update(time){halos.forEach((s,i)=>{s.material.rotation=(i%2?1:-1)*time*.009+i*.7;});},
    setTime(time){clock.value=time;this.update(time);},
    get time(){return clock.value;}
  };
};
