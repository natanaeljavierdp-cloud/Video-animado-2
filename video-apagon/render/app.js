// Capital Curioso — "Apagón mundial 17 NOV" — motor de render cuadro a cuadro.
// window.renderFrame(t) dibuja el instante t (segundos). Todo es determinista.
'use strict';
const W = 1080, H = 1920;
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');
const DURATION = 75.232653;

// ---------- Marca ----------
const NAVY = '#0B1F3A', NAVY_D = '#06142A', NAVY_L = '#1D4E9E', RED = '#E0262F', RED_D = '#A8161D';
const WHITE = '#FFFFFF', GREEN = '#22B573', GRAY = '#8A93A3', AMBER = '#FFC94A';

// ---------- Utilidades ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const prog = (t, s, d) => clamp((t - s) / d);
const eOut = x => 1 - Math.pow(1 - x, 3);
const eIn = x => x * x * x;
const eIO = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const eBack = x => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
// visibilidad: entra en `a`, sale terminando en `b`
const vis = (t, a, b, fi = .35, fo = .35) => Math.min(eOut(prog(t, a, fi)), 1 - eIn(prog(t, b - fo, fo)));
const hash = n => { let x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// tiempos de palabras (de la transcripción real)
const WD = window.WORDS;
const ws = i => WD[i].s, we = i => WD[i].e;

// ---------- Recursos ----------
const IMG = {};
const imgNames = ['01_ciudad_oscura', '02_personas_celular_azul', '03_personas_celular_gris', '04_televisor_viejo', '05_televisor_fondo_azul',
  '06_vela_sola', '07_velas_mesa', '08_velas_candelabro', '09_torre_radio_roja', '10_torre_antena', '11_antena_onda_corta', '12_familia_television',
  '13_santo_domingo_noche', '14_bandera_dominicana', '15_torres_alta_tension', '16_tapon_diario', '17_tapon_santo_domingo', '18_agua_y_comida', '19_botiquin'];
const ICO = {};
function loadImg(src) { return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = src; }); }
async function iconImg(name, color, sw = 2) {
  const k = name + color + sw; if (ICO[k]) return ICO[k];
  const svg = window.ICONS[name].replace('stroke="currentColor"', `stroke="${color}"`).replace('stroke-width="2"', `stroke-width="${sw}"`)
    .replace('width="24"', 'width="256"').replace('height="24"', 'height="256"');
  ICO[k] = await loadImg('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg));
  return ICO[k];
}
const icon = (name, color, sw = 2) => ICO[name + color + sw];
function drawIcon(name, color, x, y, s, sw = 2, a = 1) {
  const im = icon(name, color, sw); if (!im) { console.warn('icon not loaded', name, color, sw); return; }
  ctx.save(); ctx.globalAlpha *= a; ctx.drawImage(im, x - s / 2, y - s / 2, s, s); ctx.restore();
}

// grano de película + textura de sello
const GRAIN = [];
function makeGrain() {
  for (let g = 0; g < 6; g++) {
    const c = document.createElement('canvas'); c.width = 540; c.height = 960;
    const x = c.getContext('2d'); const d = x.createImageData(540, 960);
    let s = g * 9973 + 1;
    for (let i = 0; i < d.data.length; i += 4) {
      s = (s * 16807) % 2147483647; const v = (s / 2147483647) * 255;
      d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255;
    }
    x.putImageData(d, 0, 0); GRAIN.push(c);
  }
}
let SPECK;
function makeSpeck() {
  SPECK = document.createElement('canvas'); SPECK.width = 1000; SPECK.height = 500;
  const x = SPECK.getContext('2d'); let s = 77;
  const r = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  for (let i = 0; i < 2600; i++) { x.fillStyle = `rgba(0,0,0,${0.25 + r() * 0.75})`; x.beginPath(); x.arc(r() * 1000, r() * 500, r() * r() * 7 + .5, 0, 7); x.fill(); }
  for (let i = 0; i < 40; i++) { x.strokeStyle = 'rgba(0,0,0,.5)'; x.lineWidth = r() * 3; x.beginPath(); const a = r() * 1000, b = r() * 500; x.moveTo(a, b); x.lineTo(a + r() * 120 - 60, b + r() * 30 - 15); x.stroke(); }
}
const STAMPC = document.createElement('canvas'); STAMPC.width = 1000; STAMPC.height = 500;

// ---------- Primitivas de dibujo ----------
function font(fam, size, weight = '') { return `${weight} ${size}px ${fam}`.trim(); }
function text(str, x, y, o = {}) {
  ctx.save();
  ctx.font = o.font || font('InterX', 40, 700);
  ctx.fillStyle = o.color || WHITE;
  ctx.textAlign = o.align || 'center';
  ctx.textBaseline = o.base || 'middle';
  ctx.letterSpacing = (o.ls || 0) + 'px';
  if (o.alpha != null) ctx.globalAlpha *= o.alpha;
  if (o.shadow !== false) { ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = o.blur ?? 18; ctx.shadowOffsetY = 4; }
  if (o.stroke) { ctx.lineWidth = o.stroke; ctx.strokeStyle = o.strokeColor || NAVY_D; ctx.lineJoin = 'round'; ctx.strokeText(str, x, y); }
  ctx.fillText(str, x, y);
  ctx.restore();
}
function measure(str, f, ls = 0) { ctx.save(); ctx.font = f; ctx.letterSpacing = ls + 'px'; const w = ctx.measureText(str).width; ctx.restore(); return w; }
function rrect(x, y, w, h, r, fill, stroke, lw = 4) {
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
}
function circle(x, y, r, fill, stroke, lw = 4) {
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
}
function withA(a, fn) { if (a <= 0.001) return; ctx.save(); ctx.globalAlpha *= a; fn(); ctx.restore(); }
function pop(x, y, k, fn) { ctx.save(); ctx.translate(x, y); ctx.scale(k, k); ctx.translate(-x, -y); fn(); ctx.restore(); }
function glow(color, blur) { ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.shadowOffsetY = 0; }

// panel "vidrio" azul marino
function panel(x, y, w, h, r = 28, a = .82) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 12;
  rrect(x, y, w, h, r, `rgba(9,26,52,${a})`);
  ctx.restore();
  ctx.save(); rrect(x, y, w, h, r, null, 'rgba(255,255,255,.14)', 2); ctx.restore();
}

// check animado (trazo)
function checkMark(x, y, s, k, color = WHITE, lw = 12) {
  if (k <= 0) return;
  const p = [[x - s * .42, y + s * .02], [x - s * .12, y + s * .32], [x + s * .45, y - s * .3]];
  const l1 = Math.hypot(p[1][0] - p[0][0], p[1][1] - p[0][1]), l2 = Math.hypot(p[2][0] - p[1][0], p[2][1] - p[1][1]);
  const d = (l1 + l2) * k;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(...p[0]);
  if (d <= l1) ctx.lineTo(p[0][0] + (p[1][0] - p[0][0]) * d / l1, p[0][1] + (p[1][1] - p[0][1]) * d / l1);
  else { ctx.lineTo(...p[1]); const r = (d - l1) / l2; ctx.lineTo(p[1][0] + (p[2][0] - p[1][0]) * r, p[1][1] + (p[2][1] - p[1][1]) * r); }
  ctx.stroke(); ctx.restore();
}
function greenCheckBadge(x, y, r, k) {
  if (k <= 0) return;
  const s = eBack(clamp(k * 1.6));
  pop(x, y, s, () => { ctx.save(); glow('rgba(34,181,115,.8)', 25); circle(x, y, r, GREEN); ctx.restore(); circle(x, y, r, null, WHITE, 5); });
  checkMark(x, y, r * 1.1, clamp((k - .25) / .6), WHITE, r * .26);
}

