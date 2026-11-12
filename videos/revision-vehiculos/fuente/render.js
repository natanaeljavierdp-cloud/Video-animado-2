// usage: node render.js preview t1 t2 ...   |  node render.js frames start end outfile
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
(async()=>{
  const mode=process.argv[2];
  const browser=await chromium.launch({args:['--allow-file-access-from-files']});
  const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
  page.on('pageerror',e=>console.error('PAGEERR',e.message));
  page.on('console',m=>{if(m.type()==='error')console.error('CONSOLE',m.text())});
  await page.goto('file://'+path.join(__dirname,'index.html'));
  await page.evaluate(async()=>{
    for(const t of [1,8,27,45,55,61]) window.renderFrame(t);
    await window.READY;
    await Promise.all(['900 10px Playfair','700 10px Playfair','italic 400 10px Playfair','700 10px Cinzel','600 10px Cinzel','500 10px Mont','600 10px Mont','700 10px Mont','800 10px Mont'].map(f=>document.fonts.load(f)));
  });
  if(mode==='preview'){
    for(const a of process.argv.slice(3)){const t=+a;await page.evaluate(t=>window.renderFrame(t),t);
      await page.screenshot({path:path.join(__dirname,'..','w',`p_${a}.jpg`),type:'jpeg',quality:80});}
  } else {
    const start=+process.argv[3],end=+process.argv[4],out=process.argv[5];
    const ff=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate','30','-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','16','-pix_fmt','yuv420p',out],{stdio:['pipe','inherit','inherit']});
    for(let f=start;f<end;f++){
      await page.evaluate(t=>window.renderFrame(t),f/30);
      const buf=await page.screenshot({type:'jpeg',quality:95});
      if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
      if(f%150===0) console.log(out,f);
    }
    ff.stdin.end(); await new Promise(r=>ff.on('close',r));
  }
  await browser.close();
})();
