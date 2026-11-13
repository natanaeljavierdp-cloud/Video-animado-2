// Renderiza un episodio: Chromium (Playwright) dibuja cada cuadro en un canvas,
// ffmpeg lo codifica. Uso:
//   node render.mjs <episodio.js> <timeline.json> <audio.wav> <salida.mp4> [--frames a,b,c] [--workers N]
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SERIE = path.resolve(HERE, '..', '..');
const [epJs, tlJson, wav, out] = process.argv.slice(2, 6);
const opt = (name) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : null; };
const stills = opt('--frames');
const workers = parseInt(opt('--workers') || '3', 10);

const TL = JSON.parse(fs.readFileSync(tlJson, 'utf8'));
const FPS = TL.fps;
const NF = Math.round(TL.total * FPS);
const motor = fs.readFileSync(path.join(HERE, 'motor.js'), 'utf8') + '\n' + fs.readFileSync(path.join(HERE, 'cine.js'), 'utf8');
const ep = fs.readFileSync(epJs, 'utf8');

async function openPage(browser) {
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.error('PAGE ERROR', e));
  page.on('console', (m) => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.setContent('<!doctype html><html><body style="margin:0;background:#000"><canvas id="c" width="1080" height="1920"></canvas></body></html>');
  await page.addScriptTag({ content: motor });
  await page.addScriptTag({ content: ep });
  const svgs = {};
  for (const f of fs.readdirSync(SERIE)) if (/^0\d-.*\.svg$/.test(f)) svgs[f] = fs.readFileSync(path.join(SERIE, f), 'utf8');
  await page.evaluate(async ({ TL, svgs }) => {
    window.TL = TL;
    await document.fonts.load('900 60px Inter');
    await document.fonts.load('800 60px Inter');
    for (const c of window.EP.CAST) c.ch = await window.M.loadCharacter(svgs[c.file]);
    window.EP.setup();
    const cv = document.getElementById('c');
    window.ctx = cv.getContext('2d');
    window.frame = (t) => { window.EP.render(window.ctx, t); return cv.toDataURL('image/jpeg', 0.93); };
  }, { TL, svgs });
  return page;
}

const browser = await chromium.launch();
if (stills) {
  const page = await openPage(browser);
  fs.mkdirSync(out, { recursive: true });
  for (const s of stills.split(',')) {
    const t = parseFloat(s);
    const d = await page.evaluate((t) => window.frame(t), t);
    fs.writeFileSync(path.join(out, `f_${t.toFixed(2)}.jpg`), Buffer.from(d.split(',')[1], 'base64'));
  }
  await browser.close();
  process.exit(0);
}

const tmp = out + '.partes';
fs.mkdirSync(tmp, { recursive: true });
const chunk = Math.ceil(NF / workers);
const t0 = Date.now();
await Promise.all([...Array(workers).keys()].map(async (w) => {
  const a = w * chunk, b = Math.min(NF, a + chunk);
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS), path.join(tmp, `p${w}.mp4`)],
  { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((r) => ff.on('close', r));
  for (let f = a; f < b; f++) {
    const d = await page.evaluate((t) => window.frame(t), f / FPS);
    const buf = Buffer.from(d.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (w === 0 && f % 150 === 0) console.log(`cuadro ${f}/${b} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await done;
}));
await browser.close();
const list = path.join(tmp, 'lista.txt');
fs.writeFileSync(list, [...Array(workers).keys()].map((w) => `file 'p${w}.mp4'`).join('\n'));
await new Promise((res, rej) => {
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-i', wav,
    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', out], { stdio: 'inherit' });
  ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg ' + c))));
});
fs.rmSync(tmp, { recursive: true, force: true });
console.log('LISTO', out, `${((Date.now() - t0) / 1000).toFixed(0)}s`);
