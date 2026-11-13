const {chromium}=require('playwright');const path=require('path');const {spawn}=require('child_process');
const FPS=30,DUR=66.0,TOTAL=Math.round(FPS*DUR),W=+process.argv[2]||4;
async function worker(i,browser){
  const a=Math.floor(TOTAL*i/W),b=Math.floor(TOTAL*(i+1)/W);
  const p=await browser.newPage({viewport:{width:1080,height:1920}});
  p.on('pageerror',e=>console.log('ERR',e.message));
  await p.goto('file://'+path.resolve('build/index.html'));await p.evaluate(()=>window.ready);
  const ff=spawn('ffmpeg',['-y','-v','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r',String(FPS),`build/seg${i}.mp4`],{stdio:['pipe','inherit','inherit']});
  for(let f=a;f<b;f++){
    await p.evaluate(t=>render(t),f/FPS);
    const buf=await p.screenshot({type:'jpeg',quality:94});
    if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));
    if((f-a)%150===0)console.log(`w${i} ${f-a}/${b-a}`);
  }
  ff.stdin.end();await new Promise(r=>ff.on('close',r));
}
(async()=>{const br=await chromium.launch();await Promise.all([...Array(W)].map((_,i)=>worker(i,br)));await br.close();console.log('done')})();
