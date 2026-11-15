const { chromium } = require('playwright');
const fs=require('fs');
(async()=>{
  const [,,mode,a,b,outdir]=process.argv;
  const br=await chromium.launch();
  const pg=await br.newPage({viewport:{width:1080,height:1920}});
  pg.on('console',m=>console.log('C:',m.text())); pg.on('pageerror',e=>console.log('ERR',e.message));
  await pg.goto('http://127.0.0.1:8765/index.html');
  await pg.waitForFunction(()=>window.READY,null,{timeout:60000});
  fs.mkdirSync(outdir,{recursive:true});
  if(mode==='snap'){ for(const t of a.split(',')){ const d=await pg.evaluate(t=>{renderFrame(+t);return document.getElementById('c').toDataURL('image/jpeg',.85)},t); fs.writeFileSync(`${outdir}/s_${t}.jpg`,Buffer.from(d.split(',')[1],'base64')); } }
  else { const fps=30; for(let f=+a;f<+b;f++){ const d=await pg.evaluate(t=>{renderFrame(t);return document.getElementById('c').toDataURL('image/jpeg',.93)},f/fps); fs.writeFileSync(`${outdir}/f_${String(f).padStart(5,'0')}.jpg`,Buffer.from(d.split(',')[1],'base64')); } }
  await br.close();
})();
