// Renderiza escena.html cuadro por cuadro (30 fps) a un MP4 sin audio.
// Uso:
//   node render.mjs                      -> salida/_video_sin_audio.mp4 + salida/sfx.json + salida/subtitulos.srt
//   node render.mjs --stills 2,10,20     -> salida/stills/t_XX.png (para revisar cuadros sueltos)
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node-tools/node_modules/playwright'); }

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, 'salida');
mkdirSync(out, { recursive: true });
const FPS = 30;

const args = process.argv.slice(2);
const stillsArg = args.includes('--stills') ? args[args.indexOf('--stills') + 1] : null;

const browser = await playwright.chromium.launch({ args: ['--allow-file-access-from-files'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
page.on('console', m => { if (m.type() === 'warning' || m.type() === 'error') console.log('[page]', m.text()); });
await page.goto(pathToFileURL(path.join(here, 'escena.html')).href + '?render');
await page.evaluate(() => window.ready);

const grab = (t, type) => page.evaluate(([t, type]) => {
  window.renderFrame(t);
  return document.getElementById('c').toDataURL(type, 0.95).split(',')[1];
}, [t, type]);

if (stillsArg) {
  mkdirSync(path.join(out, 'stills'), { recursive: true });
  for (const s of stillsArg.split(',').map(Number)) {
    writeFileSync(path.join(out, 'stills', `t_${String(s).padStart(5, '0')}.png`), Buffer.from(await grab(s, 'image/png'), 'base64'));
  }
  await browser.close();
  process.exit(0);
}

// datos para audio y subtítulos
const { sfx, subs, timing } = await page.evaluate(() => ({ sfx: window.SFX, subs: window.SUBS, timing: window.TIMING }));
const DURATION = timing.duration;
writeFileSync(path.join(out, 'timing.json'), JSON.stringify(timing, null, 1));
writeFileSync(path.join(out, 'sfx.json'), JSON.stringify(sfx, null, 1));
const ts = s => { const ms = Math.round(s * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
writeFileSync(path.join(out, 'subtitulos.srt'), subs.map((c, i) => `${i + 1}\n${ts(c.s)} --> ${ts(c.e)}\n${c.text}\n`).join('\n'));

const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS), path.join(out, '_video_sin_audio.mp4')],
  { stdio: ['pipe', 'inherit', 'inherit'] });
const total = Math.round(FPS * DURATION), t0 = Date.now();
for (let i = 0; i < total; i++) {
  const buf = Buffer.from(await grab(i / FPS, 'image/jpeg'), 'base64');
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 150 === 0) console.log(`cuadro ${i}/${total}  (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('listo:', path.join(out, '_video_sin_audio.mp4'));
