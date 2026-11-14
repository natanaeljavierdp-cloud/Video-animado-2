// Capital Curioso — "Funcionarios en bases militares"
// Cada cuadro es una función pura del tiempo t (segundos): renderFrame(t).
'use strict';
const W = 1080, H = 1920;
const COL = {
  bg: '#050E1D', navy: '#0A1A33', navy2: '#11284D', navy3: '#183564',
  red: '#E3263C', redD: '#A3122A', white: '#FFFFFF', mute: '#B4C6DE', mute2: '#7F95B5',
  land: '#0B1C36', water: '#1C4274', waterEdge: '#2F6AB0',
};
let T, WORDS, ctx, CH = [];
const IMG = {};
const IMG_LIST = ['bessent', 'rubio', 'hegseth', 'noem', 'driscoll', 'miller', 'bondi', 'blanche',
  'casablanca', 'tesoro', 'fortmcnair', 'fortmcnair_aerea', 'anacostia', 'fortmyer', 'iran_misiles'];

// ---------- utilidades ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const prog = (t, a, d) => clamp((t - a) / d);
const lerp = (a, b, x) => a + (b - a) * x;
const eo = x => 1 - Math.pow(1 - x, 3);
const eo5 = x => 1 - Math.pow(1 - x, 5);
const eio = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const back = x => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const F = (w, s, fam = 'Inter') => `${w} ${s}px "${fam}"`;
const FD = (w, s) => F(w, s, 'Inter Display');
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }

function rr(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function drawCover(img, x, y, w, h, fx = .5, fy = .5, zoom = 1) {
  if (!img) return;
  const iw = img.width, ih = img.height;
  const sc = Math.max(w / iw, h / ih) * zoom;
  const sw = w / sc, sh = h / sc;
  const sx = clamp(fx * iw - sw / 2, 0, iw - sw), sy = clamp(fy * ih - sh / 2, 0, ih - sh);
  ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
}
function wrap(text, maxW) {
  const words = text.split(' '); const lines = []; let cur = '';
  for (const w of words) {
    const test = cur ? cur + ' ' + w : w;
    if (ctx.measureText(test).width > maxW && cur) { lines.push(cur); cur = w; } else cur = test;
  }
  if (cur) lines.push(cur);
  return lines;
}
function fitFont(text, weight, size, maxW, fam = 'Inter') {
  let s = size;
  while (s > 10) { ctx.font = F(weight, s, fam); if (ctx.measureText(text).width <= maxW) break; s -= 2; }
  return s;
}
function shadow(blur = 20, a = .55, oy = 6) { ctx.shadowColor = `rgba(0,0,0,${a})`; ctx.shadowBlur = blur; ctx.shadowOffsetY = oy; }
function noShadow() { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; ctx.shadowOffsetX = 0; }
function withAlpha(a, fn) { ctx.save(); ctx.globalAlpha *= clamp(a); fn(); ctx.restore(); }

// fondo oscurecido y desenfocado (pre-renderizado una vez)
const BG = {};
function makeBg(name, blur, bright) {
  const img = IMG[name]; if (!img) return null;
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d');
  const sc = Math.max(W / img.width, H / img.height) * 1.08;
  g.filter = `blur(${blur}px) brightness(${bright}) saturate(.8)`;
  g.drawImage(img, (W - img.width * sc) / 2, (H - img.height * sc) / 2, img.width * sc, img.height * sc);
  return c;
}
function drawKB(c, t, t0, dur, z0 = 1.04, z1 = 1.14, dx = 0, dy = 0) {
  if (!c) return;
  const p = clamp((t - t0) / dur); const z = lerp(z0, z1, p);
  ctx.save(); ctx.translate(W / 2 + dx * p, H / 2 + dy * p); ctx.scale(z, z);
  ctx.drawImage(c, -W / 2, -H / 2); ctx.restore();
}
// grano de película
const GRAIN = [];
function makeGrain() {
  for (let k = 0; k < 4; k++) {
    const c = document.createElement('canvas'); c.width = 540; c.height = 960;
    const g = c.getContext('2d'); const d = g.createImageData(540, 960);
    for (let i = 0; i < d.data.length; i += 4) { const v = Math.random() * 255; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 255; }
    g.putImageData(d, 0, 0); GRAIN.push(c);
  }
}

// ---------- personas ----------
const PEOPLE = {
  bessent: { n: 'SCOTT BESSENT', c: 'Secretario del Tesoro', f: [.47, .2], z: 1.7 },
  rubio: { n: 'MARCO RUBIO', c: 'Secretario de Estado', f: [.46, .22], z: 1.45 },
  hegseth: { n: 'PETE HEGSETH', c: 'Secretario de Guerra', f: [.5, .24], z: 1.25 },
  noem: { n: 'KRISTI NOEM', c: 'Exsecretaria de Seguridad Nacional', f: [.52, .3], z: 1.25 },
  driscoll: { n: 'DAN DRISCOLL', c: 'Secretario del Ejército', f: [.46, .4], z: 1.1 },
  miller: { n: 'STEPHEN MILLER', c: 'Jefe de gabinete de la Casa Blanca', f: [.46, .26], z: 1.5 },
  bondi: { n: 'PAM BONDI', c: 'Exfiscal general', f: [.38, .36], z: 1.15 },
  blanche: { n: 'TODD BLANCHE', c: 'Fiscal general', f: [.64, .24], z: 2.3 },
};
const ORDER8 = ['bessent', 'rubio', 'hegseth', 'noem', 'driscoll', 'miller', 'bondi', 'blanche'];

// tarjeta con foto + rótulo (nombre y cargo)
function personCard(key, x, y, w, h, t0, t, opt = {}) {
  const p = eo(prog(t, t0, .55)); if (p <= 0) return;
  const P = PEOPLE[key];
  const pad0 = Math.max(16, w * .055);
  const ns0 = fitFont(P.n, 900, opt.nameSize || Math.round(w * .085), w - pad0 * 2);
  const cs0 = opt.cargoSize || Math.round(ns0 * .62);
  ctx.font = F(600, cs0); const nl0 = Math.min(2, wrap(P.c, w - pad0 * 2).length);
  const barH = Math.max(opt.barH || Math.round(h * .3), 18 + ns0 + 12 + nl0 * (cs0 + 6) + 18);
  ctx.save();
  ctx.globalAlpha *= p;
  ctx.translate(0, (1 - p) * 70);
  shadow(30, .6, 12); rr(x, y, w, h, 18); ctx.fillStyle = COL.navy; ctx.fill(); noShadow();
  ctx.save(); rr(x, y, w, h, 18); ctx.clip();
  const zoomIn = 1 + .05 * clamp((t - t0) / 6);
  drawCover(IMG[key], x, y, w, h - barH + 4, P.f[0], P.f[1], P.z * zoomIn);
  const g = ctx.createLinearGradient(0, y + h - barH - 90, 0, y + h - barH);
  g.addColorStop(0, 'rgba(10,26,51,0)'); g.addColorStop(1, 'rgba(10,26,51,.85)');
  ctx.fillStyle = g; ctx.fillRect(x, y + h - barH - 90, w, 90);
  ctx.fillStyle = COL.navy; ctx.fillRect(x, y + h - barH, w, barH);
  // barra roja de acento que se dibuja
  const bp = eo(prog(t, t0 + .2, .45));
  ctx.fillStyle = COL.red; ctx.fillRect(x, y + h - barH, w * bp, 7);
  ctx.restore();
  // textos
  const pad = Math.max(16, w * .055);
  const tp = eo(prog(t, t0 + .25, .45));
  ctx.save(); ctx.beginPath(); ctx.rect(x, y + h - barH, w, barH); ctx.clip();
  ctx.translate(-(1 - tp) * 40, 0); ctx.globalAlpha *= tp;
  const ns = fitFont(P.n, 900, opt.nameSize || Math.round(w * .085), w - pad * 2);
  ctx.font = F(900, ns); ctx.fillStyle = COL.white; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  const ny = y + h - barH + 18 + ns;
  ctx.fillText(P.n, x + pad, ny);
  const cs = opt.cargoSize || Math.round(ns * .62);
  ctx.font = F(600, cs); ctx.fillStyle = COL.mute;
  const lines = wrap(P.c, w - pad * 2);
  lines.slice(0, 2).forEach((l, i) => ctx.fillText(l, x + pad, ny + 12 + cs * (i + 1) + i * 6));
  ctx.restore();
  // borde
  rr(x, y, w, h, 18); ctx.strokeStyle = 'rgba(255,255,255,.14)'; ctx.lineWidth = 2; ctx.stroke();
  ctx.restore();
}

// rótulo tipo "lower third"
function lowerThird(name, role, x, y, t0, t) {
  const p = prog(t, t0, .6); if (p <= 0) return;
  ctx.save();
  ctx.font = F(900, 56); const nw = ctx.measureText(name).width + 56;
  ctx.font = F(700, 32); ctx.letterSpacing = '2px'; const rw = ctx.measureText(role.toUpperCase()).width + 52; ctx.letterSpacing = '0px';
  const a = eo5(prog(t, t0, .4)), b = eo5(prog(t, t0 + .15, .4));
  shadow(24, .5, 8);
  ctx.fillStyle = COL.red; ctx.fillRect(x, y, 12, 150 * a);
  ctx.fillStyle = COL.navy; ctx.fillRect(x + 12, y, nw * a, 86);
  ctx.fillStyle = COL.red; ctx.fillRect(x + 12, y + 86, rw * b, 60);
  noShadow();
  ctx.save(); ctx.beginPath(); ctx.rect(x + 12, y, nw * a, 86); ctx.clip();
  ctx.font = F(900, 56); ctx.fillStyle = COL.white; ctx.textAlign = 'left';
  ctx.fillText(name, x + 40, y + 64); ctx.restore();
  ctx.save(); ctx.beginPath(); ctx.rect(x + 12, y + 86, rw * b, 60); ctx.clip();
  ctx.font = F(700, 32); ctx.letterSpacing = '2px'; ctx.fillStyle = COL.white;
  ctx.fillText(role.toUpperCase(), x + 34, y + 128); ctx.restore();
  ctx.restore();
}

// ---------- íconos ilustrados (vectoriales) ----------
function iconHouse(cx, cy, s, col = COL.white, accent = COL.red, lw = 0) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = lw || 7; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.strokeStyle = col;
  // chimenea
  ctx.beginPath(); ctx.moveTo(22, -30); ctx.lineTo(22, -46); ctx.lineTo(34, -46); ctx.lineTo(34, -20); ctx.stroke();
  // techo
  ctx.strokeStyle = accent; ctx.lineWidth = (lw || 7) * 1.3;
  ctx.beginPath(); ctx.moveTo(-56, -2); ctx.lineTo(0, -52); ctx.lineTo(56, -2); ctx.stroke();
  ctx.strokeStyle = col; ctx.lineWidth = lw || 7;
  ctx.beginPath(); ctx.moveTo(-42, -12); ctx.lineTo(-42, 46); ctx.lineTo(42, 46); ctx.lineTo(42, -12); ctx.stroke();
  // puerta y ventana
  ctx.beginPath(); ctx.moveTo(-12, 46); ctx.lineTo(-12, 14); ctx.lineTo(12, 14); ctx.lineTo(12, 46); ctx.stroke();
  ctx.strokeRect(18, -2, 14, 14);
  ctx.restore();
}
function iconBase(cx, cy, s, col = COL.white, accent = COL.red, wave = 0) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = 7; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.strokeStyle = col;
  // mástil y bandera
  ctx.beginPath(); ctx.moveTo(-30, 0); ctx.lineTo(-30, -62); ctx.stroke();
  ctx.fillStyle = accent; ctx.beginPath(); ctx.moveTo(-30, -62);
  for (let i = 0; i <= 10; i++) ctx.lineTo(-30 + i * 4.2, -62 + Math.sin(i * .7 + wave) * 2.5);
  ctx.lineTo(12, -40);
  for (let i = 10; i >= 0; i--) ctx.lineTo(-30 + i * 4.2, -40 + Math.sin(i * .7 + wave) * 2.5);
  ctx.closePath(); ctx.fill();
  // hangar / cuartel
  ctx.beginPath(); ctx.moveTo(-60, 46); ctx.lineTo(-60, 14); ctx.quadraticCurveTo(-60, -10, -30, -10);
  ctx.lineTo(30, -10); ctx.quadraticCurveTo(60, -10, 60, 14); ctx.lineTo(60, 46); ctx.closePath(); ctx.stroke();
  // estrella
  star(0, 18, 17, accent);
  // cerca
  ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(-74, 46); ctx.lineTo(74, 46); ctx.stroke();
  for (let i = -70; i <= 70; i += 20) { ctx.beginPath(); ctx.moveTo(i, 46); ctx.lineTo(i, 58); ctx.stroke(); }
  ctx.restore();
}
function star(x, y, r, fill) {
  ctx.save(); ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 5, rr2 = i % 2 ? r * .45 : r;
    ctx.lineTo(x + Math.cos(a) * rr2, y + Math.sin(a) * rr2);
  }
  ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.restore();
}
function iconPin(x, y, s, label = '', col = COL.red, q = false) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s / 100, s / 100);
  shadow(14, .5, 6);
  ctx.beginPath(); ctx.moveTo(0, 0);
  ctx.bezierCurveTo(-14, -26, -38, -48, -38, -78); ctx.arc(0, -78, 38, Math.PI, 0); ctx.bezierCurveTo(38, -48, 14, -26, 0, 0);
  ctx.fillStyle = col; ctx.fill(); noShadow();
  ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.stroke();
  if (q) { ctx.font = F(900, 54); ctx.fillStyle = COL.white; ctx.textAlign = 'center'; ctx.fillText('?', 0, -58); }
  else { ctx.beginPath(); ctx.arc(0, -78, 14, 0, Math.PI * 2); ctx.fillStyle = COL.white; ctx.fill(); }
  ctx.restore();
}
function iconHeadstone(cx, cy, s, col = COL.white) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = 7; ctx.strokeStyle = col; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  for (const [dx, sc] of [[-36, .7], [36, .7], [0, 1]]) {
    ctx.save(); ctx.translate(dx, sc < 1 ? 8 : 0); ctx.scale(sc, sc);
    ctx.beginPath(); ctx.moveTo(-26, 44); ctx.lineTo(-26, -20); ctx.arc(0, -20, 26, Math.PI, 0); ctx.lineTo(26, 44); ctx.closePath();
    ctx.fillStyle = sc < 1 ? COL.navy3 : COL.navy2; ctx.fill(); ctx.stroke();
    if (sc === 1) { ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(0, 10); ctx.moveTo(-12, -16); ctx.lineTo(12, -16); ctx.strokeStyle = COL.red; ctx.stroke(); }
    ctx.restore();
  }
  ctx.strokeStyle = col; ctx.beginPath(); ctx.moveTo(-70, 46); ctx.lineTo(70, 46); ctx.stroke();
  ctx.restore();
}
function iconMissile(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100); ctx.rotate(-Math.PI / 4);
  ctx.lineWidth = 7; ctx.strokeStyle = COL.white; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(0, -62); ctx.quadraticCurveTo(16, -40, 16, -14); ctx.lineTo(16, 34); ctx.lineTo(-16, 34); ctx.lineTo(-16, -14); ctx.quadraticCurveTo(-16, -40, 0, -62); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-16, 14); ctx.lineTo(-32, 40); ctx.lineTo(-16, 36); ctx.moveTo(16, 14); ctx.lineTo(32, 40); ctx.lineTo(16, 36); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-9, 40); ctx.quadraticCurveTo(0, 74, 9, 40); ctx.fillStyle = '#FFB547'; ctx.fill();
  ctx.restore();
}
function iconCartel(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = 7; ctx.strokeStyle = COL.white; ctx.lineJoin = 'round';
  // fajo de billetes
  for (let i = 0; i < 3; i++) { rr(-56, 6 - i * 16, 82, 44, 6); ctx.fillStyle = COL.redD; ctx.fill(); ctx.stroke(); }
  ctx.font = F(900, 36); ctx.fillStyle = COL.white; ctx.textAlign = 'center'; ctx.fillText('$', -15, -1);
  // cápsula
  ctx.save(); ctx.translate(36, -30); ctx.rotate(-.6);
  rr(-14, -34, 28, 68, 14); ctx.fillStyle = COL.navy; ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-14, 0); ctx.lineTo(14, 0); ctx.stroke(); ctx.restore();
  ctx.restore();
}
function iconTarget(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = 7; ctx.strokeStyle = COL.white; ctx.lineCap = 'round';
  // podio con micrófono
  ctx.beginPath(); ctx.moveTo(-34, 58); ctx.lineTo(-26, 10); ctx.lineTo(26, 10); ctx.lineTo(34, 58); ctx.closePath(); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, 10); ctx.lineTo(0, -6); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, -14, 8, 0, Math.PI * 2); ctx.stroke();
  // mira
  ctx.strokeStyle = COL.white; ctx.lineWidth = 6;
  ctx.beginPath(); ctx.arc(0, -10, 50, 0, Math.PI * 2); ctx.stroke();
  for (const a of [0, 1, 2, 3]) {
    const an = a * Math.PI / 2; ctx.beginPath();
    ctx.moveTo(Math.cos(an) * 36, -10 + Math.sin(an) * 36); ctx.lineTo(Math.cos(an) * 66, -10 + Math.sin(an) * 66); ctx.stroke();
  }
  ctx.restore();
}
function iconShield(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.beginPath(); ctx.moveTo(0, -70); ctx.lineTo(56, -48); ctx.lineTo(56, 0); ctx.quadraticCurveTo(52, 50, 0, 74);
  ctx.quadraticCurveTo(-52, 50, -56, 0); ctx.lineTo(-56, -48); ctx.closePath();
  ctx.fillStyle = 'rgba(255,255,255,.12)'; ctx.fill(); ctx.lineWidth = 8; ctx.strokeStyle = COL.white; ctx.lineJoin = 'round'; ctx.stroke();
  ctx.lineCap = 'round'; ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(-22, 2); ctx.lineTo(-4, 20); ctx.lineTo(26, -14); ctx.stroke();
  ctx.restore();
}
function iconBarrier(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineWidth = 8; ctx.strokeStyle = COL.white; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-50, -20); ctx.lineTo(-50, 64); ctx.moveTo(50, -20); ctx.lineTo(50, 64); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-66, 64); ctx.lineTo(-34, 64); ctx.moveTo(34, 64); ctx.lineTo(66, 64); ctx.stroke();
  for (const yy of [-40, 10]) {
    ctx.save(); rr(-80, yy, 160, 34, 6); ctx.clip();
    ctx.fillStyle = COL.white; ctx.fillRect(-80, yy, 160, 34);
    ctx.fillStyle = '#F2A900';
    for (let i = -100; i < 100; i += 36) { ctx.beginPath(); ctx.moveTo(i, yy + 34); ctx.lineTo(i + 18, yy + 34); ctx.lineTo(i + 36, yy); ctx.lineTo(i + 18, yy); ctx.fill(); }
    ctx.restore();
  }
  ctx.beginPath(); ctx.arc(-50, -54, 9, 0, Math.PI * 2); ctx.arc(50, -54, 9, 0, Math.PI * 2); ctx.fillStyle = '#FF5A3C'; ctx.fill();
  ctx.restore();
}
function iconWhiteHouse(cx, cy, s, glow = 0) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  shadow(20 + glow * 20, .6, 0); ctx.shadowColor = 'rgba(255,255,255,.35)';
  ctx.fillStyle = COL.white;
  ctx.fillRect(-60, -6, 120, 44);
  ctx.beginPath(); ctx.moveTo(-26, -6); ctx.lineTo(0, -30); ctx.lineTo(26, -6); ctx.fill();
  noShadow();
  ctx.fillStyle = COL.navy;
  for (let i = -18; i <= 18; i += 12) ctx.fillRect(i - 2, 2, 4, 30);
  for (const sx of [-50, -38, 34, 46]) ctx.fillRect(sx, 6, 6, 10);
  ctx.fillStyle = COL.white; ctx.fillRect(-1.5, -52, 3, 24);
  ctx.fillStyle = COL.red; ctx.fillRect(1.5, -52, 16, 9);
  ctx.restore();
}
function iconMagnifier(cx, cy, s, p = 1, qp = 1) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100);
  ctx.lineCap = 'round';
  ctx.lineWidth = 16; ctx.strokeStyle = COL.white;
  ctx.beginPath(); ctx.arc(-10, -10, 54, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * p); ctx.stroke();
  if (p > .2) {
    ctx.fillStyle = COL.navy3; ctx.beginPath(); ctx.arc(-10, -10, 46, 0, Math.PI * 2); ctx.globalAlpha *= clamp((p - .2) / .3); ctx.fill(); ctx.globalAlpha = 1;
  }
  const hp = clamp((p - .6) / .4);
  ctx.strokeStyle = COL.red; ctx.lineWidth = 24;
  ctx.beginPath(); ctx.moveTo(30, 30); ctx.lineTo(30 + 42 * hp, 30 + 42 * hp); ctx.stroke();
  if (qp > 0) {
    ctx.save(); ctx.translate(-10, -10); ctx.scale(back(qp), back(qp));
    ctx.font = FD(900, 80); ctx.fillStyle = COL.red; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText('?', 0, 4); ctx.restore();
  }
  ctx.restore();
}
function arrowRight(x0, y, x1, p, col = COL.red) {
  if (p <= 0) return;
  const xe = lerp(x0, x1, eo(p));
  ctx.save(); ctx.strokeStyle = col; ctx.fillStyle = col; ctx.lineWidth = 12; ctx.lineCap = 'round';
  ctx.setLineDash([22, 16]); ctx.lineDashOffset = -p * 60;
  ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(xe - 20, y); ctx.stroke(); ctx.setLineDash([]);
  ctx.beginPath(); ctx.moveTo(xe + 14, y); ctx.lineTo(xe - 26, y - 28); ctx.lineTo(xe - 26, y + 28); ctx.closePath(); ctx.fill();
  ctx.restore();
}

