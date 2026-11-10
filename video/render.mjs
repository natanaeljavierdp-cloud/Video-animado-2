// Renderiza la secuencia fotograma a fotograma con Chromium (Playwright) y la codifica a MP4 con ffmpeg.
//   node render.mjs                -> output/sandoval-legal-motion.mp4 (1920x1080, 30 fps)
//   node render.mjs --fps 60       -> a 60 fps
//   node render.mjs --stills       -> solo fotogramas clave en output/stills/
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { startServer } from './serve.mjs';

// Playwright: instalación local (npm i -D playwright) o global.
const { chromium } = await import('playwright').catch(() => createRequire(import.meta.url)('playwright'));

const args = process.argv.slice(2);
const FPS = args.includes('--fps') ? Number(args[args.indexOf('--fps') + 1]) : 30;
const STILLS = args.includes('--stills');
const OUT = new URL('./output/', import.meta.url).pathname;
await mkdir(OUT + 'stills', { recursive: true });

const server = await startServer(4801);
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto('http://localhost:4801/index.html?capture');
await page.waitForFunction(() => window.READY === true, null, { timeout: 60000 });
const DURATION = await page.evaluate(() => window.DURATION);

if (STILLS) {
  for (const t of [0.8, 1.8, 2.4, 3.1, 3.6, 4.6, 5.6, 6.5, 7.4, 8.5, 9.6, 10.6, 11.2, 12.0, 12.6, 13.4, 14.4]) {
    await page.evaluate((t) => window.renderAt(t), t);
    await page.screenshot({ path: `${OUT}stills/t${t.toFixed(1).padStart(4, '0')}.jpg`, quality: 85, type: 'jpeg' });
    console.log('still', t);
  }
} else {
  const total = Math.round(DURATION * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    `${OUT}sandoval-legal-motion.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = 0; f < total; f++) {
    await page.evaluate((t) => window.renderAt(t), f / FPS);
    const png = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 30 === 0) console.log(`fotograma ${f}/${total}  (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('Listo:', `${OUT}sandoval-legal-motion.mp4`);
}
await browser.close();
server.close();
