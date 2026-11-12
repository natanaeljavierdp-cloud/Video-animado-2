// Uso: node preview.mjs out_dir t1 t2 ...  → PNG por instante
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
const [out, ...ts] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const p = await b.newPage({ viewport: { width: 540, height: 960 } });
p.on('console', m => console.log('console:', m.text())); p.on('pageerror', e => console.log('ERR', e.message));
await p.goto('file://' + path.resolve('index.html')); await p.evaluate(() => window.READY);
for (const t of ts) {
  const d = await p.evaluate(t => { render(+t); return document.getElementById('c').toDataURL('image/jpeg', .85); }, t);
  fs.writeFileSync(`${out}/t${(+t).toFixed(2).padStart(6, '0')}.jpg`, Buffer.from(d.split(',')[1], 'base64'));
}
await b.close();
})();
