// Deterministic frame renderer: window.render(t) sets every element for time t (seconds).
const $ = (id) => document.getElementById(id);
const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const P = (t, a, b) => cl((t - a) / (b - a));
const lerp = (a, b, x) => a + (b - a) * x;
const eo = (x) => 1 - Math.pow(1 - x, 3);
const eio = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const eb = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const hash = (n) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
function st(el, o) {
  if (typeof el === 'string') el = $(el);
  const tr = [];
  if (o.x !== undefined || o.y !== undefined) tr.push(`translate(${o.x || 0}px,${o.y || 0}px)`);
  if (o.r !== undefined) tr.push(`rotate(${o.r}deg)`);
  if (o.s !== undefined) tr.push(`scale(${o.s})`);
  el.style.transform = tr.join(' ');
  if (o.o !== undefined) { el.style.opacity = o.o; el.style.visibility = o.o <= 0.001 ? 'hidden' : 'visible'; }
  if (o.blur !== undefined) el.style.filter = o.blur > 0.05 ? `blur(${o.blur}px)` : 'none';
}
// pop-in helper: returns {o,s,y}
const pop = (t, a, d = 0.45, dy = 40) => { const k = P(t, a, a + d); return { o: cl(k * 2.5), s: lerp(0.85, 1, eb(k)), y: (1 - eo(k)) * dy }; };

const SC = { s1: [0, 5.75], s2: [5.75, 13.6], s3: [13.6, 30.55], s4: [30.55, 34.5], s5: [34.5, 46.45], s6: [46.45, 55.0], s7: [55.0, 58.4], s8: [58.4, 99] };
const CUTS = [5.75, 13.6, 30.55, 34.5, 46.45, 55.0, 58.4];
window.DURATION = 66;

// ---------- dust ----------
const dust = $('dust'); const DN = 46; const dots = [];
for (let i = 0; i < DN; i++) { const d = document.createElement('div'); const sz = 2 + hash(i) * 5; d.style.cssText = `position:absolute;width:${sz}px;height:${sz}px;border-radius:50%;background:#ecd08f;box-shadow:0 0 ${sz * 3}px #c9a45c`; dust.appendChild(d); dots.push(d); }

// ---------- subtitles ----------
const clean = (w) => w.replace(/[.,]/g, '').replace(/…/g, '');
const W = window.WORDS.map((w) => ({ ...w, d: clean(w.w) }));
const chunks = []; let cur = [];
W.forEach((w, i) => {
  cur.push(w);
  const chars = cur.reduce((a, b) => a + b.d.length + 1, 0);
  const nx = W[i + 1];
  const brk = !nx || /[,.?]$/.test(w.w) || chars >= 18 || cur.length >= 4 || (nx && nx.s - w.e > 0.3);
  if (brk) { chunks.push(cur); cur = []; }
});
chunks.forEach((c, i) => { c.start = c[0].s - 0.05; c.end = chunks[i + 1] ? Math.min(chunks[i + 1][0].s - 0.05, c[c.length - 1].e + 0.9) : c[c.length - 1].e + 0.6; });
const subs = $('subs'); let lastChunk = -1;
function renderSubs(t) {
  let ci = -1;
  for (let i = 0; i < chunks.length; i++) if (t >= chunks[i].start && t < chunks[i].end) ci = i;
  if (t > 58.4) ci = -1; // logo card speaks the lema
  if (ci !== lastChunk) { subs.innerHTML = ci < 0 ? '' : chunks[ci].map((w) => `<span>${w.d}</span>`).join(''); lastChunk = ci; }
  if (ci < 0) return;
  const spans = subs.children;
  chunks[ci].forEach((w, j) => {
    const sp = spans[j]; const k = P(t, w.s - 0.06, w.s + 0.12);
    const active = t >= w.s - 0.04 && (t < w.e + 0.02 || (j === chunks[ci].length - 1));
    const isActive = t >= w.s - 0.04 && t < (chunks[ci][j + 1] ? chunks[ci][j + 1].s - 0.04 : 1e9);
    sp.className = isActive ? 'on' : '';
    st(sp, { o: cl(k * 1.6), s: isActive ? lerp(0.7, 1.04, eb(k)) - (P(t, w.s + 0.12, w.s + 0.3)) * 0.04 : 1, y: (1 - eo(k)) * 26 });
  });
}

