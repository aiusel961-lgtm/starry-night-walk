/* Short offline review of the v5 composition pass. No flight or FPS benchmark. */
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const deps='C:/Users/Thinkbook16p/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/';
const {chromium}=require(deps+'playwright'),sharp=require(deps+'sharp');
const root=path.resolve(__dirname,'..'),out=path.join(root,'场景对照分析','第五版');
const shots=[['lane','石巷 · 降墙、抬高机位与暖灰石材'],['church','教堂 · 偏轴构图、两侧框景与入口暖光'],['overlook','俯瞰 · 靠近村庄与前中远景层级']];
const label=(w,h,lines)=>Buffer.from(`<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#14202b"/>${lines.map(([text,x,y,size=18])=>`<text x="${x}" y="${y}" font-family="Microsoft YaHei,Segoe UI,sans-serif" font-size="${size}" fill="#dfdfd1">${text}</text>`).join('')}</svg>`);
(async()=>{
  fs.mkdirSync(out,{recursive:true});
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'scene/scene-manifest.json'),'utf8'));
  const report={capturedAt:new Date().toISOString(),revision:manifest.revision,viewport:[1280,720],scope:'Offline load, three main views, moss detail, spawn clearance and roads around relocated framing; no flight or performance benchmark',errors:[],views:[],stats:manifest.stats};
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=d3d11','--force_high_performance_gpu']});
  try{
    const context=await browser.newContext({viewport:{width:1280,height:720},offline:true});
    await context.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
    const page=await context.newPage();
    page.on('pageerror',e=>report.errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});
    await page.goto(pathToFileURL(path.join(root,'index.html')).href);
    await page.waitForFunction(()=>window.nightWalk&&!document.getElementById('startButton').disabled,null,{timeout:90000,polling:100});
    await page.addStyleTag({content:'#entry,.topbar,.bottombar,#loading,#crosshair{display:none!important}'});
    report.sky=await page.evaluate(()=>nightWalk.skySystem.version);
    for(const [id]of shots){
      const view=await page.evaluate(id=>{
        const n=nightWalk;n.goToView(id);n.skySystem.setTime(3);n.renderFrame();n.renderFrame();
        return {id,position:n.camera.position.toArray(),rotation:n.camera.rotation.toArray(),fov:n.camera.fov,altitude:n.altitude};
      },id);
      await page.screenshot({path:path.join(out,`after-${id}.png`)});
      view.blockedBy=manifest.colliders.filter(c=>{
        const [x,y,z]=view.position,dx=x-c.x,dz=z-c.z;
        return y+.25>c.yMin&&y-.25<c.yMax&&Math.abs(dx*c.cos-dz*c.sin)<c.hx+.32&&Math.abs(dx*c.sin+dz*c.cos)<c.hz+.32;
      }).map(c=>c.kind);
      if(view.blockedBy.length)report.errors.push(`${id} camera intersects ${view.blockedBy.join(', ')}`);
      report.views.push(view);
    }
    report.corridors=await page.evaluate(({streets,colliders})=>{
      let samples=0;const blocked=[];
      function sample(x,z,route){
        const y=nightWalk.heightAt(x,z)+.90;samples++;
        for(const c of colliders){
          const dx=x-c.x,dz=z-c.z;
          if(y+.25>c.yMin&&y-.25<c.yMax&&Math.abs(dx*c.cos-dz*c.sin)<c.hx+.32&&Math.abs(dx*c.sin+dz*c.cos)<c.hz+.32){
            if(!blocked.some(p=>p.route===route&&p.kind===c.kind&&Math.hypot(p.x-x,p.z-z)<3))blocked.push({route,x,z,kind:c.kind});
          }
        }
      }
      for(const route of [0,1,2,6]){
        const points=streets[route];
        for(let i=0;i<points.length-1;i++)for(let j=0;j<32;j++){
          const a=points[Math.max(0,i-1)],b=points[i],c=points[i+1],d=points[Math.min(points.length-1,i+2)],t=j/32;
          const [x,z]=[0,1].map(k=>.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t));
          sample(x,z,route);
        }
      }
      for(let i=0;i<=40;i++){const t=i/40;sample(-.8+7.8*t,-8.3-10.8*t,'church-entry');}
      return {samples,blocked};
    },{streets:manifest.streets,colliders:manifest.colliders});
    if(report.corridors.blocked.length)report.errors.push('Blocked approach: '+JSON.stringify(report.corridors.blocked));
    report.ground=await page.evaluate(()=>{
      const n=nightWalk,root=n.scene.children.find(o=>o.name==='Blender / Starry Night valley');
      let samples=0,belowGround=0,minClearance=Infinity;
      for(const m of root.children){
        if(!['lanes','lane_brushes','fields','distant_roads','gardens','verges'].includes(m.userData.blenderGroup)||!['Blender / earth','Blender / path'].includes(m.material.name))continue;
        const a=m.geometry.attributes.position,indices=m.geometry.index;
        for(let i=0;i<indices.count;i+=3*11){
          let x=0,y=0,z=0;
          for(let j=0;j<3;j++){const k=indices.getX(i+j);x+=a.getX(k)/3;y+=a.getY(k)/3;z+=a.getZ(k)/3;}
          const clearance=y-n.heightAt(x,z);samples++;minClearance=Math.min(minClearance,clearance);if(clearance<-.001)belowGround++;
        }
      }
      return {samples,belowGround,minClearance};
    });
    if(report.ground.belowGround)report.errors.push('Ground paint intersects terrain');
    await page.evaluate(()=>{
      const n=nightWalk;n.camera.position.set(12.4,n.heightAt(12.4,82)+.95,82);
      n.camera.lookAt(14.2,n.heightAt(14.2,79.3)+.18,79.3);n.camera.fov=66;n.camera.updateProjectionMatrix();n.renderFrame();n.renderFrame();
    });
    await page.screenshot({path:path.join(out,'after-moss.png')});
    const layers=[{input:label(1320,88,[['第五版 · 机位与层级优化',20,34,26],['左：修改前　　右：修改后　｜　同画幅；机位和视角随构图调整',20,69,17]]),left:0,top:0}];
    for(let i=0;i<shots.length;i++){
      const [id,name]=shots[i],top=88+i*408;
      layers.push({input:label(1320,38,[[name,20,26,19]]),left:0,top});
      for(const [column,stage]of ['before','after'].entries()){
        layers.push({input:await sharp(path.join(out,`${stage}-${id}.png`)).resize(640,360).png().toBuffer(),left:column?670:10,top:top+38});
      }
    }
    await sharp({create:{width:1320,height:1312,channels:3,background:'#14202b'}}).composite(layers).png().toFile(path.join(out,'机位与层级优化对照.png'));
    const glb=fs.readFileSync(path.join(root,'scene/starry-village.glb'));
    if(glb.readUInt32LE(0)!==0x46546c67)throw Error('Invalid GLB header');
    const gltf=JSON.parse(glb.toString('utf8',20,20+glb.readUInt32LE(12)));
    const triangles=gltf.meshes.reduce((sum,m)=>sum+m.primitives.reduce((s,p)=>s+gltf.accessors[p.indices??p.attributes.POSITION].count/3,0),0);
    report.export={glbMeshes:gltf.meshes.length,glbTriangles:triangles,webMeshes:manifest.stats.meshes,webTriangles:manifest.stats.triangles,cameras:gltf.cameras?.map(c=>({name:c.name,yfov:c.perspective?.yfov}))};
    if(triangles!==manifest.stats.triangles||gltf.meshes.length!==manifest.stats.meshes)report.errors.push('GLB / web geometry count mismatch');
    report.triangleChange=manifest.stats.triangles-1480991;
    fs.writeFileSync(path.join(out,'基础检查.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
    if(report.errors.length)process.exitCode=1;
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
