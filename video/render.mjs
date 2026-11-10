// Renderiza la animación con Chromium (Playwright) + ffmpeg.
//   node render.mjs stills <dir> t1 t2 ...   -> PNG de control
//   node render.mjs video <salida.mp4>        -> video mudo (4 procesos en paralelo)
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const words = JSON.parse(fs.readFileSync(path.join(HERE, 'words.json'), 'utf8'));
const [mode, out, ...rest] = process.argv.slice(2);

const browser = await chromium.launch();
async function newPage() {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => { console.error('ERROR en página:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(HERE, 'index.html'));
  await page.evaluate(() => window.READY);
  const info = await page.evaluate(w => window.init(w), words);
  return { page, info };
}

if (mode === 'stills') {
  fs.mkdirSync(out, { recursive: true });
  const { page, info } = await newPage();
  if (!rest.length) console.log(JSON.stringify(info, null, 1));
  for (const t of rest) {
    await page.evaluate(x => window.render(x), Number(t));
    await page.screenshot({ path: path.join(out, `f_${String(t).padStart(6, '0')}.png`) });
  }
} else if (mode === 'video') {
  const { page, info } = await newPage();
  await page.close();
  const total = Math.round(info.ANIM_END * FPS);
  console.log('fotogramas:', total, 'duración:', info.ANIM_END.toFixed(3));
  const N = 4, segs = [];
  const tmp = path.join(path.dirname(out), 'segs'); fs.mkdirSync(tmp, { recursive: true });
  await Promise.all(Array.from({ length: N }, async (_, k) => {
    const a = Math.floor(total * k / N), b = Math.floor(total * (k + 1) / N);
    const seg = path.resolve(tmp, `seg${k}.mp4`); segs[k] = seg;
    const { page } = await newPage();
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
    const done = new Promise(r => ff.on('close', r));
    for (let f = a; f < b; f++) {
      await page.evaluate(x => window.render(x), f / FPS);
      const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (k === 0 && f % 60 === 0) console.log(`  ${Math.round(100 * f / b)}%`);
    }
    ff.stdin.end(); await done;
  }));
  fs.writeFileSync(path.join(tmp, 'list.txt'), segs.map(s => `file '${s}'`).join('\n'));
  await new Promise(r => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'), '-c', 'copy', out], { stdio: 'inherit' }).on('close', r));
  console.log('listo:', out);
}
await browser.close();
