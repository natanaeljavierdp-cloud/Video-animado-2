// node scripts/preview.mjs outdir t1 t2 ...  → PNGs de instantes concretos
import { createRequire } from 'module';
const { chromium } = createRequire(import.meta.url)('playwright');
import path from 'path'; import fs from 'fs';
const [out, ...ts] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
p.on('console', m => console.log('console:', m.text())); p.on('pageerror', e => console.log('ERR', e.message));
await p.goto('file://' + path.resolve('render/index.html'));
await p.evaluate(() => window.READY);
for (const t of ts) { await p.evaluate(t => window.renderFrame(t), +t); await p.screenshot({ path: `${out}/t${(+t).toFixed(2)}.jpg`, type: 'jpeg', quality: 85 }); }
await b.close();
