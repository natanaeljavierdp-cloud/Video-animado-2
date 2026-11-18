// Renderiza scene.html fotograma a fotograma (30 fps) con Chromium/Playwright.
// Uso: node render.mjs frames            -> build/frames/*.jpg (todo el video)
//      node render.mjs stills 1.5 7 20   -> build/still_<t>.png
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const ROOT = path.dirname(new URL(import.meta.url).pathname);
const FPS = 30, END = 58.5;
const MIME = { '.html': 'text/html', '.json': 'application/json', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const f = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0);
const URL_ = `http://127.0.0.1:${server.address().port}/scene.html`;

const [, , mode = 'frames', ...args] = process.argv;
const browser = await chromium.launch();
async function newPage() {
  const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
  page.on('pageerror', e => console.error('PAGE ERROR', e));
  await page.goto(URL_);
  await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
  return page;
}
const grab = (page, t, type) => page.evaluate(([t, type]) => {
  window.renderFrame(t);
  return document.getElementById('c').toDataURL(type, 0.93).split(',')[1];
}, [t, type]);

fs.mkdirSync(path.join(ROOT, 'build/frames'), { recursive: true });
if (mode === 'stills') {
  const page = await newPage();
  for (const a of args) fs.writeFileSync(path.join(ROOT, `build/still_${a}.png`), Buffer.from(await grab(page, +a, 'image/png'), 'base64'));
} else {
  const N = Math.round(END * FPS), WORKERS = 4;
  let next = 0, done = 0; const t0 = Date.now();
  await Promise.all(Array.from({ length: WORKERS }, async () => {
    const page = await newPage();
    while (next < N) {
      const i = next++;
      const b = await grab(page, i / FPS, 'image/jpeg');
      fs.writeFileSync(path.join(ROOT, `build/frames/f${String(i).padStart(5, '0')}.jpg`), Buffer.from(b, 'base64'));
      if (++done % 150 === 0) console.log(`${done}/${N}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
  }));
}
await browser.close(); server.close();
