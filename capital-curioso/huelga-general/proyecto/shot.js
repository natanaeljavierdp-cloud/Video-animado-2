const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
p.on('console',m=>console.log('console:',m.text()));p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('file://'+__dirname+'/index.html');await p.waitForFunction('window.READY');
const out=process.env.OUT;require('fs').mkdirSync(out,{recursive:true});
for(const t of process.argv.slice(2)){await p.evaluate(`render(${t})`);await p.screenshot({path:`${out}/t${t}.jpg`,type:'jpeg',quality:80});}
await b.close();})();