// ---------- scene envelope ----------
function sceneEnv(t, [a, b], id) {
  const inK = a === 0 ? 1 : P(t, a - 0.12, a + 0.38);
  const outK = b > 90 ? 1 : 1 - P(t, b - 0.18, b + 0.2);
  const v = Math.min(inK, outK);
  const el = $(id);
  const e = eo(inK);
  st(el, { o: v, s: lerp(1.08, 1, e) * lerp(0.97, 1, eo(outK)), blur: (1 - e) * 14 + (1 - outK) * 10 });
  return v > 0.001;
}
const kb = (el, t, a, b, s0 = 1.02, s1 = 1.14, x0 = 0, x1 = 0, y0 = 0, y1 = 0) => { const k = eio(P(t, a, b)); st(el, { s: lerp(s0, s1, k), x: lerp(x0, x1, k), y: lerp(y0, y1, k) }); };

function render(t) {
  // background drift
  $('bglines').style.transform = `translateY(${(t * 6) % 60}px)`;
  dots.forEach((d, i) => {
    const sp = 12 + hash(i + 7) * 30, x = hash(i + 3) * 1080 + Math.sin(t * 0.4 + i) * 30;
    const y = ((hash(i + 11) * 2100 - t * sp) % 2100 + 2100) % 2100 - 90;
    d.style.transform = `translate(${x}px,${y}px)`; d.style.opacity = (0.15 + 0.45 * (0.5 + 0.5 * Math.sin(t * 1.3 + i * 2))) * 0.8;
  });
  // flash streak on cuts
  let fl = 0, fx = -1200;
  CUTS.forEach((c) => { const k = P(t, c - 0.22, c + 0.4); if (k > 0 && k < 1) { fl = Math.sin(k * Math.PI); fx = lerp(-1100, 1100, eio(k)); } });
  st('flash', { o: fl, x: fx });

  // ===== S1 =====
  if (sceneEnv(t, SC.s1, 's1')) {
    kb($('s1img'), t, 0, 6, 1.0, 1.16, 0, -30, 0, 10);
    kb($('s1bg'), t, 0, 6, 1.05, 1.12);
    st('s1kick', { o: t < 0.05 ? 1 : P(t, 0.4, 1.0) });
    // glitch entry at 0.25 and again on "no es delito" (4.84)
    const g = (a) => P(t, a, a + 0.45) > 0 && P(t, a, a + 0.45) < 1 ? 1 - P(t, a, a + 0.45) : 0;
    const gi = Math.max(t < 0.05 ? 0 : g(0.05), g(4.84) * 0.9);
    const fr = Math.floor(t * 30);
    const enter = t < 0.05 ? 1 : P(t, 0.05, 0.5);
    const jx = gi > 0 ? (hash(fr) - 0.5) * 60 * gi : 0;
    const titles = document.querySelectorAll('.s1t');
    st(titles[0], { o: enter > 0 ? (gi > 0.3 && hash(fr + 5) > 0.7 ? 0.3 : 1) : 0, x: jx, s: lerp(1.25, 1, eo(enter)) + (t > 4.84 && t < 5.3 ? 0.06 * (1 - P(t, 4.84, 5.3)) : 0) });
    st(titles[1], { o: gi * 0.9, x: jx - 18 * gi - 8, y: (hash(fr + 1) - 0.5) * 20 * gi });
    st(titles[2], { o: gi * 0.9, x: jx + 18 * gi + 8, y: (hash(fr + 2) - 0.5) * 20 * gi });
    const sl = hash(fr + 9);
    titles[0].style.clipPath = gi > 0.25 ? `inset(${sl * 60}% 0 ${(1 - sl) * 30}% 0)` : 'none';
    if (gi > 0.25 && hash(fr + 3) > 0.5) titles[0].style.clipPath = 'none';
    st('s1title', { o: 1, y: Math.sin(t * 1.4) * 4 });
  }

  // ===== S2 =====
  if (sceneEnv(t, SC.s2, 's2')) {
    const c = P(t, 5.85, 6.5); st('lawcard', { o: cl(c * 2), y: (1 - eo(c)) * 120, s: lerp(0.92, 1, eb(c)) });
    const wipe = (id, a, d = 0.45) => { const k = eo(P(t, a, a + d)); const el = $(id); el.style.clipPath = `inset(0 ${(1 - k) * 100}% 0 0)`; st(el, { o: k > 0 ? 1 : 0, x: (1 - k) * -20 }); };
    wipe('l1', 6.35); wipe('l2', 6.85); wipe('l3', 7.5, 0.5);
    $('l3line').style.transform = `scaleX(${eo(P(t, 7.3, 7.8))})`;
    const cc = P(t, 9.1, 9.5); st('counter', { o: cc, y: (1 - eo(cc)) * 60 });
    const steps = [9.3, 9.55, 9.8, 10.05];
    let n = 1; steps.forEach((s, i) => { if (t >= s) n = i + 1; });
    $('cnumv').textContent = n;
    const lastStep = steps[n - 1];
    const bump = 1 - P(t, lastStep, lastStep + 0.25);
    st('cnum', { s: 1 + 0.12 * bump * (n === 4 ? 2 : 1) });
    $('cring').style.strokeDashoffset = 1131 * (1 - eio(P(t, 9.25, 10.15)));
    st('clabel', pop(t, 10.15, 0.5));
    st('cnote', pop(t, 11.95, 0.5, 20));
  }

  // ===== S3 =====
  if (sceneEnv(t, SC.s3, 's3')) {
    const items = [13.78, 17.22, 25.68];
    const imgs = ['s3i1', 's3i2', 's3i3'];
    imgs.forEach((id, i) => {
      const a = items[i], b = items[i + 1] || 31;
      const fin = i === 0 ? 1 : P(t, a - 0.1, a + 0.45);
      st(id, { o: t < a - 0.1 && i > 0 ? 0 : fin, s: lerp(1.03, 1.15, eio(P(t, a - 0.5, b))) * (1 + (1 - eo(fin)) * 0.08), y: lerp(10, -10, P(t, a, b)) });
    });
    let idx = 0; items.forEach((a, i) => { if (t >= a - 0.1) idx = i; });
    $('s3tag').textContent = `EXCEPCIÓN ${idx + 1} / 4`;
    ['r1', 'r2', 'r3'].forEach((id, i) => {
      const a = items[i]; const k = P(t, a - 0.05, a + 0.5);
      const active = idx === i;
      const el = $(id);
      st(el, { o: cl(k * 2) * (active ? 1 : 0.5), x: (1 - eo(k)) * 900, s: active ? 1 : 0.97 });
      el.style.borderColor = active ? 'rgba(236,208,143,1)' : 'rgba(201,164,92,.3)';
      el.style.background = active ? 'linear-gradient(90deg,rgba(201,164,92,.25),rgba(7,20,40,.85) 40%)' : 'rgba(7,20,40,.75)';
      el.style.boxShadow = active ? '0 0 40px rgba(201,164,92,.35)' : 'none';
    });
    const ch = [19.96, 21.02, 21.82, 22.86, 24.36];
    ch.forEach((a, i) => st('c' + (i + 1), pop(t, a - 0.05, 0.35, 20)));
    $('pubhl').style.transform = `scaleX(${eo(P(t, 29.05, 29.45))})`;
  }

  // ===== S4 =====
  if (sceneEnv(t, SC.s4, 's4')) {
    kb($('s4i'), t, 30.4, 34.6, 1.04, 1.16, 0, 0, 0, -20);
    const g = 30.86; const k = P(t, g - 0.12, g + 0.08);
    st('four', { o: k > 0 ? 1 : 0, s: lerp(3.2, 1, eio(k)) + (t > g + 0.08 ? 0.06 * Math.sin(P(t, g + 0.08, g + 0.5) * Math.PI) : 0) });
    // shake
    const sh = 1 - P(t, g + 0.06, g + 0.45);
    const fr = Math.floor(t * 30);
    if (t > g + 0.06 && sh > 0) $('s4').style.transform += ` translate(${(hash(fr) - 0.5) * 30 * sh}px,${(hash(fr + 4) - 0.5) * 30 * sh}px)`;
    const m = P(t, 32.3, 32.8); st('s4m', { o: cl(m * 2), x: (1 - eo(m)) * 700, r: lerp(8, -2, eo(m)) });
    kb($('s4mi'), t, 32.3, 34.6, 1.1, 1.2);
    st('s4txt', pop(t, 31.35, 0.5));
  }

  // ===== S5 =====
  if (sceneEnv(t, SC.s5, 's5')) {
    kb($('s5i'), t, 34.3, 46.6, 1.03, 1.2);
    const ph2 = eio(P(t, 37.5, 38.0));           // doc phase
    const ph3 = eio(P(t, 40.6, 41.1));           // querella phase
    st('s5p', { o: lerp(1, 0.35, Math.max(ph2, ph3)) });
    $('s5p').style.filter = `blur(${Math.max(ph2, ph3) * 6}px)`;
    // rótulo 1 stamp at 35.72
    const r = P(t, 35.6, 35.82);
    const rx = { o: r > 0 ? cl(r * 3) : 0, s: lerp(2.4, 1, eio(r)), r: -3 };
    // move to top during later phases
    const up = Math.max(ph2, ph3);
    st('rot1', { o: rx.o, s: rx.s * lerp(1, 0.68, up), r: -3 + up * 1, y: lerp(0, -700, up) });
    // paper
    const pin = P(t, 37.6, 38.1);
    st('paperw', { o: cl(pin * 2) * (1 - P(t, 40.5, 40.9)), y: (1 - eo(pin)) * 400 + P(t, 40.5, 40.9) * 200, r: lerp(6, -1.5, eo(pin)) });
    const sk = [P(t, 38.35, 38.65), P(t, 38.6, 38.9), P(t, 38.85, 39.15)];
    ['strike1', 'strike2', 'strike3'].forEach((id, i) => { $(id).style.width = (sk[i] * (i === 2 ? 420 : 700)) + 'px'; });
    const er = eio(P(t, 39.2, 39.7));
    $('offp').style.clipPath = `inset(0 0 0 ${er * 100}%)`;
    $('offp').style.opacity = 1 - er * 0.0;
    st('eraser', { x: lerp(-40, 760, er), o: er > 0 && er < 1 ? 1 : 0 });
    const sp = P(t, 39.6, 39.78); st('supr', { o: sp > 0 ? cl(sp * 3) : 0, s: lerp(2.2, 1, eio(sp)), r: -8 });
    st('judge', pop(t, 37.9, 0.4, 20));
    // rótulo 2
    const c2 = P(t, 40.9, 41.4); st('rot2', { o: cl(c2 * 2), y: (1 - eo(c2)) * 160, s: lerp(0.9, 1, eb(c2)) });
    st('r2a', pop(t, 41.85, 0.45, 20));
    st('r2eq', pop(t, 44.6, 0.35, 0));
    const q = pop(t, 45.0, 0.45, 20); q.s *= 1 + 0.08 * Math.sin(P(t, 45.85, 46.3) * Math.PI); st('r2b', q);
  }

  // ===== S6 =====
  if (sceneEnv(t, SC.s6, 's6')) {
    kb($('s6i1'), t, 46.3, 50.6, 1.04, 1.16, 0, -20);
    const sw = P(t, 50.2, 50.7);
    st('s6i2', { o: sw, s: lerp(1.12, 1.03, eio(P(t, 50.2, 55.2))) });
    const a = P(t, 47.75, 47.95); st('c212', { o: cl(P(t, 46.6, 47.1) * 2), y: (1 - eo(P(t, 46.6, 47.1))) * 120 });
    st('a212', { o: a > 0 ? cl(a * 3) : 0, s: lerp(2.0, 1, eio(a)) });
    st('t212', pop(t, 51.5, 0.5, 20));
    st('pe', pop(t, 49.4, 0.45));
    st('pm', pop(t, 50.8, 0.45));
  }

  // ===== S7 =====
  if (sceneEnv(t, SC.s7, 's7')) {
    const p = P(t, 55.05, 55.5); st('poll', { o: cl(p * 2), s: lerp(0.85, 1, eb(p)) });
    st('bsi', pop(t, 55.3, 0.35, 30)); st('bno', pop(t, 55.42, 0.35, 30));
    const tap = P(t, 56.25, 56.8);
    st('rip', { o: tap > 0 && tap < 1 ? 1 - tap : 0, s: lerp(0.2, 6, eo(tap)) });
    $('rip').style.left = '150px'; $('rip').style.top = '40px';
    $('bsi').style.boxShadow = t > 56.25 ? `0 12px 30px rgba(0,0,0,.5),0 0 0 ${6 * (1 - P(t, 56.25, 57))}px #fff, 0 0 60px rgba(236,208,143,.8)` : '0 12px 30px rgba(0,0,0,.5)';
    st('q1', pop(t, 55.6, 0.45, 30));
    const q2 = pop(t, 57.8, 0.4, 30); q2.s *= 1 + 0.05 * Math.sin(P(t, 58.0, 58.4) * Math.PI); st('q2', q2);
    st('q3', pop(t, 57.95, 0.4, 20));
  }

  // ===== S8 logo =====
  if (sceneEnv(t, SC.s8, 's8')) {
    const L0 = 58.45;
    $('rays').style.transform = `rotate(${t * 4}deg) scale(1.6)`;
    st('rays', { o: P(t, L0 + 0.8, L0 + 2) });
    const ringK = eio(P(t, L0, L0 + 1.2));
    $('lgring').style.strokeDashoffset = 2287 * (1 - ringK);
    $('lgring').setAttribute('transform', `rotate(${-90 - 360 * (1 - ringK) + (t - L0) * 6} 400 400)`);
    st('lgring2', { o: P(t, L0 + 0.9, L0 + 1.3) });
    const dk = P(t, L0 + 0.5, L0 + 1.1);
    $('lgdisc').style.transformOrigin = '400px 400px'; st('lgdisc', { o: dk, s: lerp(0.6, 1, eb(dk)) });
    $('lgbox').style.strokeDashoffset = 920 * (1 - eio(P(t, L0 + 0.8, L0 + 1.5)));
    const sK = P(t, L0 + 1.1, L0 + 1.6); $('lgS').style.transformOrigin = '400px 200px'; st('lgS', { o: sK, s: lerp(1.4, 1, eo(sK)) });
    const nK = eo(P(t, L0 + 1.3, L0 + 1.9)); $('lgName').style.clipPath = `inset(0 ${(1 - nK) * 50}% 0 ${(1 - nK) * 50}%)`; st('lgName', { o: nK > 0 ? 1 : 0 });
    st('lgLegal', { o: P(t, L0 + 1.6, L0 + 2.1) });
    const scK = P(t, L0 + 1.8, L0 + 2.3); st('lgScale', { o: scK }); $('lgScale').setAttribute('transform', `translate(400 ${545 + (1 - eo(scK)) * 30})`);
    // gold shine sweep
    const sh = P(t, L0 + 2.2, L0 + 3.1), sh2 = P(t, L0 + 5.8, L0 + 6.6);
    const sx = sh > 0 && sh < 1 ? lerp(-300, 1100, eio(sh)) : sh2 > 0 && sh2 < 1 ? lerp(-300, 1100, eio(sh2)) : -600;
    $('lgshine').setAttribute('x', sx);
    // flare on ring top-right
    const fk = P(t, L0 + 2.3, L0 + 3.3); const fv = Math.sin(fk * Math.PI);
    const ang = -0.9 + fk * 0.9; const fxp = 140 + 400 + 364 * Math.cos(ang) - 150, fyp = 483 + 400 + 364 * Math.sin(ang) - 150;
    st('flare', { o: fv, x: fxp, y: fyp, s: 0.6 + fv * 1.2 });
    const lg = P(t, L0, L0 + 1.4); st('logo', { s: lerp(0.8, 1, eo(lg)) * (1 + 0.015 * Math.sin((t - L0) * 1.2)), o: 1 });
    st('lema', pop(t, 59.75, 0.6, 30));
    st('ighandle', pop(t, 60.9, 0.5, 30));
  }

  // frame bits
  $('ticker').style.transform = `translateX(${-((t * 90) % ($('ticker').scrollWidth / 2))}px)`;
  $('ldot').style.opacity = 0.35 + 0.65 * (Math.sin(t * 6) > 0 ? 1 : 0);
  const lt = t < 13.6 ? 'LEY 74-25' : t < 46.45 ? 'ART. 211' : t < 55 ? 'ART. 212' : 'SANDOVAL LEGAL';
  if ($('livetxt').textContent !== lt) $('livetxt').textContent = lt;
  st('frame', { o: 1 });
  renderSubs(t);
  st('fadeblack', { o: P(t, 65.4, 66) });
}
window.render = render;
window.ready = document.fonts.ready.then(() => Promise.all([...document.images].map((im) => im.decode().catch(() => {})))).then(() => true);
