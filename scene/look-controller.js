/* Critically damped mouse look. Exact integration keeps the response independent
   of monitor refresh rate; target backlog is bounded to prevent delayed spins. */
(function (root) {
  const TAU=Math.PI*2;
  const wrap=a=>((a+Math.PI)%TAU+TAU)%TAU-Math.PI;
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  function createSmoothLook({sensitivity=.00095,response=20,maxSpeed=2.2,pitchLimit=Math.PI*.44}={}) {
    let yaw=0,pitch=0,targetYaw=0,targetPitch=0,vy=0,vp=0;
    return {
      reset(y=0,p=0){yaw=targetYaw=wrap(y);pitch=targetPitch=clamp(p,-pitchLimit,pitchLimit);vy=vp=0;},
      input(dx,dy,multiplier=1){
        if(!Number.isFinite(dx)||!Number.isFinite(dy))return;
        const gain=sensitivity*clamp(Number.isFinite(multiplier)?multiplier:1,.35,1.5);
        targetYaw=wrap(targetYaw-clamp(dx,-1500,1500)*gain);
        targetYaw=wrap(yaw+clamp(wrap(targetYaw-yaw),-.65,.65));
        targetPitch=clamp(targetPitch-clamp(dy,-1500,1500)*gain,-pitchLimit,pitchLimit);
        targetPitch=clamp(targetPitch,pitch-.65,pitch+.65);
      },
      step(dt){
        dt=Number.isFinite(dt)?clamp(dt,0,.1):0;if(!dt)return {yaw,pitch};
        const advance=(position,target,velocity,angular)=>{
          const delta=angular?wrap(target-position):target-position;
          const offset=-delta,c=(velocity+response*offset)*dt,decay=Math.exp(-response*dt);
          let move=delta+(offset+c)*decay,nextVelocity=(velocity-response*c)*decay;
          const limit=maxSpeed*dt;
          if(Math.abs(move)>limit){move=Math.sign(move)*limit;nextVelocity=move/dt;}
          return [angular?wrap(position+move):position+move,nextVelocity];
        };
        [yaw,vy]=advance(yaw,targetYaw,vy,true);
        [pitch,vp]=advance(pitch,targetPitch,vp,false);
        if(Math.abs(pitch)>pitchLimit){pitch=clamp(pitch,-pitchLimit,pitchLimit);vp=0;}
        return {yaw,pitch};
      },
      get state(){return {yaw,pitch,targetYaw,targetPitch,yawVelocity:vy,pitchVelocity:vp};}
    };
  }
  if(typeof module!=='undefined')module.exports={createSmoothLook};
  root.createSmoothLook=createSmoothLook;
})(globalThis);
