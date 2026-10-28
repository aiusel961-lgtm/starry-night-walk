// Layered pigment marks shared by the editable Blender scene and the game.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('C:/Users/Thinkbook16p/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const out = path.resolve(__dirname, '../scene/textures');
fs.mkdirSync(out, { recursive: true });
let seed = 1889;
const rand = () => { seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0; return seed / 4294967296; };
(async () => {
  const size=768;
  const palettes={
    plaster:['#c7c4b4','#e2d9bf','#b1b7b4','#959f9e','#e1dec9','#c5c2af'],
    slate:['#a5b3bb','#c5c9c2','#7d969f','#a7b7b7','#8c9ca8','#d6d1b8'],
    stone:['#b5b8b1','#e0dac1','#859b9f','#a3b2b1','#8d9997','#c7cbbd'],
    earth:['#b3ab91','#c5b48d','#8e978c','#b5b59a','#d0bc8d','#929d92'],
    path:['#c7beaa','#d8ccb0','#b4b7a6','#a6afa9','#bcb49c','#e3d9bd'],
    leaves:['#899f99','#d4d9b9','#839d9f','#b6cbbd','#72898a','#bfc8a5'],
    cypress:['#919d9b','#c1c3a2','#7a9698','#b3bfae','#698584','#d1ccad'],
    wood:['#aca993','#d4c7a2','#7f9391','#9faaa0','#bdbb9e','#c9c6ab'],
    mountain:['#a1b2be','#cfcebd','#829aaf','#b6c8cc','#859fae','#c1d0d0']
  };
  for (const [kind,colors] of Object.entries(palettes)) {
    let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="${size}" height="${size}" fill="${colors[0]}"/>`;
    const vertical=['cypress','wood'].includes(kind);
    for (let layer=0;layer<3;layer++)for (let i=0;i<(layer===0?550:2400);i++) {
      const x=rand()*size,y=rand()*size;
      let angle=vertical?-Math.PI/2+.35*Math.sin(x*.025+y*.009):kind==='path'?-.9+.85*Math.sin(x*.021+y*.014):kind==='mountain'?-.6+.3*Math.sin(y*.02):rand()*Math.PI;
      if(kind==='leaves')angle=-.5+.9*Math.sin(x*.03+y*.025)+rand()*.6;
      const len=(layer===0?38:kind==='earth'?5:kind==='path'?4:10)+rand()*(layer===0?140:kind==='cypress'?60:kind==='path'?17:24);
      const dx=Math.cos(angle)*len,dy=Math.sin(angle)*len,bend=(rand()-.5)*len*.5;
      const width=layer===0?16+rand()*45:1.6+rand()*(kind==='earth'?9:6);
      const color=colors[1+Math.floor(rand()*(colors.length-1))],alpha=layer===0?.10+rand()*.15:.13+rand()*.33;
      const nx=-Math.sin(angle),ny=Math.cos(angle);
      for(const ox of [-size,0,size])for(const oy of [-size,0,size]){
        const xx=x+ox,yy=y+oy;
        if(xx+Math.max(dx,0)<-width||xx+Math.min(dx,0)>size+width||yy+Math.max(dy,0)<-width||yy+Math.min(dy,0)>size+width)continue;
        svg+=`<path d="M${xx},${yy} q${dx*.5+nx*bend},${dy*.5+ny*bend} ${dx},${dy}" fill="none" stroke="${color}" stroke-width="${width}" stroke-linecap="round" opacity="${alpha}"/>`;
        if(layer===2&&rand()<.45){
          const off=width*.33;
          svg+=`<path d="M${xx+nx*off},${yy+ny*off} q${dx*.5+nx*bend},${dy*.5+ny*bend} ${dx*.84},${dy*.84}" fill="none" stroke="${colors[1]}" stroke-width=".7" opacity=".29"/>`;
        }
      }
    }
    if(kind==='slate')for(let row=0;row<14;row++)for(let col=-1;col<12;col++){
      const x=col*72+(row%2)*36,y=row*57,j=(rand()-.5)*6;
      svg+=`<path d="M${x+3},${y+48}q26,${j+4} 64,${j}" fill="none" stroke="#637e8e" stroke-width="2.4" opacity=".42"/><path d="M${x+7},${y+44}q21,${j+4} 48,${j}" fill="none" stroke="#e3ddc4" stroke-width="1.4" opacity=".36"/>`;
    }
    svg += '</svg>';
    await sharp(Buffer.from(svg)).png().toFile(path.join(out, `${kind}.png`));
  }
  // Limestone has broad weathered areas, sparse directional paint and shallow
  // relief. The relief is scalar data; its color space is set by both loaders.
  let stone=`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="#d6d1c3"/>`;
  let relief=`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="#808080"/>`;
  function tiled(mark,x,y,pad=150){
    let s='';for(const ox of [-size,0,size])for(const oy of [-size,0,size]){
      if(x+ox < -pad || x+ox>size+pad || y+oy < -pad || y+oy>size+pad)continue;
      s+=`<g transform="translate(${x+ox} ${y+oy})">${mark}</g>`;
    }return s;
  }
  for(let i=0;i<135;i++){
    const x=rand()*size,y=rand()*size,rx=25+rand()*102,ry=14+rand()*46;
    const shape=`M${-rx},0 Q${-rx*.6},${-ry*1.3} 0,${-ry} Q${rx*.9},${-ry*.8} ${rx},0 Q${rx*.5},${ry*1.2} 0,${ry} Q${-rx*.8},${ry*.7} ${-rx},0Z`;
    stone+=tiled(`<path d="${shape}" fill="${['#f3eee1','#b4b1a3','#c4b7a1','#a8afa6','#e5e0d2'][i%5]}" opacity="${.06+rand()*.13}"/>`,x,y);
    relief+=tiled(`<path d="${shape}" fill="${i%2?'#999999':'#6b6b6b'}" opacity=".12"/>`,x,y);
  }
  for(let i=0;i<580;i++){
    const x=rand()*size,y=rand()*size,len=8+rand()*62,dy=2+Math.sin(y*.011)*len*.18,width=1.5+rand()*5.5;
    const curve=`M0,0 Q${len*.45},${dy-3} ${len},${dy}`;
    stone+=tiled(`<path d="${curve}" fill="none" stroke="${i%3?'#f0ebdd':'#aaa99c'}" stroke-width="${width}" stroke-linecap="round" opacity="${.08+rand()*.16}"/>`,x,y);
    relief+=tiled(`<path d="${curve}" fill="none" stroke="${i%2?'#a0a0a0':'#676767'}" stroke-width="${width*.65}" stroke-linecap="round" opacity=".15"/>`,x,y);
  }
  for(let i=0;i<270;i++){
    const x=rand()*size,y=rand()*size,r=.6+rand()*1.1;
    stone+=tiled(`<ellipse rx="${r*1.7}" ry="${r}" fill="#8f9289" opacity=".12"/>`,x,y,4);
    relief+=tiled(`<ellipse rx="${r*1.7}" ry="${r}" fill="#626262" opacity=".12"/>`,x,y,4);
  }
  await sharp(Buffer.from(stone+'</svg>')).blur(.7).png().toFile(path.join(out,'wallstone.png'));
  await sharp(Buffer.from(relief+'</svg>')).blur(.9).png().toFile(path.join(out,'wallstone-relief.png'));
  // glTF stores tangent normals, not a scalar bump image. Bake the same shallow
  // relief once so Blender, GLB viewers and the offline game agree.
  const heights=await sharp(path.join(out,'wallstone-relief.png')).greyscale().raw().toBuffer(),normal=Buffer.alloc(size*size*3);
  const sample=(x,y)=>heights[((y+size)%size)*size+(x+size)%size]/255;
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const nx=-(sample(x+1,y)-sample(x-1,y))*11,ny=(sample(x,y+1)-sample(x,y-1))*11;
    const length=Math.hypot(nx,ny,1),i=(y*size+x)*3;
    normal[i]=Math.round((nx/length*.5+.5)*255);normal[i+1]=Math.round((ny/length*.5+.5)*255);normal[i+2]=Math.round((1/length*.5+.5)*255);
  }
  await sharp(normal,{raw:{width:size,height:size,channels:3}}).png().toFile(path.join(out,'wallstone-normal.png'));
  async function saveSurface(kind,pigment,heightSvg,gain){
    await sharp(Buffer.from(pigment+'</svg>')).blur(.55).png().toFile(path.join(out,kind+'.png'));
    const gray=await sharp(Buffer.from(heightSvg+'</svg>')).blur(1.1).greyscale().raw().toBuffer();
    const normals=Buffer.alloc(size*size*3),h=(x,y)=>gray[((y+size)%size)*size+(x+size)%size]/255;
    for(let y=0;y<size;y++)for(let x=0;x<size;x++){
      const nx=-(h(x+1,y)-h(x-1,y))*gain,ny=(h(x,y+1)-h(x,y-1))*gain,l=Math.hypot(nx,ny,1),i=(y*size+x)*3;
      normals[i]=Math.round((nx/l*.5+.5)*255);normals[i+1]=Math.round((ny/l*.5+.5)*255);normals[i+2]=Math.round((1/l*.5+.5)*255);
    }
    await sharp(normals,{raw:{width:size,height:size,channels:3}}).png().toFile(path.join(out,kind+'-normal.png'));
  }
  const begin=fill=>`<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}"><rect width="100%" height="100%" fill="${fill}"/>`;
  let rock=begin('#b9b4a7'),rockHeight=begin('#808080');
  rockHeight+='<defs><radialGradient id="hollow"><stop stop-color="#626262"/><stop offset="1" stop-color="#808080"/></radialGradient><radialGradient id="grain"><stop stop-color="#a3a3a3"/><stop offset="1" stop-color="#808080"/></radialGradient></defs>';
  // Larger, restrained mineral stains replace the pale parallel scratches.
  for(let i=0;i<180;i++){
    const x=rand()*size,y=rand()*size,rx=24+rand()*95,ry=14+rand()*58;
    const shape=`M${-rx},0 Q${-rx*.85},${-ry} ${-rx*.2},${-ry*.92} Q${rx*.72},${-ry*1.1} ${rx},${-ry*.15} L${rx*.73},${ry*.56} Q${rx*.2},${ry} ${-rx*.56},${ry*.68} Z`;
    rock+=tiled(`<path d="${shape}" fill="${['#8c8f81','#a59b87','#d1c8b5','#97998b','#c5bdab'][i%5]}" opacity="${.07+rand()*.17}"/>`,x,y);
    rockHeight+=tiled(`<ellipse rx="${rx}" ry="${ry}" fill="url(#${i%3?'grain':'hollow'})" opacity=".20"/>`,x,y);
  }
  for(let i=0;i<430;i++){
    const x=rand()*size,y=rand()*size,len=5+rand()*37,dy=Math.sin(y*.015+x*.009)*len*.25;
    const curve=`M0,0 q${len*.4},${dy-2} ${len},${dy}`,w=1.5+rand()*5;
    rock+=tiled(`<path d="${curve}" fill="none" stroke="${i%3?'#cbc2af':'#85897b'}" stroke-width="${w}" stroke-linecap="round" opacity="${.05+rand()*.09}"/>`,x,y);
    rockHeight+=tiled(`<path d="${curve}" fill="none" stroke="${i%2?'#959595':'#6d6d6d'}" stroke-width="${w}" stroke-linecap="round" opacity=".12"/>`,x,y);
  }
  for(let i=0;i<850;i++){
    const x=rand()*size,y=rand()*size,r=.6+rand()*2.1;
    rock+=tiled(`<ellipse rx="${r*1.5}" ry="${r}" fill="${i%3?'#8b8b7c':'#d0c8b6'}" opacity=".11"/>`,x,y,6);
    rockHeight+=tiled(`<ellipse rx="${r*1.5}" ry="${r}" fill="url(#${i%3?'hollow':'grain'})" opacity=".22"/>`,x,y,6);
  }
  await saveSurface('drywall',rock,rockHeight,10);
  let moss=begin('#b9b6a5'),mossHeight=begin('#808080');
  mossHeight+='<defs><radialGradient id="tuft"><stop stop-color="#bcbcbc"/><stop offset=".55" stop-color="#969696"/><stop offset="1" stop-color="#777777"/></radialGradient></defs>';
  for(let i=0;i<220;i++){
    const x=rand()*size,y=rand()*size,rx=15+rand()*45,ry=12+rand()*30;
    moss+=tiled(`<ellipse rx="${rx}" ry="${ry}" fill="${['#8b927d','#d0c5a2','#abb196'][i%3]}" opacity="${.08+rand()*.20}"/>`,x,y);
  }
  for(let i=0;i<3400;i++){
    const x=rand()*size,y=rand()*size,r=1.4+rand()*5.8,ry=r*(.55+rand()*.65);
    moss+=tiled(`<ellipse rx="${r}" ry="${ry}" fill="${['#d0c9a4','#7c886c','#afb78d','#b7b98e'][i%4]}" opacity="${.12+rand()*.25}"/>`,x,y,12);
    mossHeight+=tiled(`<ellipse rx="${r}" ry="${ry}" fill="url(#tuft)" opacity=".32"/>`,x,y,12);
  }
  await saveSurface('moss',moss,mossHeight,8);
  console.log('General textures, limestone, weathered dry stone and moss surfaces generated.');
})().catch(e => { console.error(e); process.exitCode = 1; });
