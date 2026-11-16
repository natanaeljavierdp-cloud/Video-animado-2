// Renderiza video.html fotograma a fotograma con Playwright y lo envía a ffmpeg.
// Uso: node tools/render.js <out.mp4> [inicio] [fin]   |   node tools/render.js --stills t1,t2,... <dir>
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.png': 'image/png', '.ttf': 'font/ttf' };
const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0])); fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
(async () => {
  await new Promise(r => srv.listen(0, r)); const port = srv.address().port;
  const browser = await chromium.launch(); const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.text())); page.on('pageerror', e => { console.error('[pageerror]', e); process.exit(1); });
  await page.goto(`http://localhost:${port}/build/video.html`); await page.evaluate(() => window.ready);
  const grab = t => page.evaluate(t => { renderAt(t); return document.getElementById('c').toDataURL('image/jpeg', .93).split(',')[1]; }, t);
  const a = process.argv;
  if (a[2] === '--stills') {
    fs.mkdirSync(a[4], { recursive: true });
    for (const t of a[3].split(',').map(Number)) fs.writeFileSync(path.join(a[4], `f_${t.toFixed(2)}.jpg`), Buffer.from(await grab(t), 'base64'));
  } else if (a[2] === '--cues') {
    fs.writeFileSync(a[3], JSON.stringify(await page.evaluate(() => ({ cues: CUES, dur: DURATION }))));
  } else {
    const fps = 30, dur = await page.evaluate(() => DURATION); const t0 = +(a[3] || 0), t1 = +(a[4] || dur);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', a[2]], { stdio: ['pipe', 'inherit', 'inherit'] });
    const n0 = Math.round(t0 * fps), n1 = Math.round(t1 * fps); const st = Date.now();
    for (let n = n0; n < n1; n++) { const b = Buffer.from(await grab(n / fps), 'base64'); if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r)); if (n % 300 === 0) console.log(a[2], n, ((Date.now() - st) / 1000).toFixed(0) + 's'); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close(); srv.close();
})();