// ---------- mapa (proyección local en metros) ----------
const LAT0 = 38.875, LON0 = -77.03, MX = 86450, MY = 111000;
const P = (lon, lat) => [(lon - LON0) * MX, -(lat - LAT0) * MY];
const PL = a => a.map(([lon, lat]) => P(lon, lat));
let cam = { x: 0, y: 0, s: .1, ax: 540, ay: 640 };
const S = p => [(p[0] - cam.x) * cam.s + cam.ax, (p[1] - cam.y) * cam.s + cam.ay];

const GEO = {
  potomac: PL([[-77.125, 38.930], [-77.108, 38.918], [-77.092, 38.910], [-77.078, 38.905], [-77.069, 38.901], [-77.063, 38.896],
    [-77.058, 38.890], [-77.0535, 38.884], [-77.049, 38.878], [-77.0445, 38.8715], [-77.040, 38.865], [-77.034, 38.857],
    [-77.0285, 38.849], [-77.0265, 38.840], [-77.026, 38.830], [-77.030, 38.816], [-77.036, 38.802], [-77.040, 38.785], [-77.042, 38.760]]),
  potW: [380, 400, 420, 430, 440, 470, 520, 560, 600, 680, 780, 880, 980, 1050, 1100, 1150, 1200, 1250, 1300],
  anacostia: PL([[-77.025, 38.855], [-77.0175, 38.8622], [-77.012, 38.8658], [-77.006, 38.8688], [-76.999, 38.8705], [-76.990, 38.8722],
    [-76.979, 38.8742], [-76.970, 38.878], [-76.962, 38.885], [-76.955, 38.893], [-76.948, 38.903], [-76.940, 38.913], [-76.930, 38.925]]),
  channel: PL([[-77.0345, 38.8820], [-77.0300, 38.8790], [-77.0252, 38.8760], [-77.0226, 38.8725], [-77.0215, 38.8680], [-77.0212, 38.8620], [-77.0225, 38.8565]]),
  tidal: P(-77.0375, 38.8835),
  roosevelt: P(-77.0645, 38.8968),
  mall: PL([[-77.0502, 38.8893], [-77.0091, 38.8899]]),
  roads: [
    PL([[-77.004, 38.820], [-77.003, 38.835], [-77.002, 38.851], [-76.995, 38.862], [-76.985, 38.866], [-76.975, 38.871], [-76.962, 38.878]]),
    PL([[-77.075, 38.858], [-77.062, 38.862], [-77.050, 38.869], [-77.0415, 38.876], [-77.030, 38.880], [-77.018, 38.881], [-77.008, 38.8795], [-76.995, 38.878], [-76.985, 38.877]]),
    PL([[-77.0365, 38.8977], [-77.0091, 38.8899], [-76.985, 38.880], [-76.960, 38.868]]),
    PL([[-77.0365, 38.8977], [-77.0365, 38.960]]),
    PL([[-77.0502, 38.8893], [-77.0640, 38.8818], [-77.0700, 38.8790]]),
    PL([[-77.070, 38.905], [-77.062, 38.891], [-77.057, 38.884], [-77.053, 38.874], [-77.047, 38.862], [-77.044, 38.845], [-77.045, 38.820]]),
    PL([[-77.120, 38.884], [-77.090, 38.884], [-77.080, 38.8835]]),
    PL([[-77.0091, 38.8899], [-77.0091, 38.960]]),
    PL([[-77.0091, 38.8899], [-77.0080, 38.870]]),
  ],
  dc: PL([[-77.0410, 38.9955], [-76.9094, 38.8929], [-77.0390, 38.7908]]),
  pentagon: P(-77.0563, 38.8719),
  wh: P(-77.0365, 38.8977),
  capitol: P(-77.0091, 38.8899),
};
const BASES = {
  mcnair: { poly: PL([[-77.0199, 38.8783], [-77.0130, 38.8783], [-77.0147, 38.8738], [-77.0147, 38.8676], [-77.0170, 38.8656], [-77.0193, 38.8668]]), pin: P(-77.0168, 38.8712), short: 'FORT McNAIR' },
  jbab: { poly: PL([[-77.0168, 38.8592], [-77.0060, 38.8578], [-77.0025, 38.8480], [-77.0040, 38.8340], [-77.0110, 38.8250], [-77.0188, 38.8280], [-77.0197, 38.8400], [-77.0195, 38.8520]]), pin: P(-77.0112, 38.8445), short: 'ANACOSTIA-BOLLING' },
  myer: { poly: PL([[-77.0895, 38.8862], [-77.0762, 38.8866], [-77.0748, 38.8802], [-77.0792, 38.8762], [-77.0895, 38.8772]]), pin: P(-77.0825, 38.8818), short: 'MYER-HENDERSON HALL' },
};
const CEM = { poly: PL([[-77.0748, 38.8862], [-77.0640, 38.8842], [-77.0605, 38.8772], [-77.0652, 38.8705], [-77.0762, 38.8722], [-77.0792, 38.8762], [-77.0748, 38.8802]]), c: P(-77.0690, 38.8785) };

