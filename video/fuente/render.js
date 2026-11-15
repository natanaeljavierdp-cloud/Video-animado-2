// usage: node render.js <html> <outdir> <fps> <worker> <nworkers> [times...]
const { chromium } = require('playwright');
const path = require('path'); const fs = require('fs');
(async () => {
  const [html, out, fps, wk, nw, ...times] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on('pageerror', e => console.error('PAGEERR', e.message));
  await p.goto('file://' + path.resolve(html));
  await p.evaluate(() => window.ready);
  let frames;
  if (times.length) frames = times.map(Number).map(t => ({ t, name: `t_${t}.jpg` }));
  else { const dur = await p.evaluate(() => window.DURATION); const n = Math.round(dur * fps); frames = [];
    for (let i = +wk; i < n; i += +nw) frames.push({ t: i / fps, name: `f_${String(i).padStart(5, '0')}.jpg` }); }
  for (const f of frames) {
    await p.evaluate(t => window.render(t), f.t);
    await p.screenshot({ path: path.join(out, f.name), type: 'jpeg', quality: 93 });
  }
  await b.close();
})();
