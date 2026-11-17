const {chromium}=require('playwright');const {spawn}=require('child_process');const path=require('path');
const [,,mode,a,b,out]=process.argv; // mode: frames list "test" or "seg"
(async()=>{
 const br=await chromium.launch({args:['--allow-file-access-from-files','--disable-web-security']});
 const pg=await br.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
 pg.on('console',m=>console.log('PAGE',m.text()));pg.on('pageerror',e=>console.log('ERR',e.message));
 await pg.goto('file://'+path.resolve(__dirname,'index.html'));await pg.evaluate(()=>window.ready);
 const el=await pg.$('canvas');
 if(mode==='test'){for(const s of a.split(',')){const f=Math.round(parseFloat(s)*30);await pg.evaluate(f=>render(f),f);await el.screenshot({path:`${b}/t_${s.padStart(5,"0")}.png`})}}
 else{const ff=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate','30','-c:v','png','-i','-','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-r','30',out],{stdio:['pipe','inherit','inherit']});
  for(let f=+a;f<+b;f++){await pg.evaluate(f=>render(f),f);const buf=await el.screenshot({type:'png'});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));if(f%150==0)console.log(out,f)}
  ff.stdin.end();await new Promise(r=>ff.on('close',r))}
 await br.close()})();