function strokePath(pts) { ctx.beginPath(); pts.forEach((p, i) => { const s = S(p); i ? ctx.lineTo(s[0], s[1]) : ctx.moveTo(s[0], s[1]); }); }
function polyLen(pts) { let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); return L; }
function centroid(pts) { let x = 0, y = 0; pts.forEach(p => { x += p[0]; y += p[1]; }); return [x / pts.length, y / pts.length]; }

function drawRiver(pts, widths, col) {
  ctx.strokeStyle = col; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  for (let i = 1; i < pts.length; i++) {
    const w = Array.isArray(widths) ? (widths[i - 1] + widths[i]) / 2 : widths;
    ctx.lineWidth = Math.max(2, w * cam.s);
    const a = S(pts[i - 1]), b = S(pts[i]);
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
  }
}
function mapLabel(text, lonlatP, size, col, angle = 0, spacing = 6, weight = 700, italic = false) {
  const s = S(lonlatP);
  ctx.save(); ctx.translate(s[0], s[1]); ctx.rotate(angle);
  ctx.font = `${italic ? 'italic ' : ''}${weight} ${size}px "Inter"`; ctx.letterSpacing = spacing + 'px';
  ctx.fillStyle = col; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, 0); ctx.restore();
}

function drawMap(t) {
  ctx.fillStyle = COL.land; ctx.fillRect(0, 0, W, H);
  // retícula de calles
  const step = 320;
  const x0 = cam.x - cam.ax / cam.s, x1 = cam.x + (W - cam.ax) / cam.s;
  const y0 = cam.y - cam.ay / cam.s, y1 = cam.y + (H - cam.ay) / cam.s;
  if (step * cam.s > 9) {
    ctx.strokeStyle = 'rgba(120,165,230,.075)'; ctx.lineWidth = 1.5; ctx.beginPath();
    for (let gx = Math.floor(x0 / step) * step; gx < x1; gx += step) { const sx = (gx - cam.x) * cam.s + cam.ax; ctx.moveTo(sx, 0); ctx.lineTo(sx, H); }
    for (let gy = Math.floor(y0 / step) * step; gy < y1; gy += step) { const sy = (gy - cam.y) * cam.s + cam.ay; ctx.moveTo(0, sy); ctx.lineTo(W, sy); }
    ctx.stroke();
  }
  // Mall
  ctx.strokeStyle = 'rgba(64,120,96,.35)'; ctx.lineWidth = 320 * cam.s; ctx.lineCap = 'butt'; strokePath(GEO.mall); ctx.stroke();
  // vías principales
  ctx.strokeStyle = 'rgba(150,185,235,.22)'; ctx.lineWidth = Math.max(1.5, 40 * cam.s); ctx.lineCap = 'round';
  GEO.roads.forEach(r => { strokePath(r); ctx.stroke(); });
  // Pentágono
  const pg = S(GEO.pentagon); ctx.beginPath();
  for (let i = 0; i < 5; i++) { const a = -Math.PI / 2 + i * 2 * Math.PI / 5; ctx.lineTo(pg[0] + Math.cos(a) * 230 * cam.s, pg[1] + Math.sin(a) * 230 * cam.s); }
  ctx.closePath(); ctx.fillStyle = 'rgba(150,185,235,.16)'; ctx.fill();
  // agua: halo + cauce
  for (const pass of [0, 1]) {
    const col = pass ? COL.water : 'rgba(60,120,200,.28)';
    const extra = pass ? 0 : 160;
    drawRiver(GEO.potomac, GEO.potW.map(w => w + extra), col);
    drawRiver(GEO.anacostia, 330 + extra, col);
    drawRiver(GEO.channel, 170 + extra, col);
    const tb = S(GEO.tidal); ctx.beginPath(); ctx.arc(tb[0], tb[1], (300 + extra / 2) * cam.s, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill();
  }
  // isla Roosevelt
  const ri = S(GEO.roosevelt); ctx.save(); ctx.translate(ri[0], ri[1]); ctx.rotate(-.6);
  ctx.beginPath(); ctx.ellipse(0, 0, 150 * cam.s, 420 * cam.s, 0, 0, Math.PI * 2); ctx.fillStyle = COL.land; ctx.fill(); ctx.restore();
  // límite del D.C.
  ctx.save(); ctx.setLineDash([14, 12]); ctx.strokeStyle = 'rgba(200,215,240,.35)'; ctx.lineWidth = 3; strokePath(GEO.dc); ctx.stroke(); ctx.restore();
  // etiquetas
  const ls = clamp(cam.s * 260, 20, 40);
  mapLabel('WASHINGTON D.C.', P(-77.000, 38.902), clamp(cam.s * 420, 26, 60), 'rgba(220,232,250,.55)', 0, 10, 800);
  mapLabel('ARLINGTON, VIRGINIA', P(-77.098, 38.868), clamp(cam.s * 330, 22, 46), 'rgba(220,232,250,.45)', 0, 8, 800);
  mapLabel('RÍO POTOMAC', P(-77.0375, 38.8615), ls, '#7FAAE0', 1.03, 5, 700, true);
  mapLabel('RÍO ANACOSTIA', P(-76.9845, 38.8726), ls * .9, '#7FAAE0', -0.23, 5, 700, true);
}

// polígono de base resaltado (trazo que se dibuja + relleno + pulso)
function drawBase(key, p, t, col = COL.red, glow = true) {
  if (p <= 0) return;
  const pts = BASES[key] ? BASES[key].poly : key;
  const sp = pts.map(S);
  ctx.save();
  ctx.beginPath(); sp.forEach((s, i) => i ? ctx.lineTo(s[0], s[1]) : ctx.moveTo(s[0], s[1])); ctx.closePath();
  const fillA = clamp((p - .5) * 2) * (.38 + .12 * Math.sin(t * 5));
  ctx.fillStyle = col === COL.red ? `rgba(227,38,60,${fillA})` : col; ctx.fill();
  let L = 0; for (let i = 0; i < sp.length; i++) { const a = sp[i], b = sp[(i + 1) % sp.length]; L += Math.hypot(b[0] - a[0], b[1] - a[1]); }
  ctx.setLineDash([L * clamp(p * 1.6), L]);
  if (glow) { ctx.shadowColor = 'rgba(255,60,80,.9)'; ctx.shadowBlur = 24; }
  ctx.strokeStyle = COL.red; ctx.lineWidth = 6; ctx.lineJoin = 'round'; ctx.stroke();
  ctx.restore();
}
function pinDrop(pt, t0, t, size = 90, q = false) {
  const p = prog(t, t0, .5); if (p <= 0) return null;
  const s = S(pt);
  const yOff = (1 - eo(p)) * -260;
  // ondas
  const rp = ((t - t0) % 1.6) / 1.6;
  if (p >= 1) {
    ctx.save(); ctx.strokeStyle = `rgba(227,38,60,${(1 - rp) * .8})`; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.ellipse(s[0], s[1], 20 + rp * 90, (20 + rp * 90) * .45, 0, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
  }
  ctx.save(); ctx.globalAlpha *= clamp(p * 3);
  const sq = p < 1 ? 1 : 1 + .12 * Math.exp(-(t - t0 - .5) * 8) * Math.sin((t - t0 - .5) * 30);
  ctx.translate(s[0], s[1] + yOff); ctx.scale(1 / sq, sq); iconPin(0, 0, size, '', COL.red, q); ctx.restore();
  return s;
}
function mapTag(text, s, t0, t, side = 1, dy = -110, size = 36) {
  const p = eo(prog(t, t0, .45)); if (p <= 0) return;
  ctx.save(); ctx.font = F(900, size); ctx.letterSpacing = '2px';
  const tw = ctx.measureText(text).width + 40, th = size + 30;
  let x = side > 0 ? s[0] + 60 : s[0] - 60 - tw; const y = s[1] + dy - th / 2;
  x = clamp(x, 30, W - 30 - tw);
  ctx.globalAlpha *= p;
  ctx.strokeStyle = COL.white; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(s[0], s[1] - 60); ctx.lineTo(side > 0 ? x : x + tw, y + th / 2); ctx.stroke();
  shadow(16, .5, 6); ctx.fillStyle = COL.red; ctx.fillRect(x, y, tw * p, th); noShadow();
  ctx.beginPath(); ctx.rect(x, y, tw * p, th); ctx.clip();
  ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText(text, x + 20, y + th / 2 + 2);
  ctx.restore();
}

// cámara del mapa por fotogramas clave
function camKeys() {
  const mc = centroid(BASES.mcnair.poly), jb = centroid(BASES.jbab.poly), my = [(BASES.myer.pin[0] + CEM.c[0]) / 2, (BASES.myer.pin[1] + CEM.c[1]) / 2];
  const wide = P(-77.034, 38.874);
  return [
    [T.s4 - .3, wide, .072],
    [T.s4 + .4, wide, .078],
    [T.mcnair, [mc[0], mc[1] + 120], .30],
    [T.s5 + .05, [mc[0], mc[1] + 120], .315],
    [T.s5 + 1.5, jb, .215],
    [T.s6 - .05, jb, .225],
    [T.s6 + 1.6, my, .205],
    [T.s7 - .05, my, .215],
    [T.s7 + 1.4, P(-77.040, 38.873), .082],
    [T.s8 + 1, P(-77.040, 38.873), .086],
  ];
}
function camAt(t) {
  const K = camKeys();
  if (t <= K[0][0]) return { x: K[0][1][0], y: K[0][1][1], s: K[0][2] };
  for (let i = 1; i < K.length; i++) {
    if (t <= K[i][0]) {
      const a = K[i - 1], b = K[i]; const p = eio((t - a[0]) / (b[0] - a[0]));
      const travel = Math.hypot(b[1][0] - a[1][0], b[1][1] - a[1][1]);
      const bump = travel > 1500 ? 1 - .28 * Math.sin(Math.PI * p) : 1;
      return { x: lerp(a[1][0], b[1][0], p), y: lerp(a[1][1], b[1][1], p), s: Math.exp(lerp(Math.log(a[2]), Math.log(b[2]), p)) * bump };
    }
  }
  const L = K[K.length - 1]; return { x: L[1][0], y: L[1][1], s: L[2] };
}

// ---------- subtítulos palabra por palabra ----------
function buildChunks() {
  CH = []; let cur = [];
  const len = c => c.reduce((a, w) => a + w[0].length + 1, 0);
  WORDS.forEach((w, i) => {
    const prev = WORDS[i - 1];
    const brk = cur.length && (cur.length >= 4 || len(cur) + w[0].length > 20 || /[.,?:]$/.test(prev[0]) || w[1] - prev[2] > .45);
    if (brk) { CH.push(cur); cur = []; }
    cur.push(w);
  });
  if (cur.length) CH.push(cur);
}
function drawSubs(t) {
  if (t >= T.s3 - .05 && t < T.s4 - .05) return;
  let idx = -1;
  for (let i = 0; i < CH.length; i++) {
    const st = CH[i][0][1] - .05, en = i + 1 < CH.length ? Math.min(CH[i + 1][0][1] - .05, CH[i][CH[i].length - 1][2] + .8) : CH[i][CH[i].length - 1][2] + .8;
    if (t >= st && t < en) { idx = i; break; }
  }
  if (idx < 0) return;
  const ch = CH[idx];
  const size = 66;
  ctx.save(); ctx.font = F(900, size); ctx.textBaseline = 'middle';
  const words = ch.map(w => w[0].toUpperCase());
  const sp = 18, maxW = 960;
  const ws = words.map(w => ctx.measureText(w).width);
  // reparto en líneas
  const lines = [[]]; let lw = 0;
  ws.forEach((w, i) => { if (lw + w > maxW && lines[lines.length - 1].length) { lines.push([]); lw = 0; } lines[lines.length - 1].push(i); lw += w + sp; });
  const lh = size + 22, y0 = 300 - (lines.length - 1) * lh / 2;
  lines.forEach((ln, li) => {
    const tot = ln.reduce((a, i) => a + ws[i], 0) + sp * (ln.length - 1);
    let x = W / 2 - tot / 2; const y = y0 + li * lh;
    ln.forEach(i => {
      const w = ch[i]; const appear = prog(t, w[1] - .04, .12);
      const nextStart = i + 1 < ch.length ? ch[i + 1][1] : w[2] + .15;
      const active = t >= w[1] - .04 && t < Math.max(w[2], nextStart - .02);
      if (appear > 0) {
        ctx.save(); ctx.translate(x + ws[i] / 2, y);
        const sc = active ? 1 + .1 * (1 - eo(prog(t, w[1] - .04, .18))) + .04 : .94 + .06 * eo(appear);
        ctx.scale(sc, sc); ctx.globalAlpha = appear;
        if (active) { shadow(18, .5, 6); rr(-ws[i] / 2 - 12, -size / 2 - 8, ws[i] + 24, size + 16, 10); ctx.fillStyle = COL.red; ctx.fill(); noShadow(); }
        ctx.textAlign = 'center';
        if (!active) { shadow(14, .85, 4); }
        ctx.lineWidth = 8; ctx.strokeStyle = 'rgba(5,14,29,.55)'; ctx.lineJoin = 'round';
        if (!active) ctx.strokeText(words[i], 0, 3);
        noShadow(); ctx.fillStyle = COL.white; ctx.fillText(words[i], 0, 3);
        ctx.restore();
      }
      x += ws[i] + sp;
    });
  });
  ctx.restore();
}

// ---------- capas globales ----------
function topBand() {
  const g = ctx.createLinearGradient(0, 0, 0, 470);
  g.addColorStop(0, 'rgba(4,10,22,.88)'); g.addColorStop(.6, 'rgba(4,10,22,.5)'); g.addColorStop(1, 'rgba(4,10,22,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, 470);
}
function brandBug(t) {
  ctx.save(); ctx.globalAlpha = .92;
  iconMagnifier(84, 128, 40, 1, 1);
  ctx.font = F(900, 28); ctx.letterSpacing = '5px'; ctx.fillStyle = COL.white; ctx.textBaseline = 'middle';
  ctx.fillText('CAPITAL', 128, 116); ctx.fillStyle = COL.red; ctx.fillText('CURIOSO', 128, 148);
  ctx.restore();
}
function sources(t) {
  let s = null;
  if (t >= T.s2 && t < T.s3) s = 'Fuente: Reuters';
  else if (t >= T.s4 && t < T.s5) s = 'Fuente: The New York Times';
  else if (t >= T.s5 && t < T.s8) s = 'Fuentes: The Atlantic · Fox News';
  else if (t >= T.s8 && t < T.s10) s = 'Fuentes: The New York Times · Reuters · The Atlantic · Fox News';
  if (!s) return;
  ctx.save(); ctx.font = F(600, 23); ctx.letterSpacing = '1px'; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  const tw = ctx.measureText(s).width;
  ctx.fillStyle = 'rgba(4,10,22,.6)'; rr(44, 1712, tw + 44, 46, 8); ctx.fill();
  ctx.fillStyle = COL.red; ctx.fillRect(44, 1712, 6, 46);
  ctx.fillStyle = 'rgba(225,235,250,.88)'; ctx.fillText(s, 66, 1736); ctx.restore();
}
function vignette() {
  const g = ctx.createRadialGradient(W / 2, H / 2, H * .3, W / 2, H / 2, H * .75);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.55)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function grain(t) {
  const c = GRAIN[Math.floor(t * 30) % GRAIN.length];
  ctx.save(); ctx.globalAlpha = .045; ctx.globalCompositeOperation = 'overlay';
  ctx.drawImage(c, 0, 0, W, H); ctx.restore();
}
function wipe(t) {
  const cuts = [T.s2, T.s4, T.s8, T.s9, T.s10, T.s11];
  const D = .3;
  for (const c of cuts) {
    if (t < c - D || t > c + D) continue;
    const p = (t - (c - D)) / (2 * D);
    ctx.save();
    const sk = 220;
    let L, R;
    if (p < .5) { const q = eio(p * 2); L = lerp(W + sk, -sk, q); R = W + sk + 300; }
    else { const q = eio((p - .5) * 2); L = -sk - 300; R = lerp(W + sk, -sk, q); }
    ctx.beginPath(); ctx.moveTo(L + sk, 0); ctx.lineTo(R + sk, 0); ctx.lineTo(R - sk, H); ctx.lineTo(L - sk, H); ctx.closePath();
    ctx.fillStyle = COL.navy; ctx.fill();
    // borde rojo
    ctx.fillStyle = COL.red;
    const E = p < .5 ? L : R, dir = p < .5 ? -1 : 1;
    ctx.beginPath(); ctx.moveTo(E + sk, 0); ctx.lineTo(E + sk + dir * 34, 0); ctx.lineTo(E - sk + dir * 34, H); ctx.lineTo(E - sk, H); ctx.closePath(); ctx.fill();
    if (Math.abs(p - .5) < .22) { ctx.globalAlpha = 1 - Math.abs(p - .5) / .22; iconMagnifier(W / 2, H / 2, 160, 1, 1); }
    ctx.restore();
  }
}

// ---------- ESCENA 1: gancho ----------
function scene1(t) {
  drawKB(BG.casa, t, 0, T.s2, 1.06, 1.2, 0, 40);
  ctx.fillStyle = 'rgba(6,16,36,.45)'; ctx.fillRect(0, 0, W, H);
  const g = ctx.createLinearGradient(0, 500, 0, 1700); g.addColorStop(0, 'rgba(5,14,29,.2)'); g.addColorStop(1, 'rgba(5,14,29,.9)');
  ctx.fillStyle = g; ctx.fillRect(0, 500, W, 1200);
  // kicker
  const kp = eo(prog(t, .1, .5));
  ctx.save(); ctx.globalAlpha = kp; ctx.fillStyle = COL.red; ctx.fillRect(90, 600, 120 * kp, 8);
  ctx.font = F(800, 30); ctx.letterSpacing = '6px'; ctx.fillStyle = COL.white; ctx.fillText('WASHINGTON, D.C.', 230, 614); ctx.restore();
  const lines = [['¿POR QUÉ YA NO', COL.white], ['DUERMEN EN', COL.white], ['SUS CASAS?', COL.red]];
  lines.forEach(([txt, col], i) => {
    const p = prog(t, .15 + i * .14, .45); if (p <= 0) return;
    ctx.save(); ctx.font = FD(900, 118); ctx.textAlign = 'left';
    const y = 760 + i * 128;
    ctx.beginPath(); ctx.rect(0, y - 120, W, 150); ctx.clip();
    ctx.translate(0, (1 - eo5(p)) * 130);
    shadow(30, .6, 8); ctx.fillStyle = col; ctx.fillText(txt, 84, y); ctx.restore();
  });
  // ícono casa -> tachado -> base militar
  const cx = W / 2, cy = 1300;
  const ip = eo(prog(t, .5, .5));
  const xT = 1.75, mT = 2.85;
  const swap = prog(t, mT, .35);
  ctx.save(); ctx.globalAlpha = ip;
  shadow(30, .6, 0);
  ctx.beginPath(); ctx.arc(cx, cy, 150, 0, Math.PI * 2); ctx.fillStyle = 'rgba(10,26,51,.85)'; ctx.fill(); noShadow();
  ctx.lineWidth = 5; ctx.strokeStyle = swap > .5 ? COL.red : 'rgba(255,255,255,.4)'; ctx.stroke();
  if (swap < .5) {
    const sx = Math.cos(swap * Math.PI);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(sx, 1); iconHouse(0, 0, 160); ctx.restore();
    // X roja
    const xp = prog(t, xT, .35);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(sx, 1);
    ctx.strokeStyle = COL.red; ctx.lineWidth = 18; ctx.lineCap = 'round';
    const a = eo(clamp(xp * 2)), b = eo(clamp(xp * 2 - 1));
    ctx.beginPath(); ctx.moveTo(-95, -95); ctx.lineTo(-95 + 190 * a, -95 + 190 * a); ctx.stroke();
    if (b > 0) { ctx.beginPath(); ctx.moveTo(95, -95); ctx.lineTo(95 - 190 * b, -95 + 190 * b); ctx.stroke(); }
    ctx.restore();
  } else {
    const sx = -Math.cos(swap * Math.PI);
    ctx.save(); ctx.translate(cx, cy); ctx.scale(sx * (1 + .15 * Math.exp(-(t - mT - .35) * 6)), 1); iconBase(0, 6, 170, COL.white, COL.red, t * 6); ctx.restore();
  }
  ctx.restore();
  // etiqueta del ícono
  const lp = eo(prog(t, mT + .3, .4));
  if (lp > 0) {
    ctx.save(); ctx.globalAlpha = lp; ctx.font = F(900, 36); ctx.letterSpacing = '6px'; ctx.textAlign = 'center'; ctx.fillStyle = COL.white;
    ctx.fillText('AHORA: BASES MILITARES', cx, cy + 210 + (1 - lp) * 20); ctx.restore();
  }
}

// ---------- ESCENA 2: Bessent ----------
function scene2(t) {
  const t0 = T.s2;
  drawKB(BG.tesoro, t, t0, T.s3 - t0, 1.05, 1.15, -30, 0);
  ctx.fillStyle = 'rgba(5,14,29,.55)'; ctx.fillRect(0, 0, W, H);
  // foto principal
  const fp = eo(prog(t, t0 + .1, .6));
  const fx = 60, fy = 420, fw = 960, fh = 590;
  ctx.save(); ctx.globalAlpha = fp; ctx.translate(W / 2, fy + fh / 2); ctx.scale(lerp(1.08, 1, fp), lerp(1.08, 1, fp)); ctx.translate(-W / 2, -(fy + fh / 2));
  shadow(40, .7, 14); rr(fx, fy, fw, fh, 22); ctx.fillStyle = COL.navy; ctx.fill(); noShadow();
  ctx.save(); rr(fx, fy, fw, fh, 22); ctx.clip();
  drawCover(IMG.bessent, fx, fy, fw, fh, .44, .22, 1.18 + .08 * prog(t, t0, 12));
  const g = ctx.createLinearGradient(0, fy + fh - 260, 0, fy + fh); g.addColorStop(0, 'rgba(5,14,29,0)'); g.addColorStop(1, 'rgba(5,14,29,.8)');
  ctx.fillStyle = g; ctx.fillRect(fx, fy + fh - 260, fw, 260);
  ctx.restore();
  rr(fx, fy, fw, fh, 22); ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 2; ctx.stroke();
  ctx.restore();
  lowerThird('SCOTT BESSENT', 'Secretario del Tesoro', 60, 880, T.b_name, t);
  // fila de íconos: casa -> flecha -> base
  const out = eo(prog(t, T.b_quote - .1, .45));
  ctx.save(); ctx.globalAlpha = 1 - out; ctx.translate(-out * 300, 0);
  const rowY = 1250;
  const hp = back(prog(t, T.b_house, .45));
  if (hp > 0) {
    ctx.save(); ctx.translate(230, rowY); ctx.scale(hp, hp);
    ctx.beginPath(); ctx.arc(0, 0, 120, 0, Math.PI * 2); ctx.fillStyle = 'rgba(10,26,51,.9)'; ctx.fill();
    ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,.3)'; ctx.stroke(); iconHouse(0, 0, 130); ctx.restore();
  }
  const wl = eo(prog(t, T.b_wash, .4));
  if (wl > 0) { ctx.save(); ctx.globalAlpha *= wl; ctx.font = F(900, 32); ctx.letterSpacing = '4px'; ctx.textAlign = 'center'; ctx.fillStyle = COL.white; ctx.fillText('WASHINGTON', 230, rowY + 170); ctx.font = F(600, 24); ctx.fillStyle = COL.mute; ctx.fillText('su residencia', 230, rowY + 204); ctx.restore(); }
  arrowRight(380, rowY, 690, prog(t, T.b_arrow, .5));
  const bp = back(prog(t, T.b_base, .45));
  if (bp > 0) {
    ctx.save(); ctx.translate(850, rowY); ctx.scale(bp, bp);
    shadow(30, .6, 0); ctx.shadowColor = 'rgba(227,38,60,.6)';
    ctx.beginPath(); ctx.arc(0, 0, 120, 0, Math.PI * 2); ctx.fillStyle = COL.redD; ctx.fill(); noShadow();
    ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(255,255,255,.5)'; ctx.stroke(); iconBase(0, 6, 130, COL.white, COL.white, t * 6); ctx.restore();
    ctx.save(); ctx.globalAlpha *= clamp(bp); ctx.font = F(900, 32); ctx.letterSpacing = '4px'; ctx.textAlign = 'center'; ctx.fillStyle = COL.white; ctx.fillText('BASE MILITAR', 850, rowY + 170); ctx.restore();
  }
  ctx.restore();
  // tarjeta de cita
  const qp = eo(prog(t, T.b_quote, .55));
  if (qp > 0) {
    const cx = 60, cy = 1085, cw = 960, chh = 520;
    ctx.save(); ctx.globalAlpha = qp; ctx.translate((1 - qp) * 260, 0);
    shadow(40, .6, 14); rr(cx, cy, cw, chh, 20); ctx.fillStyle = 'rgba(12,30,58,.96)'; ctx.fill(); noShadow();
    ctx.fillStyle = COL.red; ctx.fillRect(cx, cy + 24, 10, chh - 48);
    ctx.font = F(900, 28); ctx.letterSpacing = '6px'; ctx.fillStyle = COL.red; ctx.fillText('LA RAZÓN', cx + 50, cy + 64); ctx.letterSpacing = '0px';
    // chip amenaza
    const tp = eo(prog(t, T.b_threat, .4));
    if (tp > 0) {
      ctx.save(); ctx.font = F(900, 34); ctx.letterSpacing = '1px';
      const txt = 'AMENAZAS DE MUERTE DESDE IRÁN'; const tw = ctx.measureText(txt).width + 100;
      rr(cx + 44, cy + 92, tw * tp, 70, 12); ctx.fillStyle = COL.red; ctx.fill();
      ctx.beginPath(); ctx.rect(cx + 44, cy + 92, tw * tp, 70); ctx.clip();
      // ícono de alerta
      ctx.fillStyle = COL.white; ctx.beginPath(); ctx.moveTo(cx + 82, cy + 108); ctx.lineTo(cx + 102, cy + 144); ctx.lineTo(cx + 62, cy + 144); ctx.closePath(); ctx.fill();
      ctx.fillStyle = COL.red; ctx.fillRect(cx + 80, cy + 118, 4, 14); ctx.fillRect(cx + 80, cy + 136, 4, 4);
      ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText(txt, cx + 120, cy + 129); ctx.restore();
    }
    // cita
    const qq = prog(t, T.b_iran + .1, .6);
    if (qq > 0) {
      ctx.save(); ctx.globalAlpha *= eo(qq);
      ctx.font = FD(900, 150); ctx.fillStyle = 'rgba(227,38,60,.9)'; ctx.fillText('“', cx + 36, cy + 300);
      ctx.font = `italic 700 46px "Inter"`; ctx.fillStyle = COL.white;
      const lines = wrap('No se dejará intimidar por las amenazas del régimen iraní”', cw - 190);
      lines.forEach((l, i) => ctx.fillText(l, cx + 130, cy + 246 + i * 60 + (1 - eo(qq)) * 20));
      ctx.font = F(600, 27); ctx.fillStyle = COL.mute;
      const ay = cy + 246 + lines.length * 60 + 20;
      ctx.fillText('— Vocero del Departamento del Tesoro', cx + 130, ay);
      ctx.fillStyle = COL.mute2; ctx.fillText('(vía Reuters)', cx + 130, ay + 38);
      ctx.restore();
    }
    ctx.restore();
  }
  // sello
  const sp = prog(t, T.b_stamp - .05, .3);
  if (sp > 0) {
    const sc = lerp(2.4, 1, eo5(sp));
    ctx.save(); ctx.translate(800, 965); ctx.rotate(-.12); ctx.scale(sc, sc); ctx.globalAlpha = clamp(sp * 2);
    ctx.font = F(900, 30); ctx.letterSpacing = '3px';
    const l1 = 'CONFIRMADO POR', l2 = 'EL PROPIO BESSENT';
    const tw = Math.max(ctx.measureText(l1).width, ctx.measureText(l2).width) + 56;
    ctx.fillStyle = 'rgba(10,20,40,.55)'; rr(-tw / 2, -62, tw, 124, 10); ctx.fill();
    ctx.strokeStyle = COL.red; ctx.lineWidth = 6; rr(-tw / 2, -62, tw, 124, 10); ctx.stroke();
    ctx.lineWidth = 2; rr(-tw / 2 + 9, -53, tw - 18, 106, 6); ctx.stroke();
    ctx.fillStyle = COL.red; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(l1, 0, -18); ctx.fillText(l2, 0, 22);
    ctx.restore();
  }
}

// ---------- ESCENA 3: "PERO NO ES EL ÚNICO" ----------
function scene3(t) {
  const t0 = T.s3;
  ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, W, H);
  // mosaico oscuro de los demás
  const keys = ['rubio', 'hegseth', 'noem', 'driscoll', 'miller', 'bondi', 'blanche', 'rubio', 'hegseth'];
  const flick = .14 + .06 * Math.sin(t * 40);
  ctx.save(); ctx.globalAlpha = flick * eo(prog(t, t0, .3)); ctx.filter = 'grayscale(1) contrast(1.2)';
  for (let i = 0; i < 9; i++) {
    const k = keys[i], gx = (i % 3) * 360, gy = 300 + Math.floor(i / 3) * 440;
    drawCover(IMG[k], gx, gy, 360, 440, PEOPLE[k].f[0], PEOPLE[k].f[1], PEOPLE[k].z);
  }
  ctx.restore(); ctx.filter = 'none';
  const rg = ctx.createRadialGradient(W / 2, H / 2, 50, W / 2, H / 2, 900);
  rg.addColorStop(0, 'rgba(160,18,40,.55)'); rg.addColorStop(1, 'rgba(5,14,29,.95)');
  ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
  const p = prog(t, t0 + .08, .22);
  const shake = Math.exp(-(t - t0 - .3) * 5) * (t > t0 + .3 ? 1 : 0);
  ctx.save(); ctx.translate(W / 2 + Math.sin(t * 90) * 16 * shake, 960 + Math.cos(t * 77) * 12 * shake);
  const sc = lerp(1.9, 1, eo5(p)); ctx.scale(sc, sc); ctx.globalAlpha = clamp(p * 3);
  ctx.textAlign = 'center'; shadow(40, .7, 10);
  ctx.font = FD(900, 150); ctx.fillStyle = COL.white; ctx.fillText('PERO NO', 0, -40);
  ctx.fillStyle = COL.red; ctx.font = FD(900, 132); ctx.fillText('ES EL ÚNICO', 0, 110);
  noShadow();
  const lp = eo(prog(t, t0 + .35, .4)); ctx.fillStyle = COL.white; ctx.fillRect(-380 * lp, 160, 760 * lp, 10);
  ctx.restore();
  // destello
  const fl = 1 - prog(t, t0 + .08, .2);
  if (t > t0 + .08 && fl > 0) { ctx.fillStyle = `rgba(255,255,255,${fl * .85})`; ctx.fillRect(0, 0, W, H); }
}

// ---------- ESCENAS 4–7: mapa ----------
function basePanel(t, which) {
  // foto de la base en la mitad inferior
  const panTop = 930;
  const photos = [
    ['fortmcnair', T.s4 - .3, T.fila], ['fortmcnair_aerea', T.fila, T.s5 + .4],
    ['anacostia', T.s5 + .4, T.s6 + .4], ['fortmyer', T.s6 + .4, T.s7 + .4],
  ];
  ctx.save();
  ctx.fillStyle = 'rgba(6,16,34,1)';
  const g0 = ctx.createLinearGradient(0, panTop - 60, 0, panTop + 160);
  g0.addColorStop(0, 'rgba(5,14,29,0)'); g0.addColorStop(1, 'rgba(5,14,29,1)');
  ctx.fillStyle = g0; ctx.fillRect(0, panTop - 60, W, 220); ctx.fillStyle = COL.bg; ctx.fillRect(0, panTop + 160, W, H);
  for (const [name, a, b] of photos) {
    const al = Math.min(prog(t, a, .5), 1 - prog(t, b, .5));
    if (al <= 0) continue;
    const img = IMG[name];
    ctx.save(); ctx.globalAlpha = al;
    ctx.beginPath(); ctx.rect(0, panTop, W, H - panTop); ctx.clip();
    if (img) {
      const z = 1 + .08 * prog(t, a, 7);
      ctx.save(); ctx.translate(W / 2, (panTop + H) / 2); ctx.scale(z, z); ctx.translate(-W / 2, -(panTop + H) / 2);
      drawCover(img, 0, panTop, W, H - panTop, .5, .5, 1); ctx.restore();
      ctx.fillStyle = 'rgba(5,14,29,.5)'; ctx.fillRect(0, panTop, W, H - panTop);
    } else {
      // respaldo si falta la foto: textura de plano
      ctx.fillStyle = COL.navy; ctx.fillRect(0, panTop, W, H - panTop);
      ctx.strokeStyle = 'rgba(120,165,230,.08)'; ctx.lineWidth = 2;
      for (let x = -H; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, H); ctx.lineTo(x + H, panTop); ctx.stroke(); }
    }
    ctx.restore();
  }
  const g = ctx.createLinearGradient(0, panTop, 0, panTop + 260);
  g.addColorStop(0, 'rgba(5,14,29,1)'); g.addColorStop(1, 'rgba(5,14,29,0)');
  ctx.fillStyle = g; ctx.fillRect(0, panTop, W, 260);
  const g2 = ctx.createLinearGradient(0, 1500, 0, H); g2.addColorStop(0, 'rgba(5,14,29,0)'); g2.addColorStop(1, 'rgba(5,14,29,.9)');
  ctx.fillStyle = g2; ctx.fillRect(0, 1500, W, H - 1500);
  ctx.restore();
}
function baseHeader(t, t0, t1, tag, title, sub, subT, col = COL.white) {
  const p = eo(prog(t, t0, .5)), q = 1 - eo(prog(t, t1 - .35, .35));
  const a = Math.min(p, q); if (a <= 0) return;
  ctx.save(); ctx.globalAlpha = a;
  ctx.font = F(900, 26); ctx.letterSpacing = '6px';
  const tw = ctx.measureText(tag).width + 36;
  ctx.fillStyle = COL.red; rr(60, 975, tw, 46, 6); ctx.fill();
  ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText(tag, 78, 999);
  ctx.textBaseline = 'alphabetic';
  ctx.letterSpacing = '0px';
  let size = 84; ctx.font = FD(900, size);
  let lines = [title];
  if (ctx.measureText(title).width > 960) { size = 64; ctx.font = FD(900, size); lines = wrap(title, 960); }
  ctx.save(); ctx.beginPath(); ctx.rect(0, 1025, W, lines.length * (size + 6) + 20); ctx.clip();
  shadow(20, .6, 6); ctx.fillStyle = col;
  lines.forEach((l, i) => ctx.fillText(l, 58, 1030 + size + i * (size + 6) + (1 - p) * 90));
  ctx.restore();
  if (sub) {
    const sp = eo(prog(t, subT, .4));
    if (sp > 0) {
      const y = 1030 + lines.length * (size + 6) + 22;
      ctx.font = F(800, 32); ctx.letterSpacing = '2px'; const sw = ctx.measureText(sub).width + 90;
      ctx.globalAlpha = a * sp;
      rr(60, y, sw * sp, 58, 29); ctx.fillStyle = 'rgba(255,255,255,.95)'; ctx.fill();
      ctx.save(); ctx.beginPath(); ctx.rect(60, y, sw * sp, 58); ctx.clip();
      star(92, y + 29, 15, COL.red);
      ctx.fillStyle = COL.navy; ctx.textBaseline = 'middle'; ctx.fillText(sub, 120, y + 31); ctx.restore();
    }
  }
  ctx.restore();
}
function infoTile(x, y, w, h, t0, t, drawIcon, text) {
  const p = eo(prog(t, t0, .55)); if (p <= 0) return;
  ctx.save(); ctx.globalAlpha *= p; ctx.translate(0, (1 - p) * 70);
  shadow(30, .6, 12); rr(x, y, w, h, 18); ctx.fillStyle = 'rgba(17,40,77,.96)'; ctx.fill(); noShadow();
  rr(x, y, w, h, 18); ctx.strokeStyle = 'rgba(227,38,60,.7)'; ctx.lineWidth = 3; ctx.stroke();
  drawIcon(x + w / 2, y + h * .36);
  ctx.font = F(800, 30); ctx.fillStyle = COL.white; ctx.textAlign = 'center';
  const lines = wrap(text, w - 50);
  lines.forEach((l, i) => ctx.fillText(l, x + w / 2, y + h * .7 + i * 38 - (lines.length - 1) * 12));
  ctx.restore();
}
function rentChip(t, t0, t1) {
  const p = eo(prog(t, t0, .5)), q = 1 - eo(prog(t, t1 - .3, .3)); const a = Math.min(p, q); if (a <= 0) return;
  const x = 60, y = 1585, w = 960, h = 96;
  ctx.save(); ctx.globalAlpha = a; ctx.translate((1 - p) * -200, 0);
  shadow(24, .6, 8); rr(x, y, w, h, 16); ctx.fillStyle = COL.white; ctx.fill(); noShadow();
  ctx.fillStyle = COL.red; rr(x, y, 210, h, 16); ctx.fill(); ctx.fillRect(x + 190, y, 20, h);
  const v = Math.round(4655 * eo(prog(t, t0 + .1, 1.1)));
  ctx.font = FD(900, 44); ctx.fillStyle = COL.white; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('$' + v.toLocaleString('en-US'), x + 105, y + h / 2 + 2);
  ctx.textAlign = 'left'; ctx.fillStyle = COL.navy; ctx.font = F(900, 30);
  ctx.fillText('Hegseth paga US$4,655 al mes', x + 236, y + 36);
  ctx.font = F(600, 26); ctx.fillStyle = '#41577A'; ctx.fillText('de alquiler en Fort McNair  ·  (NYT)', x + 236, y + 70);
  ctx.restore();
}
function mapScenes(t) {
  const c = camAt(t); cam.x = c.x; cam.y = c.y; cam.s = c.s; cam.ax = 540; cam.ay = 650;
  drawMap(t);
  // bases
  drawBase('mcnair', prog(t, T.mcnair - .2, .9), t);
  drawBase('jbab', prog(t, T.jbab - .3, .9), t);
  if (t > T.cemetery - .2) {
    const cp = prog(t, T.cemetery - .2, .7);
    ctx.save(); ctx.globalAlpha = cp; drawBase(CEM.poly, 1, t, 'rgba(255,255,255,.14)', false); ctx.restore();
  }
  drawBase('myer', prog(t, T.myer - .2, .9), t);
  // pines y etiquetas
  const unk = t > T.s7 + .8;
  if (!unk || true) {
    const s1 = pinDrop(BASES.mcnair.pin, T.mcnair, t, 86); if (s1 && t < T.s5 + .4) mapTag('FORT McNAIR', s1, T.mcnair + .3, t, 1, -120);
    const s2 = pinDrop(BASES.jbab.pin, T.jbab, t, 86); if (s2 && t < T.s6 + .4) mapTag('ANACOSTIA-BOLLING', s2, T.jbab + .3, t, 1, -120);
    const s3 = pinDrop(BASES.myer.pin, T.myer, t, 86); if (s3 && t < T.s7 + .4) mapTag('MYER-HENDERSON HALL', s3, T.myer + .3, t, 1, -150);
  }
  if (t > T.cemetery - .1) {
    const cs = S(CEM.c); const cp = back(prog(t, T.cemetery, .45));
    ctx.save(); ctx.translate(cs[0], cs[1]); ctx.scale(cp, cp);
    ctx.beginPath(); ctx.arc(0, 0, 54, 0, Math.PI * 2); ctx.fillStyle = 'rgba(10,26,51,.92)'; ctx.fill(); ctx.strokeStyle = COL.white; ctx.lineWidth = 3; ctx.stroke();
    iconHeadstone(0, -4, 60); ctx.restore();
    const lp = eo(prog(t, T.cemetery + .25, .4));
    if (lp > 0) { ctx.save(); ctx.globalAlpha = lp; ctx.font = F(800, 26); ctx.letterSpacing = '2px'; ctx.textAlign = 'center'; shadow(10, .9, 2); ctx.fillStyle = COL.white; ctx.fillText('CEMENTERIO DE ARLINGTON', cs[0], cs[1] + 90); ctx.restore(); }
  }
  // pin de base no revelada
  if (t > T.unknown - .1) {
    const qs = [cam.ax + 40, 560];
    const p = prog(t, T.unknown, .5); const yOff = (1 - eo(p)) * -300;
    const rp = ((t - T.unknown) % 1.4) / 1.4;
    ctx.save(); ctx.globalAlpha = clamp(p * 3);
    ctx.strokeStyle = `rgba(255,255,255,${(1 - rp) * .7})`; ctx.lineWidth = 4; ctx.setLineDash([10, 10]);
    ctx.beginPath(); ctx.arc(qs[0], qs[1] - 80, 60 + rp * 120, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
    iconPin(qs[0], qs[1] + yOff, 150, '', COL.red, true);
    ctx.restore();
    const lp = eo(prog(t, T.unknown + .35, .4));
    if (lp > 0) {
      ctx.save(); ctx.globalAlpha = lp; ctx.font = F(900, 44); ctx.letterSpacing = '4px'; ctx.textAlign = 'center';
      const tw = ctx.measureText('BASE NO REVELADA').width + 60;
      shadow(20, .6, 6); ctx.fillStyle = COL.white; rr(qs[0] - tw / 2, qs[1] + 30, tw, 76, 10); ctx.fill(); noShadow();
      ctx.fillStyle = COL.red; ctx.textBaseline = 'middle'; ctx.fillText('BASE NO REVELADA', qs[0], qs[1] + 70); ctx.restore();
    }
  }
  // panel inferior
  basePanel(t);
  baseHeader(t, T.mcnair, T.s5, 'BASE 1 · WASHINGTON D.C.', 'FORT McNAIR', 'FILA DE LOS GENERALES', T.fila);
  baseHeader(t, T.jbab - .2, T.s6, 'BASE 2 · WASHINGTON D.C.', 'BASE CONJUNTA ANACOSTIA-BOLLING', null);
  baseHeader(t, T.myer - .2, T.s7, 'BASE 3 · ARLINGTON, VIRGINIA', 'BASE CONJUNTA MYER-HENDERSON HALL', null);
  // tarjetas de personas
  const fadeOut = (a, b) => 1 - eo(prog(t, b - .35, .35));
  const grp = (t1, fn) => { const a = fadeOut(0, t1); if (a <= 0) return; ctx.save(); ctx.globalAlpha *= a; fn(); ctx.restore(); };
  const cy = 1240, ch = 330;
  if (t < T.s5) grp(T.s5, () => {
    personCard('rubio', 60, cy, 465, ch, T.rubio, t);
    personCard('hegseth', 555, cy, 465, ch, T.hegseth, t);
    rentChip(t, T.mcnair + .7, T.s5);
  });
  if (t >= T.s5 - .1 && t < T.s6) grp(T.s6, () => {
    personCard('noem', 60, cy + 40, 465, ch + 60, T.noem, t);
    infoTile(555, cy + 40, 465, ch + 60, T.cg_house, t, (x, y) => { iconHouse(x, y, 120); star(x + 70, y - 40, 18, COL.red); }, 'Residencia del comandante de la Guardia Costera');
  });
  if (t >= T.s6 - .1 && t < T.s7) grp(T.s7, () => {
    personCard('driscoll', 60, cy + 70, 465, ch + 40, T.driscoll, t);
    infoTile(555, cy + 70, 465, ch + 40, T.cemetery, t, (x, y) => iconHeadstone(x, y, 110), 'Junto al Cementerio Nacional de Arlington');
  });
  if (t >= T.s7 - .1) {
    const cw = 300, ch2 = 420, y = 1150;
    personCard('miller', 60, y, cw, ch2, T.miller, t, { nameSize: 28, cargoSize: 21, barH: 150 });
    personCard('bondi', 390, y, cw, ch2, T.bondi, t, { nameSize: 28, cargoSize: 21, barH: 150 });
    personCard('blanche', 720, y, cw, ch2, T.blanche, t, { nameSize: 28, cargoSize: 21, barH: 150 });
    // sello de interrogación sobre las tarjetas
    const qp = eo(prog(t, T.unknown + .2, .4));
    if (qp > 0) {
      ctx.save(); ctx.globalAlpha = qp; ctx.font = F(900, 30); ctx.letterSpacing = '4px'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const tx = '¿EN CUÁL BASE? NO SE HA REVELADO'; const tw = ctx.measureText(tx).width + 50;
      rr(W / 2 - tw / 2, 1600, tw, 64, 10); ctx.fillStyle = COL.red; ctx.fill(); ctx.fillStyle = COL.white; ctx.fillText(tx, W / 2, 1633); ctx.restore();
    }
  }
}

// ---------- ESCENA 8: contador y motivos ----------
function scene8(t) {
  const t0 = T.s8;
  ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, W, H);
  const rg = ctx.createRadialGradient(W / 2, 620, 40, W / 2, 620, 900);
  rg.addColorStop(0, 'rgba(30,62,120,.65)'); rg.addColorStop(1, 'rgba(5,14,29,0)'); ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
  ctx.strokeStyle = 'rgba(120,165,230,.06)'; ctx.lineWidth = 2;
  for (let x = 0; x < W; x += 60) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  for (let y = 0; y < H; y += 60) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  const mv = eio(prog(t, T.motives - .55, .6)); // la cifra sube y se encoge
  const cp = prog(t, T.count, T.eight + .3 - T.count);
  const n = Math.min(8, Math.floor(eo(cp) * 8 + (cp >= 1 ? 1 : 0)));
  const ny = lerp(640, 545, mv), nsz = lerp(380, 230, mv);
  // "AL MENOS"
  const ap = eo(prog(t, t0 + .2, .4));
  ctx.save(); ctx.globalAlpha = ap; ctx.font = F(900, 32); ctx.letterSpacing = '8px'; ctx.textAlign = 'center';
  const aw = ctx.measureText('AL MENOS').width + 50; const ay = lerp(410, 400, mv);
  rr(W / 2 - aw / 2, ay - 30, aw, 56, 8); ctx.fillStyle = COL.red; ctx.fill(); ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText('AL MENOS', W / 2, ay); ctx.restore();
  // número
  const lastTick = Math.min(1, n === 0 ? 0 : 1);
  const pulse = n > 0 ? 1 + .06 * Math.exp(-((t - T.count) % .2) * 20) : 1;
  ctx.save(); ctx.translate(W / 2, ny); ctx.scale(pulse, pulse); ctx.font = FD(900, nsz); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  shadow(50, .6, 0); ctx.shadowColor = 'rgba(227,38,60,.55)'; ctx.fillStyle = COL.white; ctx.globalAlpha = eo(prog(t, t0 + .1, .3));
  ctx.fillText(String(n), 0, 0); ctx.restore();
  ctx.save(); ctx.globalAlpha = eo(prog(t, t0 + .3, .4)); ctx.font = F(900, lerp(66, 50, mv)); ctx.letterSpacing = lerp(14, 10, mv) + 'px'; ctx.textAlign = 'center';
  ctx.fillStyle = COL.red; ctx.fillText('FUNCIONARIOS', W / 2 + 7, ny + nsz * .52 + 20); ctx.restore();
  // mosaico de 8 fotos
  const mo = 1 - eo(prog(t, T.motives - .55, .45));
  if (mo > 0) {
    ctx.save(); ctx.globalAlpha = mo;
    const tw = 225, th = 270, gx = 20, gy = 20, x0 = 60, y0 = 1000;
    ORDER8.forEach((k, i) => {
      const tp = back(prog(t, T.count + i * (T.eight + .3 - T.count) / 8, .35)); if (tp <= 0) return;
      const x = x0 + (i % 4) * (tw + gx), y = y0 + Math.floor(i / 4) * (th + gy);
      ctx.save(); ctx.translate(x + tw / 2, y + th / 2); ctx.scale(tp, tp); ctx.translate(-tw / 2, -th / 2);
      rr(0, 0, tw, th, 14); ctx.save(); ctx.clip(); drawCover(IMG[k], 0, 0, tw, th, PEOPLE[k].f[0], PEOPLE[k].f[1], PEOPLE[k].z);
      const g = ctx.createLinearGradient(0, th - 90, 0, th); g.addColorStop(0, 'rgba(5,14,29,0)'); g.addColorStop(1, 'rgba(5,14,29,.95)'); ctx.fillStyle = g; ctx.fillRect(0, th - 90, tw, 90);
      ctx.font = F(900, 21); ctx.fillStyle = COL.white; ctx.textAlign = 'center'; ctx.fillText(PEOPLE[k].n.split(' ').slice(-1)[0], tw / 2, th - 18);
      ctx.restore();
      rr(0, 0, tw, th, 14); ctx.strokeStyle = 'rgba(255,255,255,.25)'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = COL.red; ctx.beginPath(); ctx.arc(26, 26, 18, 0, Math.PI * 2); ctx.fill();
      ctx.font = F(900, 20); ctx.fillStyle = COL.white; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(String(i + 1), 26, 27);
      ctx.restore();
    });
    ctx.restore();
  }
  // motivos
  const hp = eo(prog(t, T.motives - .3, .45));
  if (hp > 0) {
    ctx.save(); ctx.globalAlpha = hp; ctx.font = F(900, 34); ctx.letterSpacing = '10px'; ctx.textAlign = 'center'; ctx.fillStyle = COL.mute;
    ctx.fillText('LOS MOTIVOS', W / 2, 850); ctx.fillStyle = COL.red; ctx.fillRect(W / 2 - 60 * hp, 872, 120 * hp, 6); ctx.restore();
  }
  const M = [[T.m_iran, 'IRÁN', 'Amenazas del régimen', iconMissile, 'iran_misiles'],
  [T.m_cart, 'CARTELES', 'Del narcotráfico', iconCartel, null],
  [T.m_viol, 'VIOLENCIA POLÍTICA', 'Ataques y amenazas', iconTarget, null]];
  M.forEach(([t1, lab, sub, ic, ph], i) => {
    const p = eo5(prog(t, t1 - .1, .5)); if (p <= 0) return;
    const x = 60, y = 920 + i * 225, w = 960, h = 200;
    ctx.save(); ctx.globalAlpha = p; ctx.translate((1 - p) * 700, 0);
    shadow(30, .6, 10); rr(x, y, w, h, 20); ctx.fillStyle = COL.navy2; ctx.fill(); noShadow();
    if (ph && IMG[ph]) { ctx.save(); rr(x, y, w, h, 20); ctx.clip(); ctx.globalAlpha *= .3; drawCover(IMG[ph], x + 420, y, 540, h, .5, .5, 1);
      const g = ctx.createLinearGradient(x + 420, 0, x + 700, 0); g.addColorStop(0, COL.navy2); g.addColorStop(1, 'rgba(17,40,77,0)'); ctx.globalAlpha = 1; ctx.fillStyle = g; ctx.fillRect(x + 420, y, 300, h); ctx.restore(); }
    rr(x, y, w, h, 20); ctx.strokeStyle = 'rgba(255,255,255,.12)'; ctx.lineWidth = 2; ctx.stroke();
    ctx.beginPath(); ctx.arc(x + 110, y + h / 2, 74, 0, Math.PI * 2); ctx.fillStyle = COL.red; ctx.fill();
    const ip = back(prog(t, t1, .45)); ctx.save(); ctx.translate(x + 110, y + h / 2); ctx.scale(ip, ip); ic(0, 0, 82); ctx.restore();
    ctx.font = F(800, 24); ctx.letterSpacing = '4px'; ctx.fillStyle = COL.red; ctx.fillText('0' + (i + 1), x + 215, y + 66);
    const fs = fitFont(lab, 900, 58, 700, 'Inter Display'); ctx.font = FD(900, fs); ctx.letterSpacing = '0px'; ctx.fillStyle = COL.white; ctx.fillText(lab, x + 212, y + 128);
    ctx.font = F(600, 26); ctx.fillStyle = COL.mute; ctx.fillText(sub, x + 214, y + 168);
    ctx.restore();
  });
}