// sello de goma
function stamp(str, x, y, rot, k, color = RED, size = 120, sub = null) {
  if (k <= 0) return;
  const c = STAMPC.getContext('2d');
  c.clearRect(0, 0, 1000, 500);
  c.font = font('Anton', size); c.letterSpacing = '4px';
  const tw = c.measureText(str).width;
  const bw = Math.min(980, tw + 90), bh = size * 1.45 + (sub ? 60 : 0);
  const bx = 500 - bw / 2, by = 250 - bh / 2;
  c.strokeStyle = color; c.lineWidth = 12; c.beginPath(); c.roundRect(bx, by, bw, bh, 18); c.stroke();
  c.lineWidth = 4; c.beginPath(); c.roundRect(bx + 16, by + 16, bw - 32, bh - 32, 10); c.stroke();
  c.fillStyle = color; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillText(str, 500, 250 - (sub ? 26 : 0) + size * .04);
  if (sub) { c.font = font('Oswald', 40, 700); c.letterSpacing = '10px'; c.fillText(sub, 500, 250 + size * .5 + 4); }
  c.globalCompositeOperation = 'destination-out'; c.drawImage(SPECK, 0, 0); c.globalCompositeOperation = 'source-over';
  const s = k < 1 ? lerp(2.4, 1, eOut(k)) : 1;
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  ctx.globalAlpha *= clamp(k * 3);
  ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 30;
  ctx.drawImage(STAMPC, -500, -250);
  ctx.restore();
}

// ---------- Fondo: fotos con movimiento lento ----------
// [img, inicio, fin, zoom0, zoom1, focoX, focoY, panX(px), oscuridad]
const SHOTS = [
  ['01_ciudad_oscura', -1, 3.25, 1.06, 1.16, .5, .55, 30, .45],
  ['02_personas_celular_azul', 3.15, 9.05, 1.0, 1.10, .5, .5, -40, .55],
  ['05_televisor_fondo_azul', 9.0, 13.0, 1.12, 1.0, .5, .5, 0, .45],
  ['04_televisor_viejo', 12.95, 18.0, 1.0, 1.10, .5, .45, 0, -.25],
  ['06_vela_sola', 17.95, 23.5, 1.15, 1.02, .5, .6, 0, -.35],
  ['07_velas_mesa', 23.45, 28.65, 1.05, 1.15, .5, .5, 30, .3],
  ['09_torre_radio_roja', 28.6, 38.85, 1.0, 1.14, .5, .4, -20, .55],
  ['11_antena_onda_corta', 38.8, 41.15, 1.04, 1.12, .55, .5, -30, .5],
  ['12_familia_television', 41.1, 43.35, 1.0, 1.08, .55, .5, 0, .45],
  ['13_santo_domingo_noche', 43.3, 46.95, 1.0, 1.10, .5, .5, 0, .5],
  ['14_bandera_dominicana', 46.9, 51.05, 1.08, 1.0, .55, .5, 0, .45],
  ['15_torres_alta_tension', 51.0, 55.65, 1.0, 1.12, .6, .5, -30, .55],
  ['17_tapon_santo_domingo', 55.6, 58.65, 1.04, 1.14, .5, .55, 0, .5],
  ['18_agua_y_comida', 58.6, 65.25, 1.0, 1.10, .5, .5, 20, .55],
  ['19_botiquin', 65.2, 72.4, 1.06, 1.16, .42, .5, 0, .6],
  ['12_familia_television', 72.35, 74.3, 1.12, 1.18, .55, .5, 0, .72],
];
function drawShot(sh, t, alpha) {
  const [name, s, e, z0, z1, fx, fy, px, dark] = sh;
  const im = IMG[name]; if (!im) return;
  const k = eIO(clamp((t - s) / (e - s + .001)));
  const z = lerp(z0, z1, k);
  const sc = Math.max(W / im.width, H / im.height) * z;
  const dw = im.width * sc, dh = im.height * sc;
  let x = W / 2 - dw * fx + lerp(-px / 2, px / 2, k), y = H / 2 - dh * fy;
  x = clamp(x, W - dw, 0); y = clamp(y, H - dh, 0);
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.filter = `saturate(0.62) contrast(1.08) brightness(${1 - dark * .55})`;
  ctx.drawImage(im, x, y, dw, dh);
  ctx.restore();
}
function drawBackground(t) {
  ctx.fillStyle = NAVY_D; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < SHOTS.length; i++) {
    const sh = SHOTS[i]; const s = sh[1], e = sh[2];
    if (t < s || t > e) continue;
    const prev = SHOTS[i - 1];
    const fin = (prev && s < prev[2]) ? clamp((t - s) / (prev[2] - s)) : 1;
    drawShot(sh, t, i === 0 ? 1 : eIO(fin));
  }
  // tinte azul marino + degradados arriba/abajo para legibilidad
  ctx.save();
  ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = 'rgba(70,95,140,1)'; ctx.globalAlpha = .35; ctx.fillRect(0, 0, W, H);
  ctx.restore();
  let g = ctx.createLinearGradient(0, 0, 0, 700);
  g.addColorStop(0, 'rgba(6,20,42,.92)'); g.addColorStop(.55, 'rgba(6,20,42,.45)'); g.addColorStop(1, 'rgba(6,20,42,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, 700);
  g = ctx.createLinearGradient(0, H - 700, 0, H);
  g.addColorStop(0, 'rgba(6,20,42,0)'); g.addColorStop(1, 'rgba(6,20,42,.9)');
  ctx.fillStyle = g; ctx.fillRect(0, H - 700, W, 700);
}
function drawFinish(t, frame) {
  // viñeta
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .28, W / 2, H / 2, H * .72);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.55)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  // grano
  const gi = GRAIN[frame % GRAIN.length];
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .085;
  const ox = Math.floor(hash(frame) * 40), oy = Math.floor(hash(frame + 7) * 40);
  ctx.drawImage(gi, -ox, -oy, W + 80, H + 80);
  ctx.restore();
  // parpadeo sutil de película
  const fl = (hash(frame * 3.1) - .5) * .035;
  if (fl > 0) { ctx.fillStyle = `rgba(255,240,220,${fl})`; ctx.fillRect(0, 0, W, H); }
  else { ctx.fillStyle = `rgba(0,0,0,${-fl})`; ctx.fillRect(0, 0, W, H); }
}

