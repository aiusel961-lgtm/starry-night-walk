/* Compare the current game with source-video frames. --sky-only exports the
   static panorama for the editable Blender project, without rebuilding models. */
const fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const deps='C:/Users/Thinkbook16p/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/';
const {chromium}=require(deps+'playwright'),sharp=require(deps+'sharp');
const root=path.resolve(__dirname,'..'),out=path.join(root,'场景对照分析'),skyOnly=process.argv.includes('--sky-only');
const shots=[
  {id:'lane',time:.5,name:'石墙下坡路',note:'近景石墙、路面与阴影决定第一眼的质感'},
  {id:'church',time:4,name:'教堂与村庄',note:'比较建筑轮廓、树冠形态和冷暖光照'},
  {id:'overlook',time:16,name:'丝柏与全景',note:'比较丝柏剪影、村庄纵深和天空的整体构图'}
];
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const label=(w,h,lines)=>Buffer.from(`<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#101a29"/>${lines.map(({text,x=16,y=28,size=19,fill='#e9e8e0'})=>`<text x="${x}" y="${y}" font-family="Microsoft YaHei,Segoe UI,sans-serif" font-size="${size}" fill="${fill}">${escape(text)}</text>`).join('')}</svg>`);
(async()=>{
  fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=d3d11','--force_high_performance_gpu']});
  const manifest=JSON.parse(fs.readFileSync(path.join(root,'scene/scene-manifest.json'),'utf8'));
  const report={capturedAt:new Date().toISOString(),edition:4,revision:manifest.revision,wallFinish:manifest.wallFinish,reference:'a7e33feb6fab21da6a49aba23d5d15f1.mp4',viewport:[1280,720],scope:'Offline load, three static views plus wall-foot detail, spawn and road centerline clearance; no flight or performance test',errors:[],views:[]};
  try{
    const context=await browser.newContext({viewport:{width:1280,height:720},offline:true});
    await context.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
    const page=await context.newPage();
    page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error')report.errors.push(m.text());});
    await page.goto(pathToFileURL(path.join(root,'index.html')).href);
    await page.waitForFunction(()=>window.nightWalk&&!document.getElementById('startButton').disabled,null,{polling:100,timeout:90000});
    if(skyOnly){
      const png=await page.evaluate(()=>nightWalk.skySystem.staticPanorama().toDataURL('image/png').split(',')[1]);
      fs.writeFileSync(path.join(root,'scene/textures/night-sky.png'),Buffer.from(png,'base64'));
      if(report.errors.length)throw Error(report.errors.join('\n'));
      console.log(JSON.stringify({status:'complete',output:'scene/textures/night-sky.png'}));return;
    }
    report.scene=await page.evaluate(()=>({stats:nightWalk.sceneStats,sky:nightWalk.skySystem.version}));
    report.corridors=await page.evaluate(({routes,colliders})=>{
      let samples=0;const blocked=[];
      routes.forEach((points,route)=>{
        for(let i=0;i<points.length-1;i++)for(let j=0;j<32;j++){
          const a=points[Math.max(0,i-1)],b=points[i],c=points[i+1],d=points[Math.min(points.length-1,i+2)],t=j/32;
          const [x,z]=[0,1].map(k=>.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t));
          if(Math.abs(x)>184||Math.abs(z)>184)continue;
          const y=nightWalk.heightAt(x,z)+nightWalk.config.EYE_HEIGHT;samples++;
          for(const f of colliders){
            const dx=x-f.x,dz=z-f.z;
            if(y+.25>f.yMin&&y-.25<f.yMax&&Math.abs(dx*f.cos-dz*f.sin)<f.hx+.25&&Math.abs(dx*f.sin+dz*f.cos)<f.hz+.25){
              if(!blocked.some(p=>p.route===route&&p.kind===f.kind&&Math.hypot(p.x-x,p.z-z)<3))blocked.push({route,x,z,kind:f.kind});
            }
          }
        }
      });return {scope:'Static road centerline samples inside the existing flight bounds',samples,blocked};
    },{routes:[...manifest.streets,...manifest.districts.map(d=>d.road)],colliders:manifest.colliders});
    if(report.corridors.blocked.length)report.errors.push(`Road centerline obstructions: ${JSON.stringify(report.corridors.blocked)}`);
    await page.addStyleTag({content:'#entry,.topbar,.bottombar,#loading,#crosshair{display:none!important}'});
    for(const shot of shots){
      const view=await page.evaluate(id=>{
        nightWalk.goToView(id);nightWalk.skySystem.setTime(3);nightWalk.renderFrame();nightWalk.renderFrame();
        return {id,position:nightWalk.camera.position.toArray(),rotation:nightWalk.camera.rotation.toArray(),fov:nightWalk.camera.fov};
      },shot.id);
      await page.screenshot({path:path.join(out,`current-${shot.id}.png`)});
      view.blockedBy=manifest.colliders.filter(c=>{
        const [x,y,z]=view.position,dx=x-c.x,dz=z-c.z;
        return y+.25>c.yMin&&y-.25<c.yMax&&Math.abs(dx*c.cos-dz*c.sin)<c.hx+.25&&Math.abs(dx*c.sin+dz*c.cos)<c.hz+.25;
      }).map(c=>c.kind);
      report.views.push(view);
      if(view.blockedBy.length)report.errors.push(`${shot.id} camera intersects ${view.blockedBy.join(', ')}`);
    }
    report.wallDetail=await page.evaluate(()=>{
      const n=nightWalk;n.camera.position.set(12.4,n.heightAt(12.4,82)+.95,82);
      n.camera.lookAt(14.2,n.heightAt(14.2,79.3)+.18,79.3);n.camera.fov=66;n.camera.updateProjectionMatrix();
      n.renderFrame();n.renderFrame();return {position:n.camera.position.toArray(),rotation:n.camera.rotation.toArray(),fov:n.camera.fov};
    });
    await page.screenshot({path:path.join(out,'石墙苔藓近景.png')});
    report.layout={districts:manifest.districts,templates:[...new Set([...manifest.houses,...manifest.distantHouses].map(h=>h.template))],windowCounts:manifest.windowCounts};
    // Decode the requested timestamps from the original MP4 directly.
    const source=await context.newPage();
    await source.goto(pathToFileURL(path.join(root,report.reference)).href);
    report.video=await source.evaluate(async()=>{
      const v=document.querySelector('video');v.pause();
      if(v.readyState<2)await new Promise(r=>v.addEventListener('loadeddata',r,{once:true}));
      return {duration:v.duration,width:v.videoWidth,height:v.videoHeight};
    });
    for(const shot of shots){
      await source.evaluate(async time=>{
        const v=document.querySelector('video');v.pause();
        await new Promise(r=>{v.addEventListener('seeked',r,{once:true});v.currentTime=time;});
        v.controls=false;v.style.cssText='position:fixed;left:0;top:0;width:1280px;height:720px;object-fit:fill;';
        document.body.style.margin='0';
      },shot.time);
      await source.locator('video').screenshot({path:path.join(out,`reference-${shot.id}.png`)});
    }
    const layers=[{input:label(1320,96,[{text:'参考视频 × 当前场景',x:20,y:35,size:27},{text:'左：原视频截图　右：当前游戏截图　｜　统一为 16:9；相近场景位置，机位并非逐帧匹配。',x:20,y:71,size:17,fill:'#a5b5c9'}]),left:0,top:0}];
    for(let i=0;i<shots.length;i++){
      const shot=shots[i],top=96+i*425;
      layers.push({input:label(1320,44,[{text:`${String(i+1).padStart(2,'0')}  ${shot.name}  ·  原视频 ${shot.time.toFixed(1)} 秒`,x:20,y:29,size:20},{text:'当前第四版',x:678,y:29,size:20}]),left:0,top});
      for(const [column,kind]of ['reference','current'].entries()){
        const input=await sharp(path.join(out,`${kind}-${shot.id}.png`)).resize(640,360).png().toBuffer();
        layers.push({input,left:column?670:10,top:top+44});
      }
      layers.push({input:label(1320,21,[{text:shot.note,x:20,y:16,size:13,fill:'#9caec5'}]),left:0,top:top+404});
    }
    await sharp({create:{width:1320,height:1371,channels:3,background:'#101a29'}}).composite(layers).png().toFile(path.join(out,'关键镜头对照.png'));
    const detailRows=[
      {id:'church',title:'01 住宅轮廓 · 长屋、两层住宅与低附房',reference:{left:380,top:205,width:700,height:265},current:{left:0,top:320,width:570,height:230},note:'观察屋脊方向、体块高低与入口；完整的 12 个住宅组合另见住宅样板组。'},
      {id:'overlook',title:'02 村落组织 · 道路、暗院与果园间隔',reference:{left:470,top:240,width:730,height:300},current:{left:410,top:295,width:520,height:170},note:'远景由 189 栋减至 102 栋，沿五段道路分布；亮窗约三分之一。'},
      {id:'lane',title:'03 入口石墙 · 沉稳灰褐石材与墙脚苔藓',reference:{left:0,top:170,width:340,height:380},current:{left:955,top:260,width:315,height:380},note:'压低亮部、保留背光层次；墙脚湿色、斑驳苔藓与低矮苔团连接石材和泥土。'}
    ];
    const detailLayers=[{input:label(1320,88,[{text:'房屋与石墙 · 原视频 / 当前第四版',x:20,y:34,size:26},{text:'局部放大，机位不同；用于比较轮廓、组织与色调。',x:20,y:69,size:17,fill:'#a5b5c9'}]),left:0,top:0}];
    for(const [i,row]of detailRows.entries()){
      const top=88+i*350;
      detailLayers.push({input:label(1320,42,[{text:row.title,x:20,y:29,size:21}]),left:0,top});
      for(const [col,kind]of ['reference','current'].entries()){
        const input=await sharp(path.join(out,`${kind}-${row.id}.png`)).extract(row[kind]).resize(640,265,{fit:'contain',background:'#101a29'}).png().toBuffer();
        detailLayers.push({input,left:col?670:10,top:top+42});
      }
      detailLayers.push({input:label(1320,43,[{text:row.note,x:20,y:28,size:16,fill:'#b3bdc9'}]),left:0,top:top+307});
    }
    await sharp({create:{width:1320,height:1138,channels:3,background:'#101a29'}}).composite(detailLayers).png().toFile(path.join(out,'房屋与石墙细节对照.png'));
    const wallLayers=[{input:label(1320,80,[{text:'石墙与苔藓 · 本次修订',x:20,y:32,size:26},{text:'原片用于判断色调和墙根质感；修订前后使用相同石巷机位。',x:20,y:64,size:17,fill:'#a5b5c9'}]),left:0,top:0}];
    for(const [i,[file,title]]of [['石墙修订前.png','修订前 · 墙面偏白'],['current-lane.png','修订后 · 灰褐石材与斑驳墙脚'],['reference-lane.png','原视频 · 0.5 秒'],['石墙苔藓近景.png','修订后近景 · 苔藓、湿土与低矮苔团']].entries()){
      const left=i%2?670:10,top=80+Math.floor(i/2)*408;
      wallLayers.push({input:label(640,38,[{text:title,x:12,y:27,size:20}]),left,top});
      wallLayers.push({input:await sharp(path.join(out,file)).resize(640,360).png().toBuffer(),left,top:top+38});
    }
    await sharp({create:{width:1320,height:896,channels:3,background:'#101a29'}}).composite(wallLayers).png().toFile(path.join(out,'石墙与苔藓修订对照.png'));
    fs.writeFileSync(path.join(out,'capture.json'),JSON.stringify(report,null,2));
    fs.writeFileSync(path.join(out,'第四版基础检查.json'),JSON.stringify(report,null,2));
    if(report.errors.length)throw Error(report.errors.join('\n'));
    console.log(JSON.stringify({status:'complete',...report,output:out}));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
