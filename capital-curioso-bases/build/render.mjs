// Uso: node build/render.mjs preview 1.0 5.2 ...   |   node build/render.mjs video
import { createRequire } from 'module';
import http from 'http'; import fs from 'fs'; import path from 'path'; import { spawn } from 'child_process';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.json': 'application/json' };
const server = http.createServer((q, r) => {
  const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]));
  fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); } else { r.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); r.end(d); } });
}).listen(0);
const port = server.address().port;
const T = JSON.parse(fs.readFileSync(path.join(ROOT, 'build/timeline.json')));
const WORDS = JSON.parse(fs.readFileSync(path.join(ROOT, 'build/words.json')));
const FPS = 30;
const browser = await chromium.launch({ args: ['--disable-web-security'] });
async function newPage() {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.text())); page.on('pageerror', e => console.log('[err]', e.message));
  await page.goto(`http://localhost:${port}/build/index.html`);
  const missing = await page.evaluate(([t, w]) => window.init(t, w), [T, WORDS]);
  return { page, missing };
}
async function grab(page, t, q = 0.94) {
  const b64 = await page.evaluate(([t, q]) => { window.renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', q).split(',')[1]; }, [t, q]);
  return Buffer.from(b64, 'base64');
}
const mode = process.argv[2];
if (mode === 'preview') {
  const { page, missing } = await newPage();
  if (missing.length) console.log('Imágenes faltantes:', missing.join(', '));
  fs.mkdirSync(path.join(ROOT, 'build/preview'), { recursive: true });
  for (const ts of process.argv.slice(3)) {
    fs.writeFileSync(path.join(ROOT, `build/preview/f_${ts}.jpg`), await grab(page, parseFloat(ts), 0.85));
  }
} else {
  const N = Math.ceil(T.dur * FPS); const WORKERS = 4;
  const per = Math.ceil(N / WORKERS);
  fs.mkdirSync(path.join(ROOT, 'build/parts'), { recursive: true });
  let done = 0; const t0 = Date.now();
  await Promise.all([...Array(WORKERS).keys()].map(async k => {
    const { page, missing } = await newPage();
    if (k === 0 && missing.length) console.log('Imágenes faltantes (se usa respaldo):', missing.join(', '));
    const a = k * per, b = Math.min(N, a + per);
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), path.join(ROOT, `build/parts/p${k}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = a; i < b; i++) {
      const buf = await grab(page, i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (++done % 150 === 0) console.log(`${done}/${N} cuadros  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }));
  fs.writeFileSync(path.join(ROOT, 'build/parts/list.txt'), [...Array(WORKERS).keys()].map(k => `file 'p${k}.mp4'`).join('\n'));
  console.log('listo', N, 'cuadros');
}
await browser.close(); server.close();