// ---------- Subtítulos palabra por palabra (arriba) ----------
const CHUNKS = (() => {
  const out = []; let cur = [];
  for (let i = 0; i < WD.length; i++) {
    const prev = WD[i - 1];
    const brk = cur.length && (cur.length >= 4 || /[.,?!]$/.test(prev.w) || WD[i].s - prev.e > .32);
    if (brk) { out.push(cur); cur = []; }
    cur.push(i);
  }
  if (cur.length) out.push(cur);
  return out.map((c, k) => ({ idx: c, s: WD[c[0]].s - .05, e: 0 })).map((c, k, a) => {
    const last = c.idx[c.idx.length - 1];
    c.e = Math.min(a[k + 1] ? a[k + 1].s : 99, WD[last].e + .6); return c;
  });
})();
function subWord(w) { return w.toUpperCase(); }
function drawSubs(t) {
  if (t >= 74.15) return;
  const ch = CHUNKS.find(c => t >= c.s && t < c.e); if (!ch) return;
  const F = font('InterX', 68, 900), LS = 0;
  const words = ch.idx.map(i => ({ i, w: subWord(WD[i].w), wd: measure(subWord(WD[i].w), F, LS) }));
  const sp = 20, maxW = 940;
  // partir en líneas
  const lines = [[]]; let lw = 0;
  for (const w of words) {
    if (lines[lines.length - 1].length && lw + sp + w.wd > maxW) { lines.push([]); lw = 0; }
    lines[lines.length - 1].push(w); lw += (lw ? sp : 0) + w.wd;
  }
  const lh = 88, y0 = 330 - (lines.length - 1) * lh / 2;
  lines.forEach((ln, li) => {
    const tw = ln.reduce((a, w) => a + w.wd, 0) + sp * (ln.length - 1);
    let x = W / 2 - tw / 2; const y = y0 + li * lh;
    for (const w of ln) {
      const st = WD[w.i].s, en = WD[w.i].e;
      if (t >= st - .04) {
        const k = eBack(prog(t, st - .04, .16));
        const nxt = WD[w.i + 1];
        const active = t >= st - .04 && (!nxt || t < nxt.s - .04) && t < en + .25;
        const cx = x + w.wd / 2;
        pop(cx, y, lerp(.7, 1, k), () => {
          if (active) {
            ctx.save(); ctx.globalAlpha *= clamp(k * 2); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 16;
            rrect(x - 12, y - 46, w.wd + 24, 90, 14, RED); ctx.restore();
          }
          text(w.w, cx, y + 3, { font: F, ls: LS, color: WHITE, alpha: clamp(k * 2), stroke: active ? 0 : 10, blur: 10 });
        });
      }
      x += w.wd + sp;
    }
  });
}

// marca pequeña arriba
function drawLogoMark(x, y, s, o = {}) {
  // lupa: anillo azul marino, mango rojo, "?" rojo
  const ring = o.ring || NAVY_L, handle = o.handle || RED;
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.save(); ctx.rotate(Math.PI / 4);
  rrect(70, -16, 120, 32, 16, handle);
  ctx.restore();
  circle(0, 0, 92, o.lens || 'rgba(255,255,255,.95)');
  circle(0, 0, 92, null, ring, 26);
  text('?', 2, 6, { font: font('Anton', 120), color: RED, shadow: false });
  ctx.restore();
}
function drawBrandBug(t) {
  const a = vis(t, .3, 74.0, .6, .4) * .85;
  withA(a, () => {
    const F = font('Oswald', 28, 700);
    const w = measure('CAPITAL CURIOSO', F, 6);
    const x0 = W / 2 - (w + 46) / 2;
    drawLogoMark(x0 + 16, 160, .17, { ring: NAVY_L, lens: 'rgba(255,255,255,.95)' });
    text('CAPITAL ', x0 + 46, 162, { font: F, ls: 6, align: 'left', color: WHITE, blur: 8 });
    const w1 = measure('CAPITAL ', F, 6);
    text('CURIOSO', x0 + 46 + w1, 162, { font: F, ls: 6, align: 'left', color: RED, blur: 8 });
  });
}

// ---------- Tarjetas de fuente (abajo) ----------
const SOURCES = [
  ['Fuente: Maldita.es', 13.4, 28.45],
  ['Fuente: FEMA y FCC', 30.2, 43.15],
  ['Fuente: Acento y CDN', 51.2, 58.45],
];
function drawSources(t) {
  for (const [s, a, b] of SOURCES) {
    const k = vis(t, a, b, .45, .35); if (k <= 0) continue;
    const F = font('InterX', 30, 600);
    const w = measure(s, F) + 64;
    const x = 64 - (1 - k) * 60, y = 1618;
    withA(k, () => {
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 20;
      rrect(x, y, w, 62, 12, 'rgba(6,20,42,.88)'); ctx.restore();
      rrect(x, y, 10, 62, [12, 0, 0, 12], RED);
      text(s, x + 34, y + 33, { font: F, align: 'left', color: 'rgba(255,255,255,.92)', shadow: false });
    });
  }
}

// =====================================================================
// ESCENA 1 — El rumor (0 – 12.95)
// =====================================================================
function scene1(t) {
  // etiqueta "EL RUMOR EN REDES"
  withA(vis(t, 3.3, 11.5), () => tag('EL RUMOR EN REDES', W / 2, 520, RED));
  // 17 NOV
  const a17 = vis(t, ws(4) - .1, 3.25, .3, .3);
  withA(a17, () => {
    const k = eBack(prog(t, ws(4) - .1, .5));
    pop(W / 2, 900, lerp(.6, 1, k), () => {
      // hoja de calendario
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 20;
      rrect(W / 2 - 250, 640, 500, 540, 30, WHITE); ctx.restore();
      rrect(W / 2 - 250, 640, 500, 150, [30, 30, 0, 0], RED);
      for (const dx of [-150, 150]) { circle(W / 2 + dx, 640, 18, NAVY_D); rrect(W / 2 + dx - 8, 600, 16, 60, 8, '#C9CFD8'); }
      text('NOV', W / 2, 718, { font: font('Anton', 110), ls: 14, color: WHITE, shadow: false });
      const n = Math.round(lerp(1, 17, eOut(prog(t, ws(4) - .1, .6))));
      text(String(n), W / 2, 985, { font: font('Anton', 330), color: NAVY, shadow: false });
    });
  });
  // contador 72 HORAS
  const ac = vis(t, ws(13), 9.0, .35, .4);
  withA(ac, () => {
    const cx = W / 2, cy = 830;
    const k = eOut(prog(t, ws(14) - .45, 1.1));
    const n = Math.round(72 * k);
    circle(cx, cy, 215, 'rgba(6,20,42,.78)');
    circle(cx, cy, 200, null, 'rgba(255,255,255,.15)', 16);
    ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = RED; ctx.lineWidth = 16;
    ctx.beginPath(); ctx.arc(cx, cy, 200, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * k); ctx.stroke(); ctx.restore();
    text(String(n), cx, cy - 20, { font: font('Anton', 220), color: WHITE });
    text('HORAS', cx, cy + 112, { font: font('Oswald', 58, 700), ls: 12, color: WHITE });
    text('¿SIN…?', cx, cy + 290, { font: font('Oswald', 48, 700), ls: 8, color: 'rgba(255,255,255,.85)', alpha: vis(t, 6.0, 9.0) });
  });
  // tres íconos que se apagan
  const items = [['lightbulb', 'lightbulb-off', 'LUZ', ws(17)], ['wifi', 'wifi-off', 'INTERNET', ws(19)], ['landmark', 'landmark', 'BANCOS', ws(22)]];
  items.forEach(([on, off, lab, tOff], i) => {
    const x = 220 + i * 320, y = 1300;
    const a = vis(t, 5.7 + i * .12, 9.05, .3, .4);
    withA(a, () => {
      const kin = eBack(prog(t, 5.7 + i * .12, .4));
      const dead = t >= tOff;
      // parpadeo antes de apagarse
      const fl = (t > tOff - .25 && t < tOff) ? (hash(Math.floor(t * 30) + i) > .5 ? 1 : .3) : 1;
      pop(x, y, kin, () => {
        if (!dead) { ctx.save(); glow(`rgba(255,201,74,${.9 * fl})`, 60); circle(x, y, 110, `rgba(255,201,74,${.25 * fl})`); ctx.restore(); }
        circle(x, y, 110, dead ? 'rgba(20,26,36,.92)' : 'rgba(6,20,42,.85)', dead ? 'rgba(255,255,255,.18)' : AMBER, 6);
        drawIcon(dead ? off : on, dead ? GRAY : AMBER, x, y - 6, 120, 2, dead ? 1 : fl);
        if (dead) {
          const kx = eOut(prog(t, tOff, .25));
          ctx.save(); ctx.strokeStyle = RED; ctx.lineWidth = 12; ctx.lineCap = 'round';
          ctx.beginPath(); ctx.moveTo(x - 78, y - 78); ctx.lineTo(x - 78 + 156 * kx, y - 78 + 156 * kx); ctx.stroke(); ctx.restore();
        }
        text(lab, x, y + 160, { font: font('Oswald', 44, 700), ls: 6, color: dead ? GRAY : WHITE });
      });
    });
  });
  // "¿Predicción?" mientras habla de Los Simpson (sin imágenes de la serie)
  withA(vis(t, ws(23), 11.55, .3, .3), () => {
    const k = eBack(prog(t, ws(23), .4));
    pop(W / 2, 1000, k, () => {
      panel(W / 2 - 380, 880, 760, 240, 30);
      text('¿LO «PREDIJO»', W / 2, 960, { font: font('Anton', 92), ls: 3 });
      text('UNA SERIE DE TV?', W / 2, 1060, { font: font('Anton', 92), ls: 3, color: RED });
    });
  });
  // sello ¿VERDAD O RUMOR?
  withA(vis(t, ws(30) - .05, 12.95, .05, .3), () => stamp('¿VERDAD O RUMOR?', W / 2, 980, -.12, prog(t, ws(30) - .05, .28), RED, 100));
}
function tag(str, x, y, color = RED, a = 1) {
  const F = font('Oswald', 34, 700); const w = measure(str, F, 6) + 50;
  withA(a, () => { rrect(x - w / 2, y - 30, w, 60, 8, color); text(str, x, y + 2, { font: F, ls: 6, shadow: false }); });
}

