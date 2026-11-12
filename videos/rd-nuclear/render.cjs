// Renderiza el video: node render.cjs [workers]
// Cada worker dibuja un tramo de fotogramas en Chromium y los envía a ffmpeg; luego se unen y se añade el audio.
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');
const FPS = 30, DUR = 67.0, TOTAL = Math.round(DUR * FPS);
const WORKERS = +(process.argv[2] || 4);
fs.mkdirSync('build', { recursive: true });

async function worker(browser, idx, f0, f1) {
  const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
  page.on('pageerror', e => console.error('ERR', e.message));
  await page.goto('file://' + path.resolve('index.html'));
  await page.evaluate(() => window.READY);
  const out = `build/seg${idx}.mp4`;
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-tune', 'film', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    const d = await page.evaluate(t => { render(t); return document.getElementById('c').toDataURL('image/jpeg', .95); }, f / FPS);
    const buf = Buffer.from(d.slice(d.indexOf(',') + 1), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 100 === 0) console.log(`w${idx}: ${f - f0}/${f1 - f0}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  return out;
}

(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const per = Math.ceil(TOTAL / WORKERS), jobs = [];
  for (let i = 0; i < WORKERS; i++) jobs.push(worker(browser, i, i * per, Math.min(TOTAL, (i + 1) * per)));
  const segs = await Promise.all(jobs);
  await browser.close();
  fs.writeFileSync('build/list.txt', segs.map(s => `file '${path.basename(s)}'`).join('\n'));
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'build/list.txt', '-i', 'build/mix.wav',
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', 'rd-nuclear.mp4'], { stdio: 'inherit' });
  console.log('listo: rd-nuclear.mp4');
})();
