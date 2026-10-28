/* Short offline visual check of the actual twelve model templates. */
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const deps='C:/Users/Thinkbook16p/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/';
const {chromium}=require(deps+'playwright'),sharp=require(deps+'sharp');
const root=path.resolve(__dirname,'..'),out=path.join(root,'场景对照分析');
const preview=path.join(root,'.samples-preview.html');
const wallOnly=process.argv.includes('--wall-only');
(async()=>{
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8').replace('src="scene/starry-village.js"','src="场景对照分析/住宅与石墙样板.js"');
  fs.writeFileSync(preview,html);
  const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--use-angle=d3d11','--force_high_performance_gpu']});
  try{
    const context=await browser.newContext({viewport:{width:800,height:600},offline:true});
    await context.addInitScript(()=>{window.requestAnimationFrame=()=>0;});
    const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await page.goto(pathToFileURL(preview).href);
    await page.waitForFunction(()=>window.nightWalk&&!document.getElementById('startButton').disabled,null,{timeout:90000,polling:100});
    await page.addStyleTag({content:'#entry,.topbar,.bottombar,#loading,#crosshair{display:none!important}'});
    const samples=JSON.parse(fs.readFileSync(path.join(out,'住宅样板索引.json'),'utf8')),layers=[];
    for(const s of wallOnly?[]:samples){
      const {x,z}=s.record;
      await page.evaluate(({x,z})=>{
        const n=nightWalk;n.camera.position.set(x+13,10,z+17);n.camera.lookAt(x,3.6,z);n.camera.fov=48;n.camera.updateProjectionMatrix();n.skySystem.setTime(3);n.renderFrame();n.renderFrame();
      },{x,z});
      const png=await page.screenshot();
      const thumb=await sharp(png).resize(400,300).png().toBuffer();
      const label=Buffer.from(`<svg width="400" height="36" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#152235"/><text x="14" y="25" fill="#ece7d7" font-size="19" font-family="Microsoft YaHei">${s.label}</text></svg>`);
      layers.push({input:thumb,left:(s.style%4)*400,top:Math.floor(s.style/4)*336});
      layers.push({input:label,left:(s.style%4)*400,top:Math.floor(s.style/4)*336+300});
    }
    if(!wallOnly)await sharp({create:{width:1600,height:1008,channels:3,background:'#152235'}}).composite(layers).png().toFile(path.join(out,'住宅样板组.png'));
    await page.evaluate(()=>{const n=nightWalk;n.camera.position.set(110,1.4,1);n.camera.lookAt(110,1.1,-5);n.camera.fov=75;n.camera.updateProjectionMatrix();n.renderFrame();n.renderFrame();});
    await page.screenshot({path:path.join(out,'入口石墙样板.png')});
    await page.evaluate(()=>{const n=nightWalk;n.camera.position.set(112,.66,-1.5);n.camera.lookAt(112.65,.22,-3.3);n.camera.fov=66;n.camera.updateProjectionMatrix();n.renderFrame();n.renderFrame();});
    await page.screenshot({path:path.join(out,'入口苔藓样板.png')});
    if(errors.length)throw Error(errors.join('\n'));
    console.log(JSON.stringify({samples:wallOnly?0:12,errors,output:wallOnly?'入口石墙样板.png / 入口苔藓样板.png':'住宅样板组.png / 入口石墙样板.png / 入口苔藓样板.png'}));
  }finally{await browser.close();fs.unlinkSync(preview);}
})().catch(e=>{console.error(e);process.exitCode=1;});