// =====================================================================
// ESCENA 2 — La serie (12.95 – 28.6)
// =====================================================================
function scene2(t) {
  // ficha de datos
  withA(vis(t, ws(34) - .1, 17.9), () => {
    const x = 120, y = 1050, w = 840, h = 380;
    const k = eOut(prog(t, ws(34) - .1, .5));
    ctx.save(); ctx.translate(0, (1 - k) * 80);
    panel(x, y, w, h, 28, .88);
    rrect(x, y, w, 90, [28, 28, 0, 0], RED);
    text('FICHA DEL CAPÍTULO', x + 40, y + 47, { font: font('Oswald', 40, 700), ls: 8, align: 'left', shadow: false });
    drawIcon('tv', WHITE, x + w - 60, y + 45, 56, 2.2);
    // temporada
    const k1 = prog(t, ws(37) - .05, .7);
    withA(clamp(k1 * 3), () => {
      text('TEMPORADA', x + 50, y + 170, { font: font('Oswald', 40, 600), ls: 6, align: 'left', color: 'rgba(255,255,255,.75)', shadow: false });
      text(String(Math.round(35 * eOut(k1))), x + w - 50, y + 168, { font: font('Anton', 110), align: 'right', color: WHITE });
    });
    ctx.fillStyle = 'rgba(255,255,255,.14)'; ctx.fillRect(x + 40, y + 240, w - 80, 2);
    const k2 = prog(t, ws(39) - .05, .7);
    withA(clamp(k2 * 3), () => {
      text('ESTRENADO EN', x + 50, y + 310, { font: font('Oswald', 40, 600), ls: 6, align: 'left', color: 'rgba(255,255,255,.75)', shadow: false });
      text(String(Math.round(lerp(2000, 2023, eOut(k2)))), x + w - 50, y + 308, { font: font('Anton', 110), align: 'right', color: RED });
    });
    ctx.restore();
  });
  // calendario + AÑO: ?
  withA(vis(t, ws(42) - .1, 23.5), () => {
    const k = eOut(prog(t, ws(42) - .1, .55));
    const cx = 90, cy = 820 + (1 - k) * 60, cw = 560, chh = 600;
    ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 18;
    rrect(cx, cy, cw, chh, 26, '#F4F5F7'); ctx.restore();
    rrect(cx, cy, cw, 110, [26, 26, 0, 0], RED);
    text('NOVIEMBRE', cx + cw / 2, cy + 58, { font: font('Anton', 66), ls: 10, shadow: false });
    const days = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
    const gx = cx + 40, gw = (cw - 80) / 7, gy = cy + 160;
    days.forEach((d, i) => text(d, gx + gw * i + gw / 2, gy, { font: font('Oswald', 30, 700), color: GRAY, shadow: false }));
    const off = 6; // 1 de nov. en domingo (cuadrícula genérica)
    for (let d = 1; d <= 30; d++) {
      const p = d - 1 + off, col = p % 7, row = Math.floor(p / 7);
      const x = gx + gw * col + gw / 2, y = gy + 62 + row * 64;
      const hit = d === 17;
      text(String(d), x, y, { font: font('InterX', 32, hit ? 900 : 600), color: hit ? RED : NAVY, shadow: false });
      if (hit) {
        const kc = eIO(prog(t, ws(49), .6));
        if (kc > 0) {
          ctx.save(); ctx.strokeStyle = RED; ctx.lineWidth = 7; ctx.lineCap = 'round';
          ctx.beginPath(); ctx.ellipse(x, y, 44, 36, -.2, -Math.PI * .6, -Math.PI * .6 + Math.PI * 2.15 * kc); ctx.stroke(); ctx.restore();
        }
        if (kc >= 1) { const kk = eBack(prog(t, ws(49) + .6, .4)); const py = cy + chh + 60; pop(cx + cw / 2, py, kk, () => { rrect(cx + cw / 2 - 170, py - 36, 340, 72, 36, RED); text('17 DE NOVIEMBRE', cx + cw / 2, py + 2, { font: font('Oswald', 32, 700), ls: 3, shadow: false }); }); }
      }
    }
    // AÑO: ?
    const ka = prog(t, ws(52) - .05, .45);
    withA(clamp(ka * 2.5), () => {
      const bx = 690, by = 900 + (1 - eOut(ka)) * 40, bw = 300, bh = 440;
      panel(bx, by, bw, bh, 26, .9);
      text('AÑO', bx + bw / 2, by + 80, { font: font('Oswald', 56, 700), ls: 10 });
      const blink = Math.floor((t - ws(52)) * 3) % 2 === 0 ? 1 : .25;
      ctx.save(); glow('rgba(224,38,47,.9)', 40 * blink);
      text('?', bx + bw / 2, by + 270, { font: font('Anton', 260), color: RED, alpha: blink, shadow: false }); ctx.restore();
      text('NUNCA LO DICE', bx + bw / 2, by + bh - 40, { font: font('Oswald', 28, 600), ls: 3, color: 'rgba(255,255,255,.8)', shadow: false });
    });
  });
  // sello ES FICCIÓN
  withA(vis(t, ws(57) - .05, 24.75, .05, .3), () => stamp('ES FICCIÓN', W / 2, 960, -.1, prog(t, ws(57) - .05, .28), RED, 150));
  // línea de tiempo 2023 → 2024 → 2026
  withA(vis(t, 24.6, 28.6, .35, .4), () => {
    const y = 1000, x0 = 150, x1 = 930;
    panel(70, 760, 940, 470, 30, .78);
    text('EL MISMO RUMOR, UNA Y OTRA VEZ', W / 2, 830, { font: font('Oswald', 38, 700), ls: 4, color: 'rgba(255,255,255,.9)', shadow: false });
    const nodes = [[x0, '2023', 'SE ESTRENA', 24.75, WHITE], [(x0 + x1) / 2, '2024', 'RUMOR', ws(66) - .05, RED], [x1, '2026', 'RUMOR OTRA VEZ', ws(66) + .75, RED]];
    // línea
    const kl = (t < nodes[1][3]) ? lerp(0, .5, eOut(prog(t, 24.75, 1.6))) * (t >= 24.75 ? 1 : 0) : (t < nodes[2][3] ? lerp(.5, .5, 1) : 1);
    let lineEnd = x0;
    if (t >= nodes[2][3]) lineEnd = lerp((x0 + x1) / 2, x1, eOut(prog(t, nodes[2][3] - .3, .4)));
    else if (t >= nodes[1][3]) lineEnd = lerp(x0, (x0 + x1) / 2, eOut(prog(t, nodes[1][3] - .35, .4)));
    else lineEnd = lerp(x0, x0 + 150, eOut(prog(t, 24.9, 1.5)));
    ctx.save(); ctx.strokeStyle = 'rgba(255,255,255,.2)'; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
    ctx.strokeStyle = RED; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(lineEnd, y); ctx.stroke(); ctx.restore();
    nodes.forEach(([x, yr, cap, st, col], i) => {
      const k = prog(t, st, .45); if (k <= 0) return;
      const s = eBack(k);
      pop(x, y, s, () => {
        if (i === 2) { const p = (t * 1.6) % 1; circle(x, y, 26 + p * 40, null, `rgba(224,38,47,${1 - p})`, 5); }
        circle(x, y, 26, col === WHITE ? WHITE : RED); circle(x, y, 26, null, NAVY_D, 6);
      });
      withA(clamp(k * 2), () => {
        text(yr, x, y - 92, { font: font('Anton', 96), color: col });
        text(cap, x, y + 82, { font: font('Oswald', i === 2 ? 30 : 34, 700), ls: 3, color: WHITE });
      });
    });
  });
}

