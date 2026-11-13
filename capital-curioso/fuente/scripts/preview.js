const {chromium}=require('playwright');const path=require('path');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
p.on('console',m=>console.log('console',m.text()));p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('file://'+path.resolve('build/index.html'));await p.evaluate(()=>window.ready);
const ts=process.argv.slice(2).map(Number);
for(const t of ts){await p.evaluate(t=>render(t),t);await p.screenshot({path:`prev/f_${t.toFixed(2).padStart(5,'0')}.jpg`,type:'jpeg',quality:80});}
await b.close()})();
