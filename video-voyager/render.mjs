// Servidor estático + Chromium sin pantalla: renderiza fotogramas [a,b) a un MP4 parcial o PNGs.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = path.dirname(new URL(import.meta.url).pathname);
const args = Object.fromEntries(process.argv.slice(2).map((a) => a.split('=')));
const FPS = 30, T = parseFloat(args.T || '93.65');
const types = { '.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json', '.woff2': 'font/woff2', '.woff': 'font/woff' };
const srv = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': types[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0);
const port = srv.address().port;
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
page.on('console', (m) => console.log('[page]', m.text()));
page.on('pageerror', (e) => console.log('[pageerror]', e.message));
await page.goto(`http://localhost:${port}/index.html?T=${T}`);
await page.waitForFunction('window.ready === true', null, { timeout: 120000 });
if (args.stills) {
  // stills=t1,t2,...  -> out/still_<t>.jpg
  fs.mkdirSync(path.join(ROOT, args.dir || 'out'), { recursive: true });
  for (const t of args.stills.split(',').map(Number)) {
    const t0 = Date.now();
    const d = await page.evaluate((t) => window.renderFrame(t, 0.9), t);
    fs.writeFileSync(path.join(ROOT, args.dir || 'out', `still_${t.toFixed(2)}.jpg`), Buffer.from(d.split(',')[1], 'base64'));
    console.log('still', t, Date.now() - t0, 'ms');
  }
} else {
  const a = parseInt(args.a || '0'), b = parseInt(args.b || String(Math.round(T * FPS)));
  const outf = args.out || 'out/part.mp4';
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), outf], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = a; f < b; f++) {
    const d = await page.evaluate((t) => window.renderFrame(t, 0.95), f / FPS);
    const buf = Buffer.from(d.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if ((f - a) % 30 === 0) console.log(`[${a}-${b}] frame ${f} ${((Date.now() - t0) / (f - a + 1)).toFixed(0)} ms/f`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
}
await browser.close(); srv.close();