// =====================================================================
// ESCENA 3 — Lo que sí pasará (28.6 – 43.3)
// =====================================================================
let US_BB, DR_BB;
function bbox(polys) {
  let a = [1e9, 1e9, -1e9, -1e9];
  for (const p of polys) for (const r of p) for (const [x, y] of r) { a[0] = Math.min(a[0], x); a[1] = Math.min(a[1], y); a[2] = Math.max(a[2], x); a[3] = Math.max(a[3], y); }
  return a;
}
function fitter(bb, x, y, w, h) {
  const s = Math.min(w / (bb[2] - bb[0]), h / (bb[3] - bb[1]));
  const ox = x + (w - (bb[2] - bb[0]) * s) / 2 - bb[0] * s, oy = y + (h - (bb[3] - bb[1]) * s) / 2 - bb[1] * s;
  return ([px, py]) => [ox + px * s, oy + py * s];
}
function pathPolys(polys, f) {
  ctx.beginPath();
  for (const p of polys) for (const r of p) { r.forEach((c, i) => { const [x, y] = f(c); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath(); }
}
function scene3(t) {
  // pregunta de transición
  withA(vis(t, 28.65, 30.0, .3, .3), () => {
    const k = eBack(prog(t, 28.65, .4));
    pop(W / 2, 960, k, () => {
      text('¿Y QUÉ PASA', W / 2, 900, { font: font('Anton', 120), ls: 2 });
      text('DE VERDAD?', W / 2, 1030, { font: font('Anton', 120), ls: 2, color: RED });
    });
  });
  // mapa de EE. UU.
  withA(vis(t, ws(73) - .1, 33.7, .4, .4), () => {
    const f = fitter(US_BB, 110, 580, 860, 540);
    const kf = eOut(prog(t, ws(74), .6));
    ctx.save(); glow('rgba(224,38,47,.7)', 50 * kf);
    pathPolys(GEO.us, f); ctx.fillStyle = `rgba(${lerp(29, 224, kf) | 0},${lerp(78, 38, kf) | 0},${lerp(158, 47, kf) | 0},.92)`; ctx.fill('evenodd');
    ctx.restore();
    ctx.save(); ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 1.2; ctx.beginPath();
    for (const l of GEO.usStates) l.forEach((c, i) => { const [x, y] = f(c); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); ctx.restore();
    pathPolys(GEO.us, f); ctx.strokeStyle = WHITE; ctx.lineWidth = 3; ctx.stroke();
    // ondas de alerta
    if (kf > .5) for (let j = 0; j < 3; j++) { const p = ((t - ws(74)) * .8 + j / 3) % 1; circle(560, 850, 60 + p * 420, null, `rgba(255,255,255,${.5 * (1 - p)})`, 4); }
    text('ESTADOS UNIDOS', W / 2, 560, { font: font('Oswald', 42, 700), ls: 10, alpha: kf });
    // rótulo
    const kr = prog(t, ws(77) - .1, .5);
    withA(clamp(kr * 2), () => {
      const y = 1180 + (1 - eOut(kr)) * 50;
      panel(70, y, 940, 230, 22, .9);
      rrect(70, y, 940, 64, [22, 22, 0, 0], RED);
      drawIcon('triangle-alert', WHITE, 116, y + 32, 40, 2.4);
      text('PRUEBA NACIONAL', 150, y + 34, { font: font('Oswald', 34, 700), ls: 8, align: 'left', shadow: false });
      text('del Sistema de Alertas', W / 2, y + 112, { font: font('InterX', 54, 900) });
      text('de Emergencia', W / 2, y + 180, { font: font('InterX', 54, 900) });
    });
  });
  // reloj 3:20 p. m. + cronómetro
  withA(vis(t, ws(82) - .1, 38.85, .4, .35), () => {
    const cx = 300, cy = 880, R = 185;
    const k = eBack(prog(t, ws(82) - .1, .5));
    pop(cx, cy, k, () => {
      circle(cx, cy, R + 14, 'rgba(6,20,42,.9)'); circle(cx, cy, R, '#F4F5F7'); circle(cx, cy, R, null, NAVY, 10);
      for (let i = 0; i < 60; i++) {
        const a = i / 60 * Math.PI * 2, big = i % 5 === 0;
        ctx.save(); ctx.strokeStyle = big ? NAVY : '#9AA3B2'; ctx.lineWidth = big ? 7 : 2.5;
        ctx.beginPath(); ctx.moveTo(cx + Math.sin(a) * (R - (big ? 34 : 20)), cy - Math.cos(a) * (R - (big ? 34 : 20))); ctx.lineTo(cx + Math.sin(a) * (R - 12), cy - Math.cos(a) * (R - 12)); ctx.stroke(); ctx.restore();
      }
      const m = 120 + 80 * eIO(prog(t, ws(85) - .4, 1.2)); // de 2:00 a 3:20
      const ha = (m / 60) / 12 * Math.PI * 2, ma = (m % 60) / 60 * Math.PI * 2;
      ctx.save(); ctx.lineCap = 'round';
      ctx.strokeStyle = NAVY; ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(ha) * R * .5, cy - Math.cos(ha) * R * .5); ctx.stroke();
      ctx.strokeStyle = RED; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(ma) * R * .78, cy - Math.cos(ma) * R * .78); ctx.stroke();
      ctx.restore(); circle(cx, cy, 13, RED);
    });
    const kd = prog(t, ws(85), .4);
    withA(clamp(kd * 2), () => {
      text('3:20 p. m.', cx, cy + 270, { font: font('Anton', 92) });
    });
    withA(clamp(prog(t, ws(91) - .05, .35) * 2), () => tag('HORA DOMINICANA', cx, cy + 360, NAVY_L));
    // cronómetro
    const ks = prog(t, ws(93) - .1, .45);
    withA(clamp(ks * 2), () => {
      const sx = 790, sy = 900, r = 150;
      pop(sx, sy, eBack(ks), () => {
        rrect(sx - 30, sy - r - 60, 60, 40, 8, '#C9CFD8'); rrect(sx - 12, sy - r - 26, 24, 30, 4, '#C9CFD8');
        circle(sx, sy, r + 12, 'rgba(6,20,42,.9)'); circle(sx, sy, r, null, 'rgba(255,255,255,.18)', 18);
        const kk = eIO(prog(t, ws(95), we(98) - ws(95)));
        ctx.save(); ctx.strokeStyle = RED; ctx.lineWidth = 18; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.arc(sx, sy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * kk); ctx.stroke(); ctx.restore();
        text('1', sx, sy - 18, { font: font('Anton', 150) });
        text('MINUTO', sx, sy + 78, { font: font('Oswald', 40, 700), ls: 6 });
      });
      text('CRONÓMETRO', sx, sy + 240, { font: font('Oswald', 34, 700), ls: 6, color: 'rgba(255,255,255,.85)' });
    });
  });
  // radio y TV con check verde
  withA(vis(t, ws(99) - .1, 43.3, .35, .35), () => {
    text('SOLO EN EE. UU.', W / 2, 600, { font: font('Oswald', 44, 700), ls: 8 });
    [['radio', 'RADIO', ws(102)], ['tv', 'TELEVISIÓN', ws(105)]].forEach(([ic, lab, st], i) => {
      const x = 330 + i * 420, y = 800;
      const k = prog(t, ws(99) - .1 + i * .15, .4);
      withA(clamp(k * 2), () => {
        pop(x, y, eBack(k), () => {
          circle(x, y, 130, 'rgba(6,20,42,.88)', 'rgba(255,255,255,.3)', 4);
          drawIcon(ic, WHITE, x, y, 140, 1.8);
        });
        text(lab, x, y + 185, { font: font('Oswald', 42, 700), ls: 6 });
        greenCheckBadge(x + 95, y - 95, 46, prog(t, st, .5));
      });
    });
  });
  // bombillo y wifi siguen funcionando
  withA(vis(t, ws(108) - .1, 43.3, .35, .35), () => {
    panel(90, 1090, 900, 420, 30, .86);
    [['lightbulb', 'LUZ', ws(112)], ['wifi', 'INTERNET', ws(115)]].forEach(([ic, lab, st], i) => {
      const x = 330 + i * 420, y = 1240;
      const k = prog(t, ws(108) + i * .12, .4);
      const on = prog(t, st - .1, .3);
      withA(clamp(k * 2), () => {
        pop(x, y, eBack(k), () => {
          ctx.save(); glow(`rgba(255,201,74,${.9 * on})`, 50); circle(x, y, 100, `rgba(255,201,74,${.18 * on})`); ctx.restore();
          circle(x, y, 100, 'rgba(6,20,42,.9)', on > .5 ? AMBER : 'rgba(255,255,255,.3)', 5);
          drawIcon(ic, on > .5 ? AMBER : WHITE, x, y - 4, 112, 2);
        });
        greenCheckBadge(x + 76, y - 76, 38, prog(t, st, .5));
      });
    });
    const kt = prog(t, ws(112), .4);
    withA(clamp(kt * 2), () => pop(W / 2, 1430, eBack(kt), () => text('SIGUEN FUNCIONANDO', W / 2, 1430, { font: font('Anton', 76), ls: 3, color: GREEN })));
  });
}

// =====================================================================
// ESCENA 4 — República Dominicana (43.3 – 58.6)
// =====================================================================
const RD_CITIES = [[-69.93, 18.48, 1.6], [-70.69, 19.45, 1.3], [-68.97, 18.43, .9], [-70.69, 19.79, .8], [-69.31, 18.46, .9], [-68.37, 18.58, .9],
  [-68.71, 18.62, .7], [-70.25, 19.3, .9], [-70.53, 19.22, .8], [-71.1, 18.2, .7], [-71.23, 18.8, .7], [-71.65, 19.85, .6], [-69.34, 19.2, .6],
  [-70.41, 18.94, .7], [-70.73, 18.45, .7], [-70.0, 18.6, .6], [-69.6, 18.75, .6], [-70.95, 19.55, .6], [-71.4, 19.4, .5], [-69.9, 19.0, .5]];
const prj = ([lo, la]) => [lo * Math.cos(19 * Math.PI / 180), -la];
function drawRD(t, x, y, w, h, darkK, lightsOff) {
  const f = fitter(DR_BB, x, y, w, h);
  // Haití en tenue
  pathPolys(GEO.haiti, f); ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fill('evenodd');
  ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 2; ctx.stroke();
  ctx.save(); glow(`rgba(29,78,158,${.9 * (1 - darkK)})`, 60);
  pathPolys(GEO.dr, f);
  const c0 = [16, 44, 88], c1 = [8, 10, 14];
  ctx.fillStyle = `rgb(${lerp(c0[0], c1[0], darkK) | 0},${lerp(c0[1], c1[1], darkK) | 0},${lerp(c0[2], c1[2], darkK) | 0})`; ctx.fill('evenodd');
  ctx.restore();
  pathPolys(GEO.dr, f); ctx.strokeStyle = `rgba(255,255,255,${lerp(.95, .45, darkK)})`; ctx.lineWidth = 4; ctx.stroke();
  // luces de ciudades
  RD_CITIES.forEach(([lo, la, s], i) => {
    const [px, py] = f(prj([lo, la]));
    const off = lightsOff(i, px);
    if (off >= 1) { circle(px, py, 4 * s, 'rgba(120,120,120,.5)'); return; }
    const fl = off > 0 ? (hash(Math.floor(t * 24) * 7 + i) > .5 ? 1 : .2) : 1;
    ctx.save(); glow(`rgba(255,201,74,${fl})`, 30 * s);
    circle(px, py, 7 * s, `rgba(255,214,110,${fl})`); ctx.restore();
  });
  return f;
}
function scene4(t) {
  const tOff = 51.6; // empieza el apagón (al decir la fecha)
  const tOff2 = ws(149) + .2; // febrero: vuelve a apagarse
  const relight = t > 55.55 && t < tOff2;
  const darkA = relight ? 1 - eOut(prog(t, 55.55, .3)) : eIO(prog(t, tOff, 2.0));
  const darkB = eIO(prog(t, tOff2, .8));
  const darkK = t < 55.55 ? darkA : (relight ? darkA : darkB);
  const mapA = vis(t, ws(116) - .15, 58.6, .45, .35);
  const small = eIO(prog(t, 50.7, .8));
  withA(mapA, () => {
    const k = eOut(prog(t, ws(116) - .15, .8));
    const mw = lerp(900, 760, small), mh = lerp(560, 440, small), my = lerp(620, 540, small);
    ctx.save(); ctx.translate(0, (1 - k) * 60);
    drawRD(t, (W - mw) / 2, my, mw, mh, darkK, (i, px) => {
      if (t < tOff) return 0;
      const st = (relight ? 99 : (t >= tOff2 ? tOff2 : tOff)) + (px / W) * 1.4;
      if (relight) return 0;
      return t < st ? 0 : (t < st + .25 ? .5 : 1);
    });
    ctx.restore();
    withA(1 - small, () => text('REPÚBLICA DOMINICANA', W / 2, 560, { font: font('Oswald', 44, 700), ls: 10, alpha: k }));
  });
  // bandera en recuadro
  withA(vis(t, 44.0, 50.8, .5, .4), () => {
    const im = IMG['14_bandera_dominicana']; const k = eBack(prog(t, 44.0, .5));
    pop(880, 1250, k, () => {
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 30;
      rrect(770, 1150, 220, 200, 18, WHITE); ctx.restore();
      ctx.save(); ctx.beginPath(); ctx.roundRect(780, 1160, 200, 180, 12); ctx.clip();
      ctx.filter = 'saturate(.85)'; ctx.drawImage(im, 120, 140, 860, 760, 780, 1160, 200, 180); ctx.restore();
    });
  });
  // Alerta oficial en RD: NINGUNA
  withA(vis(t, ws(120) - .15, 50.8, .4, .35), () => {
    const y = 1180;
    panel(90, y, 650, 260, 26, .9);
    text('ALERTA OFICIAL EN RD:', 120, y + 70, { font: font('Oswald', 44, 700), ls: 4, align: 'left', shadow: false });
    const kn = prog(t, ws(121), .3);
    if (kn > 0) {
      withA(1, () => {
        ctx.save(); ctx.translate(410, y + 175); ctx.rotate(-.03); ctx.scale(lerp(1.8, 1, eOut(kn)), lerp(1.8, 1, eOut(kn)));
        ctx.globalAlpha *= clamp(kn * 3);
        rrect(-280, -60, 560, 120, 14, RED);
        text('NINGUNA', 0, 4, { font: font('Anton', 100), ls: 10, shadow: false });
        ctx.restore();
      });
    }
  });
  // Pero ojo
  withA(vis(t, ws(124), 50.8, .3, .35), () => {
    const k = eBack(prog(t, ws(124), .4));
    pop(250, 1520, k, () => { rrect(90, 1475, 320, 90, 45, AMBER); drawIcon('eye', NAVY_D, 150, 1520, 54, 2.6); text('¡OJO!', 280, 1524, { font: font('Anton', 62), color: NAVY_D, shadow: false }); });
  });
  // 11 NOV 2025 + casi 11 millones
  withA(vis(t, ws(135) - .1, 55.75, .35, .35), () => {
    const k = eBack(prog(t, ws(135) - .1, .45));
    pop(W / 2, 1110, k, () => {
      text('11 NOV', W / 2, 1080, { font: font('Anton', 190), ls: 4 });
      const ky = prog(t, ws(139) - .05, .35);
      withA(clamp(ky * 2), () => { rrect(W / 2 - 150, 1185, 300, 84, 10, RED); text('2025', W / 2, 1230, { font: font('Anton', 72), ls: 10, shadow: false }); });
    });
    const km = prog(t, ws(141) - .05, 1.4);
    withA(clamp(km * 3), () => {
      const y = 1400;
      panel(90, y - 90, 900, 220, 26, .9);
      drawIcon('users', WHITE, 190, y + 20, 110, 2);
      text('CASI', 280, y - 30, { font: font('Oswald', 38, 700), ls: 6, align: 'left', shadow: false, color: 'rgba(255,255,255,.8)' });
      const n = Math.round(11 * eOut(km));
      text(`${n} MILLONES`, 278, y + 40, { font: font('Anton', 100), align: 'left', shadow: false });
      text('DE AFECTADOS', 280, y + 105, { font: font('Oswald', 32, 700), ls: 6, align: 'left', shadow: false, color: RED });
    });
  });
  // 23 FEB 2026 — otro apagón
  withA(vis(t, ws(148), 58.6, .35, .35), () => {
    const k = eBack(prog(t, ws(148), .45));
    pop(W / 2, 1200, k, () => {
      text('23 FEB', W / 2, 1110, { font: font('Anton', 190), ls: 4 });
      rrect(W / 2 - 150, 1215, 300, 84, 10, RED); text('2026', W / 2, 1260, { font: font('Anton', 72), ls: 10, shadow: false });
    });
    const ko = prog(t, ws(153) - .1, .4);
    withA(clamp(ko * 2), () => pop(W / 2, 1400, eBack(ko), () => {
      panel(W / 2 - 300, 1345, 600, 110, 55, .92);
      drawIcon('zap-off', AMBER, W / 2 - 220, 1400, 60, 2.4);
      text('OTRO APAGÓN', W / 2 + 30, 1404, { font: font('Anton', 70), ls: 3, shadow: false });
    }));
  });
}

// =====================================================================
// ESCENA 5 — Mochila de emergencia (58.6 – 72.35)
// =====================================================================
const KIT = [['glass-water', 'Agua', 169], ['cylinder', 'Comida enlatada', 170], ['flashlight', 'Linterna', 172], ['radio', 'Radio de pilas', 173],
  ['pill', 'Medicinas', 176], ['file-text', 'Documentos', 177], ['banknote', 'Efectivo', 181]];
function backpack(x, y, s) {
  ctx.save(); glow('rgba(224,38,47,.7)', 60); circle(x, y, 150 * s, RED); ctx.restore();
  circle(x, y, 150 * s, null, WHITE, 8 * s);
  drawIcon('backpack', WHITE, x, y, 180 * s, 1.8);
}
function scene5(t) {
  const tHead = ws(166) - .25; // "mochila"
  const tList = 63.0;
  const kHead = eBack(prog(t, tHead, .5));
  const move = eIO(prog(t, tList - .5, .6));
  withA(vis(t, tHead, 70.15, .3, .35), () => {
    const bx = lerp(W / 2, 170, move), by = lerp(900, 640, move), bs = lerp(1.2, .55, move);
    pop(bx, by, kHead, () => backpack(bx, by, bs));
    const tx = lerp(W / 2, 290, move), ty1 = lerp(1150, 605, move), ty2 = lerp(1250, 672, move);
    const al = move > .5 ? 'left' : 'center';
    const fs = lerp(110, 60, move);
    withA(clamp(prog(t, tHead + .1, .3) * 2), () => {
      text('MOCHILA', tx, ty1, { font: font('Anton', fs), ls: 4, align: al });
      text('DE EMERGENCIA', tx, ty2, { font: font('Anton', fs * .8), ls: 4, align: al, color: RED });
    });
  });
  withA(vis(t, 59.0, ws(166) - .2, .4, .3), () => {
    text('CON RUMOR', W / 2, 860, { font: font('Anton', 120), ls: 3, alpha: clamp(prog(t, ws(158), .3) * 2) });
    text('O SIN RUMOR', W / 2, 990, { font: font('Anton', 120), ls: 3, color: RED, alpha: clamp(prog(t, ws(160), .3) * 2) });
  });
  // lista
  withA(vis(t, tList, 70.15, .3, .35), () => {
    panel(70, 760, 940, 820, 30, .84);
    KIT.forEach(([ic, lab, wi], i) => {
      const st = ws(wi) - .08; const k = prog(t, st, .35);
      const y = 830 + i * 108;
      if (i) { ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fillRect(110, y - 54, 860, 2); }
      if (k <= 0) { // casilla vacía en espera
        rrect(880, y - 30, 60, 60, 12, null, 'rgba(255,255,255,.18)', 3); return;
      }
      withA(clamp(k * 2.5), () => {
        ctx.save(); ctx.translate((1 - eOut(k)) * -60, 0);
        circle(160, y, 42, 'rgba(255,255,255,.1)', 'rgba(255,255,255,.35)', 3);
        drawIcon(ic, WHITE, 160, y, 54, 2);
        text(lab, 230, y + 2, { font: font('InterX', 52, 800), align: 'left', shadow: false });
        ctx.restore();
      });
      const kc = prog(t, st + .12, .35);
      rrect(880, y - 30, 60, 60, 12, kc > 0 ? GREEN : null, kc > 0 ? GREEN : 'rgba(255,255,255,.4)', 3);
      checkMark(910, y, 50, kc, WHITE, 9);
    });
  });
  // frase final
  withA(vis(t, ws(182) - .1, 72.4, .2, .3), () => {
    const k1 = eBack(prog(t, ws(182) - .1, .4)), k2 = eBack(prog(t, ws(185) - .1, .4));
    pop(W / 2, 880, k1, () => text('NO ES MIEDO,', W / 2, 880, { font: font('Anton', 140), ls: 2 }));
    if (k2 > 0) pop(W / 2, 1060, k2, () => {
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; rrect(70, 975, 940, 175, 18, RED); ctx.restore();
      text('ES PREVENCIÓN', W / 2, 1068, { font: font('Anton', 140), ls: 2, shadow: false });
    });
  });
}

// =====================================================================
// ESCENA 6 — Encuesta (72.35 – 74.15)
// =====================================================================
function scene6(t) {
  const kq = eOut(prog(t, ws(187) - .1, .4));
  withA(clamp(kq * 2) * (1 - eIn(prog(t, 74.0, .2))), () => {
    ctx.save(); ctx.translate(0, (1 - kq) * 60);
    panel(70, 640, 940, 340, 30, .92);
    rrect(70, 640, 940, 14, [30, 30, 0, 0], RED);
    text('¿Ya tienes tu', W / 2, 760, { font: font('InterX', 78, 900) });
    text('mochila de emergencia?', W / 2, 870, { font: font('InterX', 66, 900) });
    ctx.restore();
    const kb1 = eBack(prog(t, 72.8, .35)), kb2 = eBack(prog(t, 72.95, .35));
    const press = Math.sin(clamp(prog(t, 73.35, .25)) * Math.PI) * .06;
    pop(W / 2, 1100, kb1 * (1 - press), () => { ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; rrect(170, 1040, 740, 125, 62, NAVY_L); ctx.restore(); rrect(170, 1040, 740, 125, 62, null, 'rgba(255,255,255,.35)', 3); text('SÍ', W / 2, 1106, { font: font('Anton', 80), ls: 6, shadow: false }); });
    pop(W / 2, 1260, kb2, () => { ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; rrect(170, 1200, 740, 125, 62, RED); ctx.restore(); rrect(170, 1200, 740, 125, 62, null, 'rgba(255,255,255,.35)', 3); text('TODAVÍA NO', W / 2, 1266, { font: font('Anton', 80), ls: 6, shadow: false }); });
    // flecha hacia los comentarios
    const ka = prog(t, 73.45, .35);
    if (ka > 0) {
      const bob = Math.sin((t - 73.45) * 12) * 12;
      ctx.save(); ctx.globalAlpha *= clamp(ka * 2);
      ctx.translate(0, bob);
      ctx.strokeStyle = WHITE; ctx.lineWidth = 16; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      glow('rgba(0,0,0,.5)', 20);
      const p = eOut(ka);
      ctx.beginPath(); ctx.moveTo(640, 1390); ctx.quadraticCurveTo(900, 1400, lerp(640, 960, p) > 900 ? 960 : lerp(640, 960, p), lerp(1390, 1520, p)); ctx.stroke();
      if (p > .9) { ctx.beginPath(); ctx.moveTo(925, 1478); ctx.lineTo(962, 1525); ctx.lineTo(985, 1468); ctx.stroke(); }
      ctx.restore();
      withA(clamp(ka * 2), () => {
        rrect(250, 1350, 360, 84, 42, 'rgba(6,20,42,.9)', WHITE, 3);
        drawIcon('message-circle', WHITE, 300, 1392, 46, 2.4);
        text('COMENTA', 455, 1396, { font: font('Anton', 52), ls: 4, shadow: false });
      });
    }
  });
}

// =====================================================================
// CIERRE — logo
// =====================================================================
function outro(t) {
  const t0 = 74.1;
  const kbg = eIO(prog(t, t0, .3));
  if (kbg <= 0) return;
  ctx.save(); ctx.globalAlpha = kbg;
  const g = ctx.createRadialGradient(W / 2, 860, 50, W / 2, 900, 1100);
  g.addColorStop(0, '#F7F8FB'); g.addColorStop(1, '#D7DCE6');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.restore();
  const kl = eBack(prog(t, t0 + .1, .45));
  if (kl > 0) pop(W / 2, 820, kl, () => {
    ctx.save(); ctx.translate(W / 2, 820); ctx.rotate((1 - kl) * -.6); ctx.translate(-W / 2, -820);
    ctx.save(); ctx.shadowColor = 'rgba(11,31,58,.35)'; ctx.shadowBlur = 40; ctx.shadowOffsetY = 14;
    drawLogoMark(W / 2 - 40, 790, 1.55, { ring: NAVY, lens: '#FFFFFF' }); ctx.restore();
    ctx.restore();
  });
  const kn = eOut(prog(t, t0 + .3, .35));
  withA(kn, () => {
    const F = font('Anton', 128);
    const w1 = measure('CAPITAL ', F, 3), w2 = measure('CURIOSO', F, 3);
    const x0 = W / 2 - (w1 + w2) / 2;
    ctx.save(); ctx.translate(0, (1 - kn) * 40);
    text('CAPITAL ', x0, 1150, { font: F, ls: 3, align: 'left', color: NAVY, shadow: false });
    text('CURIOSO', x0 + w1, 1150, { font: F, ls: 3, align: 'left', color: RED, shadow: false });
    ctx.restore();
  });
  const kh = eOut(prog(t, t0 + .5, .35));
  withA(kh, () => {
    rrect(W / 2 - 230, 1245, 460, 80, 40, NAVY);
    text('@capitalcuriosoo', W / 2, 1287, { font: font('InterX', 44, 700), shadow: false });
  });
}

// ---------- Ensamblado ----------
const SCENES = [[scene1, 0, 12.95], [scene2, 12.95, 28.6], [scene3, 28.6, 43.3], [scene4, 43.3, 58.6], [scene5, 58.6, 72.35], [scene6, 72.35, 74.3]];
window.renderFrame = function (t) {
  const frame = Math.round(t * 30);
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.filter = 'none';
  drawBackground(t);
  for (const [fn, a, b] of SCENES) if (t >= a - .05 && t <= b + .05) fn(t);
  drawSources(t);
  drawBrandBug(t);
  drawSubs(t);
  outro(t);
  drawFinish(t, frame);
  // fundido de entrada
  if (t < .25) { ctx.fillStyle = `rgba(0,0,0,${1 - t / .25})`; ctx.fillRect(0, 0, W, H); }
  ctx.restore();
};

window.READY = (async () => {
  await document.fonts.load('100px Anton'); await document.fonts.load('700 40px Oswald'); await document.fonts.load('600 40px Oswald');
  await document.fonts.load('900 40px InterX'); await document.fonts.load('700 40px InterX'); await document.fonts.load('600 40px InterX'); await document.fonts.load('800 40px InterX');
  await Promise.all(imgNames.map(async n => { IMG[n] = await loadImg(`../assets/img/${n}.jpg`); }));
  const need = [['lightbulb', AMBER, 2], ['lightbulb-off', GRAY, 2], ['wifi', AMBER, 2], ['wifi-off', GRAY, 2], ['landmark', AMBER, 2], ['landmark', GRAY, 2],
    ['tv', WHITE, 2.2], ['triangle-alert', WHITE, 2.4], ['radio', WHITE, 1.8], ['tv', WHITE, 1.8], ['lightbulb', AMBER, 2], ['lightbulb', WHITE, 2], ['wifi', WHITE, 2],
    ['eye', NAVY_D, 2.6], ['users', WHITE, 2], ['zap-off', AMBER, 2.4], ['backpack', WHITE, 1.8], ['message-circle', WHITE, 2.4],
    ...KIT.map(k => [k[0], WHITE, 2])];
  await Promise.all(need.map(([n, c, s]) => iconImg(n, c, s)));
  makeGrain(); makeSpeck();
  US_BB = bbox(GEO.us); DR_BB = bbox(GEO.dr);
  return true;
})();