// ---------- ESCENA 9: mapa general ----------
function scene9(t) {
  const t0 = T.s9;
  const z = lerp(.092, .1, prog(t, t0, T.s10 - t0));
  cam.x = P(-77.044, 38.868)[0]; cam.y = P(-77.044, 38.868)[1]; cam.s = z; cam.ax = 540; cam.ay = 920;
  drawMap(t);
  const keys = ['mcnair', 'jbab', 'myer'];
  keys.forEach((k, i) => drawBase(k, prog(t, t0 + .2 + i * .18, .8), t));
  // Casa Blanca
  const wh = S(GEO.wh);
  const wp = back(prog(t, t0 + .3, .5));
  ctx.save(); ctx.translate(wh[0], wh[1]);
  const rp = ((t - t0) % 1.5) / 1.5;
  ctx.strokeStyle = `rgba(255,255,255,${(1 - rp) * .6})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(0, 0, 60 + rp * 110, 0, Math.PI * 2); ctx.stroke();
  ctx.scale(wp, wp);
  ctx.beginPath(); ctx.arc(0, 0, 70, 0, Math.PI * 2); ctx.fillStyle = COL.navy; ctx.fill(); ctx.strokeStyle = COL.white; ctx.lineWidth = 4; ctx.stroke();
  iconWhiteHouse(0, 8, 90); ctx.restore();
  const lp = eo(prog(t, T.wh - .2, .4));
  ctx.save(); ctx.globalAlpha = Math.max(lp, eo(prog(t, t0 + .6, .4))); ctx.font = F(900, 30); ctx.letterSpacing = '4px'; ctx.textAlign = 'center';
  shadow(10, .9, 2); ctx.fillStyle = COL.white; ctx.fillText('CASA BLANCA', wh[0], wh[1] - 92); ctx.restore();
  // líneas punteadas
  const names = { mcnair: 'FORT McNAIR', jbab: 'ANACOSTIA-BOLLING', myer: 'MYER-HENDERSON HALL' };
  keys.forEach((k, i) => {
    const b = S(BASES[k].pin);
    const p = prog(t, T.lines - .45 + i * .3, .8);
    // etiqueta base
    const tp = eo(prog(t, t0 + .5 + i * .2, .4));
    if (tp > 0) {
      ctx.save(); ctx.globalAlpha = tp; ctx.font = F(900, 24); ctx.letterSpacing = '2px';
      const tw = ctx.measureText(names[k]).width + 28;
      const off = { mcnair: [-tw - 30, 40], jbab: [-tw / 2, 150], myer: [-tw / 2, 70] }[k];
      ctx.fillStyle = COL.red; rr(b[0] + off[0], b[1] + off[1] - 22, tw, 42, 6); ctx.fill();
      ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText(names[k], b[0] + off[0] + 14, b[1] + off[1] + 1); ctx.restore();
    }
    if (p <= 0) return;
    const ex = lerp(wh[0], b[0], eo(p)), ey = lerp(wh[1], b[1], eo(p));
    ctx.save(); ctx.setLineDash([16, 14]); ctx.lineDashOffset = -t * 40; ctx.strokeStyle = COL.white; ctx.lineWidth = 6; ctx.lineCap = 'round';
    shadow(10, .7, 0);
    ctx.beginPath(); ctx.moveTo(wh[0], wh[1]); ctx.lineTo(ex, ey); ctx.stroke(); ctx.restore();
    ctx.beginPath(); ctx.arc(ex, ey, 11, 0, Math.PI * 2); ctx.fillStyle = COL.white; ctx.fill();
    // etiqueta "a pocos minutos"
    const mp = eo(prog(t, T.lines - .45 + i * .3 + .7, .35));
    if (mp > 0) {
      const fr = { mcnair: .42, jbab: .62, myer: .5 }[k]; const mx = lerp(wh[0], b[0], fr) + { mcnair: 95, jbab: 105, myer: 0 }[k], my = lerp(wh[1], b[1], fr) + (k === 'myer' ? -34 : 0);
      ctx.save(); ctx.globalAlpha = mp; ctx.translate(mx, my); ctx.scale(lerp(.6, 1, mp), lerp(.6, 1, mp));
      ctx.font = F(800, 22); const tw = ctx.measureText('a pocos minutos').width + 54;
      shadow(12, .6, 4); rr(-tw / 2, -20, tw, 40, 20); ctx.fillStyle = COL.white; ctx.fill(); noShadow();
      ctx.strokeStyle = COL.navy; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(-tw / 2 + 22, 0, 9, 0, Math.PI * 2); ctx.moveTo(-tw / 2 + 22, -5); ctx.lineTo(-tw / 2 + 22, 0); ctx.lineTo(-tw / 2 + 26, 3); ctx.stroke();
      ctx.fillStyle = COL.navy; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText('a pocos minutos', -tw / 2 + 38, 1);
      ctx.restore();
    }
  });
  // "3 BASES"
  const bp = eo(prog(t, t0 + .25, .45));
  if (bp > 0) {
    ctx.save(); ctx.globalAlpha = bp; ctx.translate(0, (1 - bp) * 30);
    shadow(20, .6, 6); rr(60, 420, 300, 120, 16); ctx.fillStyle = COL.red; ctx.fill(); noShadow();
    ctx.font = FD(900, 92); ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText('3', 90, 484);
    ctx.font = F(900, 40); ctx.letterSpacing = '4px'; ctx.fillText('BASES', 160, 470);
    ctx.font = F(600, 20); ctx.letterSpacing = '1px'; ctx.fillText('MILITARES', 162, 505); ctx.restore();
  }
  // texto final
  const gp = prog(t, T.generals - .1, .5);
  if (gp > 0) {
    const g = ctx.createLinearGradient(0, 1300, 0, 1800); g.addColorStop(0, 'rgba(5,14,29,0)'); g.addColorStop(.35, 'rgba(5,14,29,.92)'); g.addColorStop(1, 'rgba(5,14,29,.95)');
    ctx.save(); ctx.globalAlpha = eo(gp); ctx.fillStyle = g; ctx.fillRect(0, 1300, W, 500);
    ctx.textAlign = 'center';
    for (let i = 0; i < 4; i++) { const sp = back(prog(t, T.generals + i * .08, .3)); if (sp > 0) star(W / 2 - 105 + i * 70, 1440, 24 * sp, i % 3 ? COL.white : COL.red); }
    const tp = eo5(gp);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 1470, W, 230); ctx.clip();
    ctx.font = FD(900, 74); ctx.fillStyle = COL.white; shadow(20, .6, 6);
    ctx.fillText('CASAS QUE ERAN', W / 2, 1555 + (1 - tp) * 120);
    ctx.fillStyle = COL.red; ctx.fillText('SOLO PARA GENERALES', W / 2, 1640 + (1 - eo5(prog(t, T.generals + .05, .5))) * 140);
    ctx.restore(); ctx.restore();
  }
}

// ---------- ESCENA 10: encuesta ----------
function scene10(t) {
  const t0 = T.s10;
  const sp = eio(prog(t, t0, .6));
  const mid = 980;
  // mitad superior (azul) y mitad inferior (roja) con corte diagonal
  ctx.fillStyle = '#0D2B5C'; ctx.fillRect(0, 0, W, H);
  const gb = ctx.createLinearGradient(0, 0, 0, mid); gb.addColorStop(0, '#071631'); gb.addColorStop(1, '#16407F'); ctx.fillStyle = gb; ctx.fillRect(0, 0, W, mid + 60);
  ctx.save(); ctx.beginPath(); ctx.moveTo(0, mid + 50); ctx.lineTo(W, mid - 50); ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
  ctx.translate(0, (1 - sp) * 900);
  const gr = ctx.createLinearGradient(0, mid, 0, H); gr.addColorStop(0, '#C8192F'); gr.addColorStop(1, '#6E0A18'); ctx.fillStyle = gr; ctx.fill();
  ctx.restore();
  // diagonal blanca
  ctx.save(); ctx.globalAlpha = sp; ctx.strokeStyle = COL.white; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(0, mid + 50); ctx.lineTo(W, mid - 50); ctx.stroke(); ctx.restore();
  // opción A
  const a = eo(prog(t, T.p_prot - .2, .5));
  if (a > 0) {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(0, (1 - a) * 40);
    const ip = back(prog(t, T.p_prot - .2, .5)); ctx.save(); ctx.translate(W / 2, 600); ctx.scale(ip, ip); iconShield(0, 0, 150); ctx.restore();
    ctx.textAlign = 'center'; ctx.font = FD(900, 84); shadow(20, .5, 6); ctx.fillStyle = COL.white;
    ctx.fillText('PROTECCIÓN', W / 2, 800); ctx.fillText('NECESARIA', W / 2, 890); ctx.restore();
  }
  const b = eo(prog(t, T.p_gob - .2, .5));
  if (b > 0) {
    ctx.save(); ctx.globalAlpha = b; ctx.translate(0, (1 - b) * 40);
    const ip = back(prog(t, T.p_gob - .2, .5)); ctx.save(); ctx.translate(W / 2, 1200); ctx.scale(ip, ip); iconBarrier(0, 0, 150); ctx.restore();
    ctx.textAlign = 'center'; ctx.font = FD(900, 84); shadow(20, .5, 6); ctx.fillStyle = COL.white;
    ctx.fillText('GOBIERNO', W / 2, 1395); ctx.fillText('AISLADO', W / 2, 1485); ctx.restore();
  }
  // VS
  const v = back(prog(t, T.p_gob - .45, .4));
  if (v > 0) {
    ctx.save(); ctx.translate(W / 2 + 330, mid - 15); ctx.scale(v, v); ctx.rotate(-.09);
    shadow(30, .6, 8); ctx.beginPath(); ctx.arc(0, 0, 78, 0, Math.PI * 2); ctx.fillStyle = COL.white; ctx.fill(); noShadow();
    ctx.font = FD(900, 64); ctx.fillStyle = COL.navy; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('VS', 0, 4); ctx.restore();
  }
  // CTA
  const c = eo(prog(t, T.p_cta - .3, .5));
  if (c > 0) {
    ctx.save(); ctx.globalAlpha = c; ctx.translate(W / 2, 1620 + (1 - c) * 60);
    const pul = 1 + .03 * Math.sin((t - T.p_cta) * 8);
    ctx.scale(pul, pul);
    ctx.font = F(900, 46); const tx = '¿TÚ QUÉ OPINAS? COMENTA'; const tw = ctx.measureText(tx).width + 150;
    shadow(30, .6, 10); rr(-tw / 2, -50, tw, 100, 50); ctx.fillStyle = COL.white; ctx.fill(); noShadow();
    // burbuja
    ctx.save(); ctx.translate(-tw / 2 + 62, 0);
    rr(-26, -22, 52, 38, 10); ctx.fillStyle = COL.red; ctx.fill(); ctx.beginPath(); ctx.moveTo(-10, 14); ctx.lineTo(-16, 28); ctx.lineTo(4, 14); ctx.fill();
    ctx.fillStyle = COL.white; for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.arc(i * 12, -3, 4, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
    ctx.fillStyle = COL.navy; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(tx, -tw / 2 + 106, 3);
    ctx.restore();
  }
}

// ---------- ESCENA 11: cierre ----------
function scene11(t) {
  const t0 = T.s11;
  ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, W, H);
  const rg = ctx.createRadialGradient(W / 2, 820, 30, W / 2, 820, 800);
  rg.addColorStop(0, 'rgba(36,74,140,.75)'); rg.addColorStop(1, 'rgba(5,14,29,0)'); ctx.fillStyle = rg; ctx.fillRect(0, 0, W, H);
  // rayos giratorios
  ctx.save(); ctx.translate(W / 2, 820); ctx.rotate(t * .15); ctx.globalAlpha = .07;
  for (let i = 0; i < 12; i++) { ctx.rotate(Math.PI / 6); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(-60, -1200); ctx.lineTo(60, -1200); ctx.closePath(); ctx.fillStyle = COL.white; ctx.fill(); }
  ctx.restore();
  const lp = eo(prog(t, t0 + .05, .7)), qp = prog(t, t0 + .6, .45);
  iconMagnifier(W / 2 + 10, 790, 330, lp, qp);
  const wp = eo5(prog(t, t0 + .5, .5));
  ctx.save(); ctx.textAlign = 'center';
  ctx.beginPath(); ctx.rect(0, 1000, W, 260); ctx.clip();
  ctx.font = FD(900, 104); ctx.letterSpacing = '4px'; ctx.fillStyle = COL.white; ctx.fillText('CAPITAL', W / 2, 1110 + (1 - wp) * 140);
  ctx.fillStyle = COL.red; ctx.fillText('CURIOSO', W / 2, 1220 + (1 - eo5(prog(t, t0 + .6, .5))) * 160);
  ctx.restore();
  const hp = eo(prog(t, t0 + .9, .5));
  if (hp > 0) {
    ctx.save(); ctx.globalAlpha = hp; ctx.textAlign = 'center'; ctx.font = F(800, 46); ctx.fillStyle = COL.white; ctx.fillText('@capitalcuriosoo', W / 2, 1340);
    const bt = 1 + .04 * Math.sin((t - t0) * 7);
    ctx.translate(W / 2, 1450); ctx.scale(bt * lerp(.7, 1, hp), bt * lerp(.7, 1, hp));
    shadow(30, .6, 10); rr(-210, -52, 420, 104, 52); ctx.fillStyle = COL.red; ctx.fill(); noShadow();
    ctx.font = F(900, 44); ctx.letterSpacing = '3px'; ctx.fillStyle = COL.white; ctx.textBaseline = 'middle'; ctx.fillText('SÍGUENOS', 26, 3);
    ctx.lineWidth = 7; ctx.strokeStyle = COL.white; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(-150, 3); ctx.lineTo(-118, 3); ctx.moveTo(-134, -13); ctx.lineTo(-134, 19); ctx.stroke();
    ctx.restore();
  }
}

// ---------- cuadro ----------
function renderFrame(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.letterSpacing = '0px'; ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'; ctx.filter = 'none'; noShadow();
  ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, W, H);
  ctx.save();
  if (t < T.s2) scene1(t);
  else if (t < T.s3) scene2(t);
  else if (t < T.s4) scene3(t);
  else if (t < T.s8) mapScenes(t);
  else if (t < T.s9) scene8(t);
  else if (t < T.s10) scene9(t);
  else if (t < T.s11) scene10(t);
  else scene11(t);
  ctx.restore();
  ctx.save(); vignette(); ctx.restore();
  if (t < T.s11 && !(t >= T.s3 && t < T.s4)) { ctx.save(); topBand(); brandBug(t); ctx.restore(); }
  ctx.save(); drawSubs(t); ctx.restore();
  ctx.save(); sources(t); ctx.restore();
  ctx.save(); wipe(t); ctx.restore();
  ctx.save(); grain(t); ctx.restore();
  const fi = 1 - prog(t, 0, .35), fo = prog(t, T.dur - .5, .5);
  const fa = Math.max(fi, fo); if (fa > 0) { ctx.fillStyle = `rgba(0,0,0,${fa})`; ctx.fillRect(0, 0, W, H); }
}

async function init(timeline, words) {
  T = timeline; WORDS = words; buildChunks();
  const cv = document.getElementById('c'); ctx = cv.getContext('2d');
  await Promise.all(IMG_LIST.map(n => new Promise(res => {
    const im = new Image(); im.onload = () => { IMG[n] = im; res(); }; im.onerror = () => { IMG[n] = null; res(); };
    im.src = '../imagenes/' + n + '.jpg';
  })));
  for (const f of ['900 40px "Inter"', '800 40px "Inter"', '700 40px "Inter"', '600 40px "Inter"', 'italic 700 40px "Inter"', '900 40px "Inter Display"']) await document.fonts.load(f);
  BG.casa = makeBg('casablanca', 3, .62);
  BG.tesoro = makeBg('tesoro', 14, .45);
  makeGrain();
  return IMG_LIST.filter(n => !IMG[n]);
}
window.init = init; window.renderFrame = renderFrame;
