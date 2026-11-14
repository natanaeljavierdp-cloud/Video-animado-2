// node scripts/render.mjs outdir workers → segmentos mp4 sin audio (30 fps)
import { createRequire } from 'module'; import { spawn } from 'child_process';
import path from 'path'; import fs from 'fs';
const { chromium } = createRequire(import.meta.url)('playwright');
// argumento opcional `only`: re-renderizar solo un segmento
const [out, nw = 4, only] = process.argv.slice(2); fs.mkdirSync(out, { recursive: true });
const FPS = 30, DUR = 75.232653, N = Math.ceil(DUR * FPS);
const per = Math.ceil(N / nw);
const b = await chromium.launch();
await Promise.all([...Array(+nw)].map(async (_, w) => {
  if (only != null && w !== +only) return;
  const a = w * per, z = Math.min(N, a + per);
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file://' + path.resolve('render/index.html')); await p.evaluate(() => window.READY);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', `${out}/seg${w}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = a; f < z; f++) {
    await p.evaluate(t => window.renderFrame(t), f / FPS);
    const buf = await p.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - a) % 150 === 0) console.log(`w${w} ${f - a}/${z - a}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}));
await b.close();
fs.writeFileSync(`${out}/list.txt`, [...Array(+nw)].map((_, w) => `file 'seg${w}.mp4'`).join('\n'));
console.log('done');
