// Renderiza escenas.html cuadro a cuadro con Playwright y lo une con la narración usando ffmpeg.
// Uso: node render.mjs            -> out/cumbre-final.mp4
//      node render.mjs --preview  -> fotogramas de muestra en out/preview/
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { spawn } from 'node:child_process';
import { readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const dir = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30, DUR = 77.1;
const preview = process.argv.includes('--preview');
const segs = JSON.parse(readFileSync(path.join(dir, 'audio/transcripcion.json'), 'utf8'));
mkdirSync(path.join(dir, 'out/preview'), { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto(pathToFileURL(path.join(dir, 'escenas.html')).href);
await page.evaluate(s => window.setWords(s), segs);
await page.evaluate(() => document.fonts.ready);

if (preview) {
  const times = process.argv.slice(3).map(Number);
  const ts = times.length ? times : [1, 5, 9, 14.6, 17, 21, 28.5, 34.5, 39.5, 42, 49.5, 55, 58, 64, 67, 71, 74, 76];
  for (const t of ts) {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: path.join(dir, `out/preview/t${String(t).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 80 });
  }
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', path.join(dir, 'audio/narracion.mp3'),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart',
    path.join(dir, 'out/cumbre-final.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.ceil(DUR * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`cuadro ${i}/${n}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log('Listo: out/cumbre-final.mp4');
}
await browser.close();
