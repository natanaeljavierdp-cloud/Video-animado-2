const {chromium}=require('playwright');
(async()=>{const [a,b]=process.argv.slice(2).map(Number);const out=process.env.OUT;
const br=await chromium.launch();const p=await br.newPage({viewport:{width:1080,height:1920}});
p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('file://'+__dirname+'/index.html');await p.waitForFunction('window.READY');
const t0=Date.now();
for(let n=a;n<b;n++){await p.evaluate(`render(${n/30})`);await p.screenshot({path:`${out}/f${String(n).padStart(5,'0')}.jpg`,type:'jpeg',quality:93});
 if(n%200===0)console.log(n,((Date.now()-t0)/1000).toFixed(0)+'s');}
await br.close();console.log('done',a,b);})();
