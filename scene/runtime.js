/* Blender geometry loader. Uses classic scripts and embedded PNGs so file://
   launching still works offline, without a local server or CDN dependency. */
window.buildStarryVillage = async function (THREE, scene, renderer) {
  const payload = window.STARRY_VILLAGE;
  if (!payload || payload.metadata.version !== 1) throw new Error('场景文件缺失，请保留 index.html 旁的 scene 文件夹。');
  const meta = payload.metadata;
  const compressed = Uint8Array.from(atob(payload.binary), c => c.charCodeAt(0));
  const buffer = await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const types = { f: Float32Array, I: Uint32Array, B: Uint8Array };
  const array = record => new types[record.type](buffer, record.offset, record.length);
  const ground = meta.terrain, heights = array(ground.heights), step = ground.span / (ground.n - 1);
  const groundPixels=new Uint8Array(heights.length*4);
  for(let i=0;i<heights.length;i++){groundPixels[i*4]=Math.round((heights[i]+16)/96*255);groundPixels[i*4+3]=255;}
  const groundMap=new THREE.DataTexture(groundPixels,ground.n,ground.n,THREE.RGBAFormat);
  groundMap.minFilter=groundMap.magFilter=THREE.LinearFilter;groundMap.needsUpdate=true;
  const clock={value:0};
  const maps = {};
  await Promise.all(Object.entries(payload.textures).map(async ([name, data]) => {
    const image = new Image(); image.src = 'data:image/png;base64,' + data; await image.decode();
    const texture = new THREE.Texture(image);
    texture.colorSpace = name.endsWith('-normal') ? THREE.NoColorSpace : THREE.SRGBColorSpace;
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    texture.needsUpdate = true;
    maps[name] = texture;
  }));
  const materials = {};
  const lightSize=1536,lightSpan=ground.span;
  const lightCanvas = Object.assign(document.createElement('canvas'), { width:lightSize, height:lightSize });
  const lc = lightCanvas.getContext('2d'); lc.fillStyle = '#000'; lc.fillRect(0,0,lightSize,lightSize);
  for (const pool of meta.lightPools || []) {
    const x=(pool.x/lightSpan+.5)*lightSize, y=(.5-pool.z/lightSpan)*lightSize, r=pool.radius/lightSpan*lightSize;
    const glow=lc.createRadialGradient(x,y,0,x,y,r);
    const strength=pool.strength??.75;
    glow.addColorStop(0,`rgba(255,208,130,${.78*strength})`);glow.addColorStop(.22,`rgba(241,177,95,${.40*strength})`);glow.addColorStop(1,'rgba(194,140,78,0)');
    lc.globalCompositeOperation='screen';lc.fillStyle=glow;lc.fillRect(x-r,y-r,r*2,r*2);
  }
  const warmMap=new THREE.CanvasTexture(lightCanvas);warmMap.colorSpace=THREE.SRGBColorSpace;
  // Soft ground contact anchors the houses and tree roots to the hillside.
  const contactCanvas=Object.assign(document.createElement('canvas'),{width:1024,height:1024});
  const cc=contactCanvas.getContext('2d');cc.fillStyle='#fff';cc.fillRect(0,0,1024,1024);
  function contact(x,z,rx,rz,angle,strength){
    const scale=1024/ground.span;cc.save();cc.translate((x/ground.span+.5)*1024,(.5-z/ground.span)*1024);
    cc.rotate(angle);cc.scale(rx*scale,rz*scale);
    const g=cc.createRadialGradient(0,0,.2,0,0,1);g.addColorStop(0,`rgba(0,0,0,${strength})`);g.addColorStop(.55,`rgba(0,0,0,${strength*.7})`);g.addColorStop(1,'rgba(0,0,0,0)');
    cc.fillStyle=g;cc.fillRect(-1,-1,2,2);cc.restore();
  }
  for(const h of [...meta.houses,...(meta.distantHouses||[])]){
    for(const v of h.volumes||[h])contact(v.x,v.z,v.width*.60+.5,v.depth*.60+.5,h.yaw,.43);
  }
  for(const c of meta.colliders){
    if(['trunk','cypress','distant_house','market','fountain'].includes(c.kind))contact(c.x,c.z,c.hx+1.5,c.hz+1.5,Math.atan2(c.sin,c.cos),.4);
  }
  const contactMap=new THREE.CanvasTexture(contactCanvas);
  const painterlyNames=['plaster','roof','stone','wallstone','drywall','mortar','earth','path','mountain'];
  const windNames=['leaves','cypress','brush','cloth'];
  for (const [name, spec] of Object.entries(meta.materials)) {
    const m = new THREE.MeshStandardMaterial({
      color: '#ffffff', vertexColors: true, roughness: spec.roughness, metalness: 0,
      map: maps[spec.texture] || null,
      normalMap: maps[spec.normal] || null, normalScale: new THREE.Vector2(spec.normalScale??1,spec.normalScale??1),
      side: spec.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
      transparent: !!spec.transparent, depthWrite: !spec.transparent,
      emissive: spec.emission || '#000000', emissiveIntensity: spec.emissionStrength || 0,
    });
    m.name = 'Blender / ' + name;
    // A faint colored underpainting keeps the night shadows blue, not black.
    if (!spec.emission && name !== 'dark') {
      m.emissive.set(spec.underpaint || (name==='wallstone'?'#9da9b2':'#53749b'));
      m.emissiveIntensity = spec.underpaintStrength ?? (name==='wallstone'?.048:.025);
    }
    if (!spec.emission) {
      m.onBeforeCompile = shader => {
        shader.uniforms.uVillageWarm={value:warmMap};
        shader.uniforms.uVillageGround={value:groundMap};
        shader.uniforms.uVillageContact={value:contactMap};
        shader.uniforms.uVillageTime=clock;
        shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vVillageWorld;uniform float uVillageTime;')
          .replace('#include <beginnormal_vertex>', `#include <beginnormal_vertex>
            ${windNames.includes(name)?`float normalWind=sin(uVillageTime*1.55+position.y*.83+position.x*.31+position.z*.27);
            objectNormal.xz+=vec2(normalWind*.018,cos(uVillageTime*1.13+position.z*.57+position.y*.41)*.014);
            objectNormal=normalize(objectNormal);
            `:''}
          `)
          .replace('#include <begin_vertex>', `#include <begin_vertex>
            ${windNames.includes(name)?`float windMask=clamp((transformed.y+1.)/8.,0.,1.);
            float windWave=sin(uVillageTime*1.55+transformed.y*.83+transformed.x*.31+transformed.z*.27);
            float windWave2=cos(uVillageTime*1.13+transformed.z*.57+transformed.y*.41);
            transformed.x+=windWave*.045*windMask;
            transformed.z+=windWave2*.030*windMask;
            `:''}
          `)
          .replace('#include <project_vertex>', 'vVillageWorld=(modelMatrix*vec4(transformed,1.)).xyz;\n#include <project_vertex>');
        shader.fragmentShader = shader.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vVillageWorld;uniform sampler2D uVillageWarm,uVillageGround,uVillageContact;uniform float uVillageTime;')
          .replace('#include <color_fragment>', `#include <color_fragment>
            ${painterlyNames.includes(name)?`// Break up procedural surfaces with slow, irregular brush bundles.
            float brushA=sin(vVillageWorld.x*1.17+sin(vVillageWorld.z*.37+vVillageWorld.y*.08)*2.4);
            float brushB=sin(vVillageWorld.z*2.13-vVillageWorld.x*.41+sin(vVillageWorld.y*.52)*1.7);
            float brush=brushA*.62+brushB*.38;
            float brushEdge=smoothstep(.18,.92,abs(brush));
            diffuseColor.rgb*=1.+brush*.028;
            diffuseColor.rgb+=vec3(.012,.009,.004)*brushEdge;
            `:''}
            ${name==='water'?`float rings=sin(length(vVillageWorld.xz-vec2(-9.,-19.))*23.-uVillageTime*2.4);
            diffuseColor.rgb*=.88+.12*rings;
            `:''}
            float grazing=pow(1.-abs(normalize(vViewPosition).z),2.);
            diffuseColor.rgb+=vec3(.006,.010,.018)*grazing;
          `)
          .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
            vec2 warmUV=vVillageWorld.xz/${lightSpan.toFixed(1)}+.5;
            vec3 lamplight=texture2D(uVillageWarm,warmUV).rgb;
            vec2 groundUV=(vVillageWorld.xz/${ground.span.toFixed(1)}+.5)*${((ground.n-1)/ground.n).toFixed(8)}+${(.5/ground.n).toFixed(8)};
            float groundY=texture2D(uVillageGround,groundUV).r*96.-16.;
            float lampFlicker=.965+.035*sin(uVillageTime*3.1+vVillageWorld.x*.37+vVillageWorld.z*.23);
            totalEmissiveRadiance+=lamplight*diffuseColor.rgb*2.70*lampFlicker*exp(-max(0.,vVillageWorld.y-groundY-.85)*.48);
            ${['plaster','roof','stone'].includes(name)?`
              float villageFocus=exp(-pow(vVillageWorld.x/95.,2.)-pow((vVillageWorld.z+48.)/78.,2.));
              totalEmissiveRadiance+=diffuseColor.rgb*vec3(1.,.88,.69)*villageFocus*.085;
            `:''}
            ${['cypress','leaves','wood','brush'].includes(name)?'totalEmissiveRadiance+=diffuseColor.rgb*.12;':''}
          `)
          .replace('#include <aomap_fragment>',`#include <aomap_fragment>
            float grounding=mix(1.,texture2D(uVillageContact,warmUV).r,exp(-max(0.,vVillageWorld.y-groundY)*.9));
            reflectedLight.indirectDiffuse*=grounding;
            reflectedLight.directDiffuse*=mix(1.,grounding,.65);
          `);
        if(name==='water')shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
          float rings=sin(length(vVillageWorld.xz-vec2(-9.,-19.))*23.-uVillageTime*2.4);
          diffuseColor.rgb*=.88+.12*rings;
        `);
        if(name === 'earth') shader.vertexShader = shader.vertexShader.replace('#include <fog_vertex>', `#include <fog_vertex>
          #ifdef USE_FOG
            float outerMist = smoothstep(225., 325., length((modelMatrix * vec4(transformed, 1.)).xz));
            vFogDepth = mix(vFogDepth, 700., outerMist * .88);
          #endif
        `);
      };
      m.customProgramCacheKey = () => 'blender-painted-valley-v6-living-paint-'+name;
    }
    materials[name] = m;
  }
  const root = new THREE.Group(); root.name = 'Blender / Starry Night valley';
  const detail = [];
  for (const record of meta.meshes) {
    const g = new THREE.BufferGeometry();
    for (const name of ['position', 'normal', 'uv', 'color']) {
      g.setAttribute(name, new THREE.BufferAttribute(array(record[name]), record[name].components, name === 'color'));
    }
    g.setIndex(new THREE.BufferAttribute(array(record.index), 1));
    g.computeBoundingSphere(); g.computeBoundingBox();
    const mesh = new THREE.Mesh(g, materials[record.material]); mesh.name = record.name;
    mesh.userData.blenderGroup = record.group;
    mesh.castShadow = !['terrain','lanes','lane_brushes','ridges','leaf_marks','verges','fields','hero_brushes','meadow','flowers','distant_village','distant_groves','distant_roads','wall_growth'].includes(record.group) && !record.material.startsWith('window');
    mesh.receiveShadow = !record.material.startsWith('window') && record.group !== 'ridges';
    mesh.matrixAutoUpdate = false;
    root.add(mesh);
    if (['leaf_marks','verges','lane_brushes','meadow','flowers'].includes(record.group)) detail.push(mesh);
  }
  scene.add(root);
  function heightAt(x, z) {
    const u = Math.max(0, Math.min(ground.n - 1.00001, (x + ground.span / 2) / step));
    const v = Math.max(0, Math.min(ground.n - 1.00001, (z + ground.span / 2) / step));
    const ix = Math.floor(u), iz = Math.floor(v), fx = u - ix, fz = v - iz;
    const a = heights[iz * ground.n + ix], b = heights[(iz + 1) * ground.n + ix];
    const c = heights[(iz + 1) * ground.n + ix + 1], d = heights[iz * ground.n + ix + 1];
    // Blender tessellates these quads across a-c. Match its triangular surface.
    return fz >= fx ? a + (b - a) * fz + (c - b) * fx : a + (d - a) * fx + (c - d) * fz;
  }
  // Small, shallow architectural accents sharpen the church silhouette and
  // give its entrance a readable threshold in the low camera.
  const churchAccent=new THREE.Group();churchAccent.name='Church hand-painted stone accents';
  const churchGround=heightAt(8,-20.25);
  const addAccent=(material,size,position)=>{
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),material);
    mesh.position.set(...position);mesh.castShadow=true;mesh.receiveShadow=true;churchAccent.add(mesh);
  };
  const accentStone=materials.wallstone||materials.stone;
  const accentDark=materials.dark||materials.mortar;
  addAccent(accentStone,[.34,8.6,.28],[3.28,churchGround+4.55,-20.40]);
  addAccent(accentStone,[.34,8.6,.28],[12.72,churchGround+4.55,-20.40]);
  addAccent(accentStone,[9.75,.26,.30],[8,churchGround+8.15,-20.40]);
  addAccent(accentStone,[.24,3.45,.24],[5.92,churchGround+1.72,-19.78]);
  addAccent(accentStone,[.24,3.45,.24],[8.08,churchGround+1.72,-19.78]);
  addAccent(accentStone,[2.40,.28,.25],[7,churchGround+3.40,-19.78]);
  addAccent(accentDark,[1.52,2.68,.08],[7,churchGround+1.38,-19.63]);
  root.add(churchAccent);
  // Three low haze sheets create a quiet valley floor without washing out the
  // moonlit buildings. Their animated noise is deliberately very slow.
  const mistGeometry=new THREE.PlaneGeometry(380,380,1,1);mistGeometry.rotateX(-Math.PI/2);
  const mistLayers=[];
  for(const layer of [{y:1.15,alpha:.030,scale:38,speed:.10},{y:3.2,alpha:.018,scale:27,speed:.07},{y:6.8,alpha:.010,scale:19,speed:.045}]){
    const mat=new THREE.ShaderMaterial({uniforms:{uTime:clock,uAlpha:{value:layer.alpha},uScale:{value:layer.scale},uSpeed:{value:layer.speed}},transparent:true,depthWrite:false,depthTest:true,side:THREE.DoubleSide,fog:false,
      vertexShader:`varying vec3 vMistWorld;void main(){vec4 world=modelMatrix*vec4(position,1.);vMistWorld=world.xyz;gl_Position=projectionMatrix*viewMatrix*world;}`,
      fragmentShader:`varying vec3 vMistWorld;uniform float uTime,uAlpha,uScale,uSpeed;
        float hazeNoise(vec2 p){return .5+.5*sin(p.x*1.73+sin(p.y*.91)*2.2+sin((p.x+p.y)*.37));}
        void main(){vec2 p=vMistWorld.xz;float field=hazeNoise(p/uScale+vec2(uTime*uSpeed,-uTime*uSpeed*.65));
          float valley=1.-smoothstep(115.,220.,length(p-vec2(0.,-72.)));
          float ribbon=smoothstep(.34,.82,field)*smoothstep(.22,.58,1.-abs(sin(p.x*.012+p.y*.009)));
          float a=uAlpha*valley*ribbon; if(a<.002)discard;gl_FragColor=vec4(.12,.19,.30,a);
        }`});
    const mesh=new THREE.Mesh(mistGeometry,mat);mesh.position.y=layer.y;mesh.frustumCulled=false;mesh.renderOrder=-3;scene.add(mesh);mistLayers.push(mesh);
  }
  // A few real, shadowless light anchors give the painted lamp pools a soft
  // directional spill on nearby walls and the church approach.
  const warmAnchors=[];
  for(const pool of (meta.lightPools||[])
    .filter(p=>p.radius>=4.7&&Math.hypot(p.x,p.z)<80)
    .sort((a,b)=>Math.hypot(a.x,a.z)-Math.hypot(b.x,b.z)).slice(0,6)){
    const light=new THREE.PointLight('#ffd09a',16*(pool.strength??.8),Math.max(12,pool.radius*4.2),2);
    light.position.set(pool.x,heightAt(pool.x,pool.z)+2.6,pool.z);
    light.castShadow=false;
    scene.add(light);warmAnchors.push({light,base:light.intensity,phase:pool.x*.17+pool.z*.11});
  }
  // A restrained layer of low fireflies gives the dark foreground a sense of
  // scale. They stay sparse and soft so the painted sky remains dominant.
  let fireflySeed=7411;
  const fireflyRandom=()=>{fireflySeed=(fireflySeed*1664525+1013904223)>>>0;return fireflySeed/4294967296;};
  const fireflyCount=96,fireflyPositions=[],fireflySizes=[],fireflyPhases=[],fireflyColors=[];
  for(let i=0;i<fireflyCount;i++){
    const a=fireflyRandom()*Math.PI*2,r=22+Math.pow(fireflyRandom(),.72)*118;
    const x=Math.cos(a)*r-12,z=Math.sin(a)*r-64;
    const y=heightAt(x,z)+.55+fireflyRandom()*3.5;
    fireflyPositions.push(x,y,z);fireflySizes.push(1.5+fireflyRandom()*2.4);fireflyPhases.push(fireflyRandom()*Math.PI*2);
    fireflyColors.push(...new THREE.Color(fireflyRandom()<.78?'#f2c66f':'#b5d7bd').toArray());
  }
  const fireflyGeometry=new THREE.BufferGeometry();
  fireflyGeometry.setAttribute('position',new THREE.Float32BufferAttribute(fireflyPositions,3));
  fireflyGeometry.setAttribute('aSize',new THREE.Float32BufferAttribute(fireflySizes,1));
  fireflyGeometry.setAttribute('aPhase',new THREE.Float32BufferAttribute(fireflyPhases,1));
  fireflyGeometry.setAttribute('aColor',new THREE.Float32BufferAttribute(fireflyColors,3));
  const fireflyMaterial=new THREE.ShaderMaterial({uniforms:{uTime:clock},transparent:true,depthWrite:false,
    blending:THREE.AdditiveBlending,fog:false,
    vertexShader:`attribute float aSize,aPhase;attribute vec3 aColor;uniform float uTime;varying vec3 vColor;varying float vAlpha;
      void main(){vec3 p=position;float phase=uTime*.62+aPhase;p.x+=sin(phase)*.32;p.z+=cos(phase*.83)*.22;p.y+=sin(phase*1.27)*.16;
        vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(aSize*105./max(1.,-mv.z),1.,12.);vColor=aColor;vAlpha=.42+.58*(.5+.5*sin(phase*1.7));}`,
    fragmentShader:`varying vec3 vColor;varying float vAlpha;void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);float a=smoothstep(1.,0.,r);a*=.18+.82*exp(-r*4.8);if(a<.01)discard;gl_FragColor=vec4(vColor*1.7,a*vAlpha*.76);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const fireflies=new THREE.Points(fireflyGeometry,fireflyMaterial);
  fireflies.name='Low meadow fireflies';fireflies.frustumCulled=false;fireflies.renderOrder=-5;scene.add(fireflies);
  // Soft point halos make the practical lights read through the valley air
  // while depth testing keeps them behind walls when they are occluded.
  const lampPositions=[],lampSizes=[],lampPhases=[],lampStrengths=[];
  for(const pool of meta.lightPools||[]){
    lampPositions.push(pool.x,heightAt(pool.x,pool.z)+2.15,pool.z);
    lampSizes.push(pool.radius>=4.7?13:7.5);lampPhases.push(pool.x*.13+pool.z*.09);lampStrengths.push(pool.strength??.65);
  }
  const lampGeometry=new THREE.BufferGeometry();
  lampGeometry.setAttribute('position',new THREE.Float32BufferAttribute(lampPositions,3));
  lampGeometry.setAttribute('aSize',new THREE.Float32BufferAttribute(lampSizes,1));
  lampGeometry.setAttribute('aPhase',new THREE.Float32BufferAttribute(lampPhases,1));
  lampGeometry.setAttribute('aStrength',new THREE.Float32BufferAttribute(lampStrengths,1));
  const lampMaterial=new THREE.ShaderMaterial({uniforms:{uTime:clock},transparent:true,depthWrite:false,
    depthTest:true,blending:THREE.AdditiveBlending,fog:false,
    vertexShader:`attribute float aSize,aPhase,aStrength;uniform float uTime;varying float vAlpha;
      void main(){vec4 mv=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(aSize*72./max(1.,-mv.z),2.,42.);vAlpha=aStrength*(.90+.10*sin(uTime*3.1+aPhase));}`,
    fragmentShader:`varying float vAlpha;void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);float a=smoothstep(1.,0.,r);a*=.16+.84*exp(-r*3.2);if(a<.008)discard;gl_FragColor=vec4(1.0,.55,.18,a*vAlpha*.34);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const lampHalos=new THREE.Points(lampGeometry,lampMaterial);
  lampHalos.name='Lantern air halos';lampHalos.frustumCulled=false;lampHalos.renderOrder=-4;scene.add(lampHalos);
  // Sparse chimney smoke adds a quiet sign of life without competing with
  // the painted sky. Each plume is a small animated cloud of soft points.
  const smokePositions=[],smokeSizes=[],smokePhases=[],smokeRise=[];
  const smokeCandidates=meta.houses.filter(h=>h.height>4.1&&h.ground<12).sort((a,b)=>Math.hypot(a.x,a.z+40)-Math.hypot(b.x,b.z+40)).slice(0,18);
  let smokeSeed=9137;const smokeRandom=()=>{smokeSeed=(smokeSeed*1664525+1013904223)>>>0;return smokeSeed/4294967296;};
  for(const h of smokeCandidates){
    const roofRise=h.volumes?.[0]?.rise??h.height*.35;
    const roofY=h.ground+h.height+roofRise+.45;
    for(let i=0;i<7;i++){
      const t=smokeRandom();smokePositions.push(h.x+(smokeRandom()-.5)*.55,roofY+t*5.6,h.z+(smokeRandom()-.5)*.55);
      smokeSizes.push(3.5+smokeRandom()*5.0);smokePhases.push(smokeRandom());smokeRise.push(.65+smokeRandom()*.6);
    }
  }
  const smokeGeometry=new THREE.BufferGeometry();
  smokeGeometry.setAttribute('position',new THREE.Float32BufferAttribute(smokePositions,3));
  smokeGeometry.setAttribute('aSize',new THREE.Float32BufferAttribute(smokeSizes,1));
  smokeGeometry.setAttribute('aPhase',new THREE.Float32BufferAttribute(smokePhases,1));
  smokeGeometry.setAttribute('aRise',new THREE.Float32BufferAttribute(smokeRise,1));
  const smokeMaterial=new THREE.ShaderMaterial({uniforms:{uTime:clock},transparent:true,depthWrite:false,depthTest:true,
    blending:THREE.NormalBlending,fog:false,
    vertexShader:`attribute float aSize,aPhase,aRise;uniform float uTime;varying float vAlpha;
      void main(){float cycle=fract(uTime*.035+aPhase);vec3 p=position;p.y+=cycle*3.8*aRise;p.x+=sin(uTime*.24+aPhase*9.)*.24*cycle;p.z+=cos(uTime*.19+aPhase*7.)*.18*cycle;
        vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(aSize*56./max(1.,-mv.z),2.,24.);vAlpha=(1.-cycle)*(.08+.08*sin(aPhase*12.));}`,
    fragmentShader:`varying float vAlpha;void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);float a=smoothstep(1.,0.,r)*exp(-r*1.7);if(a<.006)discard;gl_FragColor=vec4(.33,.39,.45,a*vAlpha);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
    }`});
  const smoke=new THREE.Points(smokeGeometry,smokeMaterial);smoke.name='Quiet chimney smoke';smoke.frustumCulled=false;smoke.renderOrder=-2;scene.add(smoke);
  const paths = meta.streets.map(points => new THREE.CatmullRomCurve3(points.map(([x,z]) => new THREE.Vector3(x,0,z)), false, 'catmullrom', .5));
  const lodObjects = [{ update(camera) {
    for (const mesh of detail) mesh.visible = camera.position.distanceTo(mesh.geometry.boundingSphere.center) - mesh.geometry.boundingSphere.radius < 110;
  }}];
  // Data is no longer duplicated as a large Base64 string after decoding.
  delete window.STARRY_VILLAGE;
  return { root, heightAt, colliders: meta.colliders, houses: meta.houses, streets: paths,
    roadCurve: paths[0], views: meta.views, lodObjects, update(time){
      clock.value=time;
      for(const anchor of warmAnchors)anchor.light.intensity=anchor.base*(.965+.035*Math.sin(time*3.1+anchor.phase));
      for(const mesh of mistLayers)mesh.material.uniforms.uTime.value=time;
    }, stats: { ...meta.stats,
      triangles: meta.meshes.reduce((sum, m) => sum + m.index.length / 3, 0) } };
};
