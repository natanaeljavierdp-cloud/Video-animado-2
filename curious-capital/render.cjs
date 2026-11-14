// Usage:
//   node render.js preview 1.5 10 22.9 ...   -> preview/frame_<t>.jpg
//   node render.js video [workers]           -> build/video_noaudio.mp4
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FPS = 30;
const DIR = __dirname;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => { if (m.type() === 'error') console.error('PAGE:', m.text()); });
  page.on('pageerror', e => console.error('PAGEERR:', e.message));
  await page.goto('file://' + path.join(DIR, 'render.html'));
  await page.evaluate(() => window.ready);
  return page;
}

async function preview(times) {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await openPage(browser);
  fs.mkdirSync(path.join(DIR, 'preview'), { recursive: true });
  for (const t of times) {
    await page.evaluate(t => window.render(t), parseFloat(t));
    await page.screenshot({ path: path.join(DIR, 'preview', `frame_${t}.jpg`), type: 'jpeg', quality: 85 });
  }
  await browser.close();
}

async function worker(browser, idx, f0, f1) {
  const page = await openPage(browser);
  const out = path.join(DIR, 'build', `seg_${idx}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => window.render(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 150 === 0) console.log(`w${idx}: ${f - f0}/${f1 - f0}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  return out;
}

async function video(nw) {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const probe = await openPage(browser);
  const dur = await probe.evaluate(() => window.DURATION);
  await probe.close();
  const total = Math.round(dur * FPS);
  fs.mkdirSync(path.join(DIR, 'build'), { recursive: true });
  const per = Math.ceil(total / nw);
  const jobs = [];
  for (let i = 0; i < nw; i++) jobs.push(worker(browser, i, i * per, Math.min(total, (i + 1) * per)));
  const segs = await Promise.all(jobs);
  await browser.close();
  const list = path.join(DIR, 'build', 'list.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  await new Promise(r => spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(DIR, 'build', 'video_noaudio.mp4')], { stdio: 'inherit' }).on('close', r));
  console.log('frames', total);
}

const [mode, ...rest] = process.argv.slice(2);
if (mode === 'preview') preview(rest).catch(e => { console.error(e); process.exit(1); });
else video(parseInt(rest[0] || '4')).catch(e => { console.error(e); process.exit(1); });
