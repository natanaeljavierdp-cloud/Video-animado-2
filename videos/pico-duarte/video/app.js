/* Capital Curioso — "Lo más alto y lo más bajo del Caribe están en RD"
 * Animación 100 % vectorial dibujada en canvas. render(t) dibuja el fotograma
 * del segundo t. Todos los tiempos salen de los tiempos reales de la voz
 * (words.json), desplazados OFF segundos.
 */
'use strict';
const W = 1080, H = 1920;
const cv = document.getElementById('c');
const ctx = cv.getContext('2d');

const C = {
  navy: '#0B2A5B', red: '#FF4B55', yel: '#FFD23F', white: '#FFFFFF', cream: '#F6F3EC',
  drBlue: '#002D62', drRed: '#CE1126', green: '#2BB673', teal: '#17909C', ink: '#06183A',
};
const OFF = 0.25;           // la voz entra a los 0,25 s
let WORDS = [], GROUPS = [], B = [], ANIM_END = 0, VOICE_END = 0;

// ---------- fuentes ----------
const FP = 'node_modules/@fontsource/';
const fonts = [
  new FontFace('Poppins', `url(${FP}poppins/files/poppins-latin-400-normal.woff2)`, { weight: '400' }),
  new FontFace('Poppins', `url(${FP}poppins/files/poppins-latin-600-normal.woff2)`, { weight: '600' }),
  new FontFace('Poppins', `url(${FP}poppins/files/poppins-latin-700-normal.woff2)`, { weight: '700' }),
  new FontFace('Poppins', `url(${FP}poppins/files/poppins-latin-800-normal.woff2)`, { weight: '800' }),
  new FontFace('Archivo Black', `url(${FP}archivo-black/files/archivo-black-latin-400-normal.woff2)`, { weight: '400' }),
];
window.READY = Promise.all(fonts.map(f => f.load().then(ff => document.fonts.add(ff))));

// ---------- utilidades ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const eo = t => 1 - Math.pow(1 - clamp(t), 3);
const ei = t => Math.pow(clamp(t), 3);
const eio = t => { t = clamp(t); return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const back = t => { t = clamp(t); const c1 = 2.0, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
const prog = (t, a, d) => clamp((t - a) / d);
const pop = (t, a, d = .45) => (t < a ? 0 : back(prog(t, a, d)));
const bump = (t, a, d = .4) => Math.sin(Math.PI * prog(t, a, d));
const EASE = { eo, ei, eio, lin: x => clamp(x) };
const S = i => WORDS[i].start + OFF;
const E = i => WORDS[i].end + OFF;
const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z]/g, '').toUpperCase();
function seeded(n) { let s = n * 9301 + 49297; return () => (s = (s * 9301 + 49297) % 233280) / 233280; }

function F(w, s, fam = 'Poppins') { return `${w} ${s}px "${fam}"`; }
function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function withT(x, y, s, fn, rot = 0) { ctx.save(); ctx.translate(x, y); if (rot) ctx.rotate(rot); ctx.scale(s, s); fn(); ctx.restore(); }
function alpha(a, fn) { ctx.save(); ctx.globalAlpha *= clamp(a); fn(); ctx.restore(); }
function shadow(on, blur = 18, oy = 6, col = 'rgba(0,0,0,.35)') {
  if (on) { ctx.shadowColor = col; ctx.shadowBlur = blur; ctx.shadowOffsetY = oy; }
  else { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetY = 0; }
}
function text(s, x, y, o = {}) {
  const { w = 800, size = 48, fam = 'Poppins', color = '#fff', align = 'center', stroke = null, sw = 8, maxW = 0, sh = false, ls = 0 } = o;
  ctx.letterSpacing = ls + 'px';
  let sz = size;
  ctx.font = F(w, sz, fam);
  if (maxW) { const m = ctx.measureText(s).width; if (m > maxW) { sz = size * maxW / m; ctx.font = F(w, sz, fam); } }
  ctx.textAlign = align; ctx.textBaseline = 'middle';
  if (sh) shadow(true, 14, 5);
  if (stroke) { ctx.lineJoin = 'round'; ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.strokeText(s, x, y); shadow(false); }
  ctx.fillStyle = color; ctx.fillText(s, x, y);
  shadow(false); ctx.letterSpacing = '0px';
  return sz;
}
// texto con partes de distintos colores, centrado en x
function rich(parts, x, y, o = {}) {
  const { w = 800, size = 48, fam = 'Poppins', stroke = null, sw = 8, maxW = 0, sh = false } = o;
  let sz = size; ctx.font = F(w, sz, fam);
  let tot = parts.reduce((a, p) => a + ctx.measureText(p[0]).width, 0);
  if (maxW && tot > maxW) { sz = size * maxW / tot; ctx.font = F(w, sz, fam); tot = parts.reduce((a, p) => a + ctx.measureText(p[0]).width, 0); }
  let cx = x - tot / 2;
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  for (const [s, col] of parts) {
    if (sh) shadow(true, 14, 5);
    if (stroke) { ctx.lineJoin = 'round'; ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.strokeText(s, cx, y); shadow(false); }
    ctx.fillStyle = col; ctx.fillText(s, cx, y); shadow(false);
    cx += ctx.measureText(s).width;
  }
  return tot;
}
function pill(x, y, w, h, fill, r = h / 2, strokeCol = null, lw = 4) {
  rr(x - w / 2, y - h / 2, w, h, r); ctx.fillStyle = fill; ctx.fill();
  if (strokeCol) { ctx.strokeStyle = strokeCol; ctx.lineWidth = lw; ctx.stroke(); }
}
function poly(pts, sx = 1, sy = 1) { ctx.beginPath(); pts.forEach(([x, y], i) => i ? ctx.lineTo(x * sx, y * sy) : ctx.moveTo(x * sx, y * sy)); ctx.closePath(); }
function check(x, y, s, col = '#fff', lw = 10) {
  ctx.beginPath(); ctx.moveTo(x - s * .5, y); ctx.lineTo(x - s * .12, y + s * .38); ctx.lineTo(x + s * .55, y - s * .4);
  ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke();
}

// ---------- bandera dominicana (dibujada) ----------
const FL = document.createElement('canvas'); FL.width = 300; FL.height = 200;
(function drawFlagImg() {
  const f = FL.getContext('2d'); const cw = 34, mx = 150, my = 100;
  f.fillStyle = '#fff'; f.fillRect(0, 0, 300, 200);
  f.fillStyle = C.drBlue; f.fillRect(0, 0, mx - cw / 2, my - cw / 2); f.fillRect(mx + cw / 2, my + cw / 2, 300, 200);
  f.fillStyle = C.drRed; f.fillRect(mx + cw / 2, 0, 300, my - cw / 2); f.fillRect(0, my + cw / 2, mx - cw / 2, 200);
  // escudo simplificado
  f.lineWidth = 4; f.strokeStyle = '#1E8E3E';
  f.beginPath(); f.arc(mx, my, 24, Math.PI * .55, Math.PI * 1.45); f.stroke();
  f.beginPath(); f.arc(mx, my, 24, -Math.PI * .45, Math.PI * .45); f.stroke();
  f.fillStyle = C.drBlue; f.fillRect(mx - 11, my - 13, 11, 12); f.fillRect(mx, my + 1, 11, 12);
  f.fillStyle = C.drRed; f.fillRect(mx, my - 13, 11, 12); f.fillRect(mx - 11, my + 1, 11, 12);
  f.fillStyle = '#fff'; f.fillRect(mx - 2, my - 13, 4, 26); f.fillRect(mx - 11, my - 2, 22, 4);
  f.fillStyle = C.drBlue; f.fillRect(mx - 16, my - 26, 32, 6);
  f.fillStyle = C.drRed; f.fillRect(mx - 16, my + 20, 32, 6);
})();
function flag(x, y, w, h, t, amp = 0.06) {
  const N = 30; const a = h * amp;
  for (let i = 0; i < N; i++) {
    const u = i / N; const ph = u * Math.PI * 2.2 - t * 6;
    const dy = Math.sin(ph) * a * (0.3 + u);
    const sx = i * FL.width / N, sw = FL.width / N + 0.6;
    const dx = x + u * w, dw = w / N + 0.8;
    ctx.drawImage(FL, sx, 0, sw, FL.height, dx, y + dy, dw, h);
    const sh = (Math.cos(ph) + 1) / 2;
    ctx.fillStyle = `rgba(0,0,0,${0.13 * sh})`; ctx.fillRect(dx, y + dy, dw, h);
  }
}
function flagPole(x, y, len, fw, t) { // asta con base en (x,y)
  ctx.strokeStyle = '#E8E8E8'; ctx.lineWidth = Math.max(3, fw * .05); ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - len); ctx.stroke();
  flag(x + 2, y - len, fw, fw * 2 / 3, t, .08);
  ctx.fillStyle = C.yel; ctx.beginPath(); ctx.arc(x, y - len, Math.max(4, fw * .06), 0, 7); ctx.fill();
}

// ---------- piezas de dibujo ----------
function cloud(x, y, s, a = .9) {
  ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = '#fff';
  ctx.beginPath();
  [[0, 0, 46], [44, -18, 40], [86, 2, 38], [40, 14, 40], [-38, 10, 30], [120, 14, 26]].forEach(([cx, cy, r]) => {
    ctx.moveTo(x + (cx + r) * s, y + cy * s); ctx.arc(x + cx * s, y + cy * s, r * s, 0, 7);
  });
  ctx.fill(); ctx.restore();
}
function mountain(cx, base, w, h, grow = 1, t = 0) {
  ctx.save(); ctx.translate(cx, base); ctx.scale(1, Math.max(0.001, grow));
  const P = [[-.5, 0], [-.36, -.38], [-.27, -.33], [-.12, -.8], [0, -1], [.1, -.84], [.2, -.58], [.31, -.64], [.5, 0]];
  const g = ctx.createLinearGradient(0, -h, 0, 0);
  g.addColorStop(0, '#7C8BA6'); g.addColorStop(.45, '#556A86'); g.addColorStop(.62, '#2F7A55'); g.addColorStop(1, '#1F5A3E');
  poly(P, w, h); ctx.fillStyle = g; ctx.fill();
  // sombra lado derecho
  poly([[0, -1], [.1, -.84], [.2, -.58], [.31, -.64], [.5, 0], [.04, 0], [.02, -.5]], w, h);
  ctx.fillStyle = 'rgba(5,20,50,.25)'; ctx.fill();
  // nieve
  poly([[-.145, -.72], [-.12, -.8], [0, -1], [.1, -.84], [.135, -.75], [.09, -.78], [.05, -.71], [0, -.78], [-.05, -.7], [-.1, -.76]], w, h);
  ctx.fillStyle = '#FFFFFF'; ctx.fill();
  poly([[0, -1], [.1, -.84], [.135, -.75], [.09, -.78], [.05, -.71], [.02, -.8]], w, h);
  ctx.fillStyle = '#D6E4F5'; ctx.fill();
  // pinos en la base
  const r = seeded(3);
  for (let i = 0; i < 26; i++) {
    const u = -.46 + i * .036 + r() * .01; const yy = -(.03 + r() * .14) * h * (1 - Math.abs(u) * 1.6);
    const th = 34 + r() * 22; const tw = th * .5;
    ctx.fillStyle = i % 2 ? '#174A32' : '#1D5B3C';
    ctx.beginPath(); ctx.moveTo(u * w, yy - th); ctx.lineTo(u * w + tw / 2, yy); ctx.lineTo(u * w - tw / 2, yy); ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}
function hiker(x, y, s, t, walking, cheer) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const sw = walking ? Math.sin(t * 14) : 0; const bob = walking ? Math.abs(Math.sin(t * 14)) * 3 : 0;
  ctx.translate(0, -bob);
  ctx.lineCap = 'round'; ctx.strokeStyle = '#1B1B2F'; ctx.lineWidth = 7;
  ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(12 * sw, 0); ctx.moveTo(0, -30); ctx.lineTo(-12 * sw, 0); ctx.stroke();
  ctx.fillStyle = '#F2A541'; rr(-17, -60, 12, 26, 4); ctx.fill();          // mochila
  ctx.strokeStyle = C.red; ctx.lineWidth = 14;
  ctx.beginPath(); ctx.moveTo(0, -30); ctx.lineTo(0, -58); ctx.stroke(); // chaqueta
  ctx.fillStyle = '#C68B59'; ctx.beginPath(); ctx.arc(0, -70, 10, 0, 7); ctx.fill();
  ctx.fillStyle = C.navy; ctx.beginPath(); ctx.arc(0, -73, 10, Math.PI, 0); ctx.fill(); ctx.fillRect(0, -75, 15, 4);
  ctx.strokeStyle = C.red; ctx.lineWidth = 6;
  if (cheer) {
    const wv = Math.sin(t * 8) * 6;
    ctx.beginPath(); ctx.moveTo(0, -54); ctx.lineTo(-16, -78 + wv); ctx.moveTo(0, -54); ctx.lineTo(16, -78 - wv); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.moveTo(0, -54); ctx.lineTo(13, -42); ctx.stroke();
    ctx.strokeStyle = '#ddd'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(13, -42); ctx.lineTo(15, -112); ctx.stroke();
    flag(16, -112, 36, 24, t, .1);
  }
  ctx.restore();
}
function croc(x, y, s, t, dir = 1) { // y = línea del agua; mira a la derecha si dir=1
  ctx.save(); ctx.translate(x, y); ctx.scale(s * dir, s);
  const wv = Math.sin(t * 5);
  ctx.fillStyle = '#3F7F3A';
  ctx.beginPath(); ctx.moveTo(-100, -18);
  ctx.quadraticCurveTo(-190, -10 + wv * 10, -270, 4 + wv * 18);
  ctx.quadraticCurveTo(-190, 14 + wv * 8, -100, 22); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.ellipse(0, 0, 125, 30, 0, 0, 7); ctx.fill();
  ctx.beginPath(); ctx.moveTo(100, -22); ctx.lineTo(235, -4); ctx.quadraticCurveTo(245, 6, 232, 12); ctx.lineTo(100, 22); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#8DB86B'; ctx.beginPath(); ctx.ellipse(10, 14, 110, 12, 0, 0, 7); ctx.fill();
  ctx.fillStyle = '#fff';
  for (let i = 0; i < 6; i++) { ctx.beginPath(); ctx.moveTo(130 + i * 17, 10); ctx.lineTo(137 + i * 17, 20); ctx.lineTo(144 + i * 17, 10); ctx.fill(); }
  ctx.fillStyle = '#2E6A2B';
  for (let i = 0; i < 13; i++) { const xx = -250 + i * 26; const yy = xx < -100 ? -6 + wv * 8 * ((-100 - xx) / 170) : -28; ctx.beginPath(); ctx.moveTo(xx - 9, yy + 4); ctx.lineTo(xx, yy - 12); ctx.lineTo(xx + 9, yy + 4); ctx.fill(); }
  ctx.fillStyle = '#3F7F3A'; ctx.beginPath(); ctx.arc(118, -24, 16, 0, 7); ctx.fill();
  ctx.fillStyle = C.yel; ctx.beginPath(); ctx.arc(121, -27, 9, 0, 7); ctx.fill();
  ctx.fillStyle = '#111'; ctx.beginPath(); ctx.ellipse(122, -27, 2.5, 8, 0, 0, 7); ctx.fill();
  ctx.fillStyle = '#2E6A2B'; ctx.beginPath(); ctx.arc(226, -8, 4, 0, 7); ctx.fill();
  ctx.restore();
}
function crocEyes(x, y, s, rise, t) { // ojos asomando: y = superficie
  ctx.save(); ctx.translate(x, y - rise); ctx.scale(s, s);
  for (const dx of [-38, 38]) {
    ctx.fillStyle = '#3F7F3A'; ctx.beginPath(); ctx.ellipse(dx, 0, 30, 24, 0, Math.PI, 0); ctx.fill(); ctx.fillRect(dx - 30, 0, 60, 30);
    ctx.fillStyle = C.yel; ctx.beginPath(); ctx.arc(dx, -2, 14, 0, 7); ctx.fill();
    const blink = (Math.sin(t * 2.3) > 0.97) ? .15 : 1;
    ctx.fillStyle = '#111'; ctx.beginPath(); ctx.ellipse(dx + Math.sin(t * 1.5) * 3, -2, 3.5, 12 * blink, 0, 0, 7); ctx.fill();
  }
  ctx.fillStyle = '#3F7F3A'; ctx.beginPath(); ctx.ellipse(0, 30, 56, 12, 0, Math.PI, 0); ctx.fill();
  ctx.restore();
}
function water(x, y, w, h, t, c1 = '#1FA3B0', c2 = '#0D5C78') {
  const g = ctx.createLinearGradient(0, y, 0, y + h); g.addColorStop(0, c1); g.addColorStop(1, c2);
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x, y + h);
  for (let xx = x; xx <= x + w + 10; xx += 20) ctx.lineTo(xx, y + Math.sin(xx * .025 + t * 2.4) * 7);
  ctx.lineTo(x + w, y + h); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.55)'; ctx.lineWidth = 4; ctx.beginPath();
  for (let xx = x; xx <= x + w + 10; xx += 20) { const yy = y + Math.sin(xx * .025 + t * 2.4) * 7; xx === x ? ctx.moveTo(xx, yy) : ctx.lineTo(xx, yy); }
  ctx.stroke();
}
function waterVeil(x, y, w, h, t) { // agua por delante de los animales sumergidos
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, 'rgba(31,163,176,.68)'); g.addColorStop(.6, 'rgba(31,163,176,.6)'); g.addColorStop(1, 'rgba(31,163,176,0)');
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x, y + h);
  for (let xx = x; xx <= x + w + 10; xx += 20) ctx.lineTo(xx, y + 6 + Math.sin(xx * .025 + t * 2.4) * 7);
  ctx.lineTo(x + w, y + h); ctx.closePath(); ctx.fill();
}
function flamingo(x, y, s, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const hb = Math.sin(t * 2.2) * 6;
  ctx.strokeStyle = '#F07AA0'; ctx.lineWidth = 7; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(2, -60); ctx.lineTo(0, -120); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(8, -120); ctx.lineTo(22, -88); ctx.lineTo(4, -72); ctx.stroke();
  ctx.fillStyle = '#FF8FB1'; ctx.beginPath(); ctx.ellipse(0, -158, 66, 40, -0.15, 0, 7); ctx.fill();
  ctx.fillStyle = '#F06C9B'; ctx.beginPath(); ctx.ellipse(-12, -160, 44, 24, -0.25, 0, 7); ctx.fill();
  ctx.fillStyle = '#E2557F'; ctx.beginPath(); ctx.moveTo(-58, -170); ctx.lineTo(-92, -182); ctx.lineTo(-62, -150); ctx.fill();
  ctx.strokeStyle = '#FF8FB1'; ctx.lineWidth = 17;
  ctx.beginPath(); ctx.moveTo(42, -178); ctx.bezierCurveTo(90, -210, 0, -250, 30, -300 + hb); ctx.stroke();
  ctx.fillStyle = '#FF8FB1'; ctx.beginPath(); ctx.arc(38, -306 + hb, 18, 0, 7); ctx.fill();
  ctx.fillStyle = '#F6F3EC'; ctx.beginPath(); ctx.moveTo(50, -312 + hb); ctx.lineTo(84, -300 + hb); ctx.lineTo(54, -296 + hb); ctx.fill();
  ctx.fillStyle = '#111'; ctx.beginPath(); ctx.moveTo(72, -304 + hb); ctx.lineTo(88, -298 + hb); ctx.lineTo(80, -282 + hb); ctx.lineTo(68, -298 + hb); ctx.fill();
  ctx.beginPath(); ctx.arc(40, -312 + hb, 3.5, 0, 7); ctx.fill();
  ctx.restore();
}
function iguana(x, y, s, t, kind, sil = 0) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const base = kind === 'ricord' ? '#8E9F78' : '#7F838C';
  const dark = kind === 'ricord' ? '#5F7350' : '#5A5E68';
  const col = c => sil > 0.5 ? '#1A2A4A' : c;
  const tw = Math.sin(t * 3) * 8, hb = Math.sin(t * 2.6) * 3;
  ctx.fillStyle = col(base);
  ctx.beginPath(); ctx.moveTo(-60, -40); ctx.quadraticCurveTo(-130, -30 + tw, -175, -4 + tw); ctx.quadraticCurveTo(-130, -10 + tw, -60, -10); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.ellipse(0, -30, 72, 27, 0, 0, 7); ctx.fill();
  ctx.strokeStyle = col(dark); ctx.lineWidth = 9; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-40, -14); ctx.lineTo(-52, 0); ctx.moveTo(-25, -12); ctx.lineTo(-18, 0); ctx.moveTo(35, -14); ctx.lineTo(28, 0); ctx.moveTo(50, -14); ctx.lineTo(60, 0); ctx.stroke();
  ctx.save(); ctx.translate(0, hb);
  ctx.fillStyle = col(base); ctx.beginPath(); ctx.ellipse(88, -42, 34, 21, -.1, 0, 7); ctx.fill();
  ctx.fillStyle = col(dark); ctx.beginPath(); ctx.ellipse(76, -24, 16, 11, 0, 0, 7); ctx.fill();
  if (kind === 'rino') {
    ctx.fillStyle = col('#9A9EA8');
    [[104, -60], [114, -57], [94, -62]].forEach(([hx, hy]) => { ctx.beginPath(); ctx.moveTo(hx - 5, hy + 3); ctx.lineTo(hx, hy - 12); ctx.lineTo(hx + 5, hy + 3); ctx.fill(); });
  }
  if (sil <= 0.5) {
    ctx.fillStyle = kind === 'ricord' ? '#C0392B' : '#E2B33C'; ctx.beginPath(); ctx.arc(95, -47, 6, 0, 7); ctx.fill();
    ctx.fillStyle = '#111'; ctx.beginPath(); ctx.arc(96, -47, 2.6, 0, 7); ctx.fill();
  }
  ctx.restore();
  ctx.fillStyle = col(dark);
  for (let i = 0; i < 10; i++) { const xx = -55 + i * 13; ctx.beginPath(); ctx.moveTo(xx - 5, -54); ctx.lineTo(xx, -70 + (i % 2) * 4); ctx.lineTo(xx + 5, -54); ctx.fill(); }
  ctx.restore();
}
function sun(x, y, r, t) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(t * .6);
  ctx.fillStyle = C.yel;
  for (let i = 0; i < 12; i++) { ctx.rotate(Math.PI / 6); ctx.beginPath(); ctx.moveTo(-9, r + 10); ctx.lineTo(0, r + 36 + Math.sin(t * 4 + i) * 6); ctx.lineTo(9, r + 10); ctx.fill(); }
  ctx.restore();
  const g = ctx.createRadialGradient(x - r * .3, y - r * .3, 4, x, y, r); g.addColorStop(0, '#FFF3B0'); g.addColorStop(1, '#FFC21A');
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
}
function magnifier(x, y, s, col = C.red) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.strokeStyle = col; ctx.lineWidth = 6; ctx.lineCap = 'round';
  ctx.fillStyle = 'rgba(255,255,255,.95)'; ctx.beginPath(); ctx.arc(-4, -4, 13, 0, 7); ctx.fill(); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(6, 6); ctx.lineTo(17, 17); ctx.stroke();
  ctx.fillStyle = C.yel; ctx.font = F(800, 13); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = C.navy; ctx.fillText('?', -4, -3);
  ctx.restore();
}
function pin(x, y, s, col = C.red) { // punta en (x,y)
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  shadow(true, 10, 4);
  ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(0, 0);
  ctx.bezierCurveTo(-8, -18, -24, -30, -24, -48); ctx.arc(0, -48, 24, Math.PI, 0); ctx.bezierCurveTo(24, -30, 8, -18, 0, 0); ctx.fill();
  shadow(false);
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(0, -48, 9, 0, 7); ctx.fill();
  ctx.restore();
}
function arrowUp(x, y, len, t, a) { // flecha ondulada hacia arriba (evaporación)
  ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = '#fff'; ctx.lineWidth = 7; ctx.lineCap = 'round';
  ctx.beginPath();
  for (let i = 0; i <= 16; i++) { const yy = y - i * len / 16; const xx = x + Math.sin(i * .8 + t * 6) * 9; i ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); }
  ctx.stroke();
  const tx = x + Math.sin(16 * .8 + t * 6) * 9, ty = y - len;
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.moveTo(tx, ty - 16); ctx.lineTo(tx - 14, ty + 4); ctx.lineTo(tx + 14, ty + 4); ctx.fill();
  ctx.restore();
}
function cursorArrow(x, y, s) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  shadow(true, 10, 4);
  ctx.fillStyle = '#fff'; ctx.strokeStyle = '#111'; ctx.lineWidth = 3;
  poly([[0, 0], [0, 52], [13, 40], [23, 62], [32, 58], [22, 37], [40, 37]]); ctx.fill(); shadow(false); ctx.stroke();
  ctx.restore();
}
function heart(x, y, s, col = C.red) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.fillStyle = col;
  ctx.beginPath(); ctx.moveTo(0, 8); ctx.bezierCurveTo(-22, -6, -12, -26, 0, -12); ctx.bezierCurveTo(12, -26, 22, -6, 0, 8); ctx.fill();
  ctx.restore();
}
function shieldIcon(x, y, s) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.fillStyle = C.green; ctx.beginPath(); ctx.moveTo(0, -26); ctx.lineTo(22, -18); ctx.lineTo(20, 6); ctx.quadraticCurveTo(14, 20, 0, 28); ctx.quadraticCurveTo(-14, 20, -20, 6); ctx.lineTo(-22, -18); ctx.closePath(); ctx.fill();
  check(0, 0, 22, '#fff', 6);
  ctx.restore();
}

// ---------- altímetro ----------
function altitude(t) {
  const K = [
    [0, 0], [S(3) - .1, 0], [S(3) + .45, 3098, 'eo'], [S(8) - .12, 3098], [S(8) + .45, -45, 'eo'],
    [S(13), -45], [S(13) + .5, 0, 'eio'],
    [S(24) + .25, 0], [E(36), 3098, 'eio'],
    [S(54), 3098], [S(68) + .05, 0, 'ei'], [S(68) + .95, -45, 'eo'],
    [S(136) - .1, -45], [S(136) + .9, 3098, 'eio'], [S(140) - .1, 3098], [S(140) + .9, -45, 'eio'],
  ];
  if (t <= K[0][0]) return K[0][1];
  for (let i = 1; i < K.length; i++) {
    if (t <= K[i][0]) { const [t0, v0] = K[i - 1], [t1, v1, e = 'lin'] = K[i]; return lerp(v0, v1, EASE[e]((t - t0) / (t1 - t0))); }
  }
  return K[K.length - 1][1];
}
const fmtAlt = a => { const r = Math.round(a); if (r === 0) return '0 m'; return (r > 0 ? '+' : '−') + Math.abs(r).toLocaleString('en-US') + ' m'; };
const altY = a => a >= 0 ? 1140 - a / 3200 * 790 : 1140 + (-a) / 50 * 150;
function drawAltimeter(t) {
  const a = altitude(t); const moving = Math.abs(altitude(t + .05) - a) > 1;
  // tubo
  rr(30, 312, 160, 1000, 26); ctx.fillStyle = 'rgba(6,24,58,.62)'; ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.22)'; ctx.lineWidth = 3; ctx.stroke();
  rr(58, 340, 34, 950, 17); ctx.fillStyle = 'rgba(255,255,255,.12)'; ctx.fill();
  const y0 = altY(0), ya = altY(a);
  ctx.save(); rr(58, 340, 34, 950, 17); ctx.clip();
  if (a > 0) { const g = ctx.createLinearGradient(0, ya, 0, y0); g.addColorStop(0, C.red); g.addColorStop(1, C.yel); ctx.fillStyle = g; ctx.fillRect(58, ya, 34, y0 - ya); }
  else if (a < 0) { ctx.fillStyle = '#21B8C6'; ctx.fillRect(58, y0, 34, ya - y0); }
  ctx.restore();
  for (const [v, lab] of [[3000, '3000'], [2000, '2000'], [1000, '1000'], [0, '0'], [-50, '−50']]) {
    const y = altY(v);
    ctx.strokeStyle = v === 0 ? '#fff' : 'rgba(255,255,255,.6)'; ctx.lineWidth = v === 0 ? 4 : 3;
    ctx.beginPath(); ctx.moveTo(92, y); ctx.lineTo(108, y); ctx.stroke();
    text(lab, 112, y, { w: 700, size: 24, align: 'left', color: v === 0 ? C.yel : 'rgba(255,255,255,.85)' });
  }
  // mini íconos
  withT(75, 326, 1, () => { ctx.fillStyle = '#fff'; poly([[-14, 8], [0, -10], [14, 8]]); ctx.fill(); });
  // marcador
  const pr = 22 + (moving ? 3 * Math.sin(t * 30) : 2 * Math.sin(t * 5));
  shadow(true, 14, 3, 'rgba(255,75,85,.7)');
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(75, ya, pr, 0, 7); ctx.fill(); shadow(false);
  ctx.strokeStyle = C.red; ctx.lineWidth = 6; ctx.stroke();
  ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(75, ya, 8, 0, 7); ctx.fill();
  // lectura
  const glow = .5 + .5 * Math.sin(t * 4);
  const shake = moving ? Math.sin(t * 60) * 2 : 0;
  rr(24, 160, 420, 132, 24); ctx.fillStyle = 'rgba(6,24,58,.88)'; ctx.fill();
  ctx.strokeStyle = `rgba(255,75,85,${.7 + .3 * glow})`; ctx.lineWidth = 5; ctx.stroke();
  text('ALTÍMETRO', 48, 190, { w: 700, size: 24, align: 'left', color: C.cream, ls: 3 });
  const col = a >= 3000 ? C.yel : a <= -40 ? '#5FE3EE' : '#fff';
  text(fmtAlt(a), 48 + shake, 248, { w: 400, fam: 'Archivo Black', size: 62, align: 'left', color: col, maxW: 370 });
  let st = '';
  if (a >= 3090) st = 'CIMA'; else if (Math.abs(a) < 1) st = 'NIVEL DEL MAR'; else if (a <= -44) st = 'BAJO EL MAR';
  if (st) { ctx.font = F(800, 20); const w = ctx.measureText(st).width + 22; pill(424 - w / 2, 190, w, 32, C.red); text(st, 424 - w / 2, 191, { w: 800, size: 20 }); }
}

// ---------- fondo (la "cámara" viaja con la altitud) ----------
const CLOUDS = (() => { const r = seeded(11); return Array.from({ length: 18 }, () => ({ alt: 400 + r() * 3800, x: r() * 1400 - 160, s: .7 + r() * .9, v: 12 + r() * 30, a: .35 + r() * .5 })); })();
const DOTS = (() => { const r = seeded(5); return Array.from({ length: 50 }, () => ({ x: r() * W, y: r() * H, v: 10 + r() * 30, r: 1.5 + r() * 3 })); })();
function bgAltitude(t) {
  if (t < B[2]) return 1500 + altitude(t) * .52 + Math.sin(t * .7) * 60;
  return altitude(t);
}
function drawBG(t) {
  const A = bgAltitude(t);
  const f = clamp(A / 1800);
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, f > .5 ? C.navy : '#123A73');
  g.addColorStop(.6, `rgb(${lerp(46, 22, f)},${lerp(104, 64, f)},${lerp(170, 124, f)})`);
  g.addColorStop(1, `rgb(${lerp(110, 30, f)},${lerp(170, 80, f)},${lerp(220, 150, f)})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  for (const d of DOTS) { const y = ((d.y - t * d.v) % H + H) % H; ctx.fillStyle = 'rgba(255,255,255,.18)'; ctx.beginPath(); ctx.arc(d.x, y, d.r, 0, 7); ctx.fill(); }
  for (const c of CLOUDS) {
    const y = 960 + (A - c.alt) * .42; if (y < -150 || y > H + 150) continue;
    const x = ((c.x + t * c.v) % 1400 + 1400) % 1400 - 200;
    cloud(x, y, c.s, c.a);
  }
  // nivel del mar y cuenca del lago
  const k = 12.7; const seaY = 900 + A * k, lakeY = 900 + (A + 45) * k;
  if (seaY < H + 300) {
    ctx.fillStyle = '#B9824E';
    poly([[0, seaY - 30], [140, seaY], [250, lakeY - 140], [330, lakeY + 30], [0, lakeY + 30]]); ctx.fill();
    poly([[W, seaY - 30], [W - 140, seaY], [W - 230, lakeY - 150], [W - 320, lakeY + 30], [W, lakeY + 30]]); ctx.fill();
    ctx.fillStyle = 'rgba(120,70,30,.35)';
    poly([[0, seaY + 60], [170, seaY + 90], [240, lakeY - 120], [0, lakeY - 60]]); ctx.fill();
    poly([[W, seaY + 80], [W - 160, seaY + 100], [W - 220, lakeY - 130], [W, lakeY - 70]]); ctx.fill();
    water(0, lakeY, W, Math.max(10, H - lakeY + 40), t);
    const r = seeded(9);
    for (let i = 0; i < 16; i++) { const bx = r() * W, sp = 40 + r() * 60; const by = H - ((t * sp + r() * 900) % Math.max(1, H - lakeY)); if (by > lakeY + 20) { ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(bx + Math.sin(t * 3 + i) * 8, by, 5 + r() * 7, 0, 7); ctx.stroke(); } }
    // línea del nivel del mar
    ctx.setLineDash([26, 16]); ctx.lineDashOffset = -t * 60; ctx.strokeStyle = '#fff'; ctx.lineWidth = 5;
    ctx.beginPath(); ctx.moveTo(0, seaY); ctx.lineTo(W, seaY); ctx.stroke(); ctx.setLineDash([]);
    if (seaY > 300 && seaY < 1330 && !(t > B[6] && t < B[7])) alpha(clamp((seaY - 300) / 40), () => {
      ctx.font = F(800, 26); const tw = ctx.measureText('NIVEL DEL MAR · 0 m').width + 30;
      pill(1050 - tw / 2, seaY - 30, tw, 42, 'rgba(6,24,58,.8)');
      text('NIVEL DEL MAR · 0 m', 1050 - tw / 2, seaY - 29, { w: 800, size: 26, color: '#fff' });
    });
  }
}

// ---------- transición franja bandera ----------
function wipe(t, b) {
  const p = (t - (b - .35)) / .7; if (p <= 0 || p >= 1) return;
  const gx = lerp(1080 + 320, -1800 - 320, eio(p));
  ctx.save(); ctx.translate(gx, 0);
  const sk = 320; const parts = [[0, 700, C.drBlue], [700, 400, '#fff'], [1100, 700, C.drRed]];
  for (const [x, w, c] of parts) { ctx.fillStyle = c; poly([[x + sk, 0], [x + w + sk, 0], [x + w, H], [x, H]]); ctx.fill(); }
  ctx.restore();
}

// ---------- ESCENA 1: GANCHO ----------
function scene1(t) {
  const tp = pop(t, -.18, .5), bp = pop(t, -.12, .5);
  const pulseTop = 1 + .05 * bump(t, S(3) - .05, .45), pulseBot = 1 + .05 * bump(t, S(8) - .05, .45);
  const zoom = 1 + .03 * (t / B[1]);
  withT(628, 535, tp * pulseTop * zoom, () => {
    ctx.save(); rr(-418, -235, 836, 470, 34); ctx.clip();
    const g = ctx.createLinearGradient(0, -235, 0, 235); g.addColorStop(0, '#4FA6E8'); g.addColorStop(1, '#CFE9FB');
    ctx.fillStyle = g; ctx.fillRect(-418, -235, 836, 470);
    sun(300, -150, 40, t);
    mountain(20, 235, 760, 400, 1, t);
    cloud(-380 + ((t * 45) % 900), -60, .8, .9); cloud(200 - ((t * 30) % 900), 40, .6, .8);
    ctx.restore();
    rr(-418, -235, 836, 470, 34); ctx.strokeStyle = '#fff'; ctx.lineWidth = 6; ctx.stroke();
    pill(-245, -185, 300, 62, C.navy);
    rich([['LO MÁS ', '#fff'], ['ALTO', C.yel]], -245, -183, { w: 800, size: 34 });
  });
  withT(628, 1065, bp * pulseBot * zoom, () => {
    ctx.save(); rr(-418, -235, 836, 470, 34); ctx.clip();
    ctx.fillStyle = '#D9B27C'; ctx.fillRect(-418, -235, 836, 470);
    ctx.fillStyle = '#B9824E'; poly([[-418, -235], [-250, -120], [-150, -20], [-418, 0]]); ctx.fill();
    poly([[418, -235], [260, -110], [150, -20], [418, 0]]); ctx.fill();
    water(-418, -10, 836, 260, t);
    const cx = -500 + ((t * 120) % 1200);
    croc(cx, 30, .9, t, 1);
    waterVeil(-418, 30, 836, 230, t);
    ctx.restore();
    rr(-418, -235, 836, 470, 34); ctx.strokeStyle = '#fff'; ctx.lineWidth = 6; ctx.stroke();
    pill(-245, 185, 300, 62, C.navy);
    rich([['LO MÁS ', '#fff'], ['BAJO', C.yel]], -245, 187, { w: 800, size: 34 });
  });
  // flecha + pregunta
  const ap = prog(t, S(13) - .05, .45);
  const flagT = S(18) - .1;
  if (ap > 0 && t < flagT + .3) alpha(1 - prog(t, flagT, .3), () => {
    ctx.strokeStyle = C.yel; ctx.lineWidth = 12; ctx.lineCap = 'round';
    const y1 = 420, y2 = lerp(420, 1180, eo(ap));
    ctx.beginPath(); ctx.moveTo(990, y1); ctx.lineTo(990, y2); ctx.stroke();
    ctx.fillStyle = C.yel;
    poly([[990, 384], [964, 430], [1016, 430]]); ctx.fill();
    if (ap >= 1) { poly([[990, 1216], [964, 1170], [1016, 1170]]); ctx.fill(); }
    const s = pop(t, S(13), .45) * (1 + .04 * Math.sin(t * 9));
    withT(600, 795, s, () => {
      shadow(true, 20, 8); pill(0, 0, 640, 104, C.red); shadow(false);
      text('¿EN EL MISMO PAÍS?', 0, 3, { w: 400, fam: 'Archivo Black', size: 50, maxW: 590 });
    }, -.03);
  });
  // bandera: "el nuestro"
  if (t > flagT) {
    const fp = pop(t, flagT, .55);
    alpha(prog(t, flagT, .3) * .72, () => { ctx.fillStyle = C.ink; ctx.fillRect(200, 290, 880, 1030); });
    withT(628, 760, fp * (1 + .03 * Math.sin(t * 3)), () => {
      shadow(true, 30, 10); ctx.fillStyle = 'rgba(0,0,0,.01)'; ctx.fillRect(-270, -180, 540, 360); shadow(false);
      flag(-270, -180, 540, 360, t, .07);
    });
    const tp2 = pop(t, S(23) - .1, .45);
    withT(628, 1060, tp2, () => rich([['¡ES EL ', '#fff'], ['NUESTRO!', C.yel]], 0, 0, { w: 400, fam: 'Archivo Black', size: 76, stroke: C.ink, sw: 14, maxW: 800 }));
  }
}

// ---------- ESCENA 2: PICO DUARTE ----------
const TRAIL = [[330, 1290], [560, 1170], [430, 1050], [620, 930], [520, 820], [650, 700], [640, 562]];
function trailPos(u) {
  const L = []; let tot = 0;
  for (let i = 1; i < TRAIL.length; i++) { const d = Math.hypot(TRAIL[i][0] - TRAIL[i - 1][0], TRAIL[i][1] - TRAIL[i - 1][1]); L.push(d); tot += d; }
  let d = u * tot;
  for (let i = 0; i < L.length; i++) { if (d <= L[i] || i === L.length - 1) { const f = clamp(d / L[i]); return [lerp(TRAIL[i][0], TRAIL[i + 1][0], f), lerp(TRAIL[i][1], TRAIL[i + 1][1], f), i]; } d -= L[i]; }
}
function scene2(t) {
  const t0 = B[1]; const lp = prog(t, t0, B[2] - t0);
  const grow = back(prog(t, t0 + .05, .85));
  withT(628, 900, 1 + .05 * lp, () => {
    ctx.translate(-628, -900);
    mountain(640, 1322, 880, 760, grow, t);
    // nubes delante
    cloud(150 + ((t - t0) * 50) % 1100 - 100, 980, 1.0, .85);
    cloud(900 - ((t - t0) * 38) % 1100, 760, .8, .8);
    // sendero + excursionista
    const hs = t0 + .95, he = E(36) - .05;
    const u = eio(prog(t, hs, he - hs));
    if (t > hs - .3 && grow > .95) {
      ctx.setLineDash([10, 12]); ctx.strokeStyle = 'rgba(255,255,255,.75)'; ctx.lineWidth = 5; ctx.beginPath();
      const [hx, hy, seg] = trailPos(u);
      ctx.moveTo(TRAIL[0][0], TRAIL[0][1]); for (let i = 1; i <= seg; i++) ctx.lineTo(TRAIL[i][0], TRAIL[i][1]); ctx.lineTo(hx, hy); ctx.stroke(); ctx.setLineDash([]);
      const arrived = t >= he;
      if (arrived) { const pp = back(prog(t, he, .5)); withT(640, 562, 1, () => flagPole(0, 0, 150 * pp, 110, t)); }
      hiker(arrived ? 600 : hx, arrived ? 566 : hy, 1.15, t, !arrived && t > hs, arrived);
    }
  });
  // "+3,000 m"
  const bp = pop(t, S(32) - .05, .45);
  if (bp > 0) withT(880, 640, bp * (1 + .03 * Math.sin(t * 6)), () => {
    shadow(true); pill(0, 0, 290, 92, C.red); shadow(false);
    text('+3,000 m', 0, 3, { w: 400, fam: 'Archivo Black', size: 48, maxW: 250 });
  });
  // TECHO DEL CARIBE
  const tp = pop(t, S(40) - .1, .5);
  if (tp > 0) withT(628, 375, tp, () => {
    shadow(true, 24, 8); rr(-400, -50, 800, 100, 22); ctx.fillStyle = C.yel; ctx.fill(); shadow(false);
    text('TECHO DEL CARIBE', 0, 4, { w: 400, fam: 'Archivo Black', size: 62, color: C.navy, maxW: 740 });
  }, Math.sin(t * 2) * .015);
  // Nº1 DEL CARIBE
  const sp = pop(t, S(48) - .05, .5);
  if (sp > 0) withT(880, 930, sp * (1 + .04 * Math.sin(t * 5)), () => {
    shadow(true); ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(0, 0, 105, 0, 7); ctx.fill(); shadow(false);
    ctx.strokeStyle = '#fff'; ctx.lineWidth = 5; ctx.setLineDash([8, 7]); ctx.beginPath(); ctx.arc(0, 0, 90, 0, 7); ctx.stroke(); ctx.setLineDash([]);
    text('Nº 1', 0, -18, { w: 400, fam: 'Archivo Black', size: 58 });
    text('DEL CARIBE', 0, 36, { w: 800, size: 24, color: C.yel });
  }, -.2);
}

// ---------- ESCENA 3: TRIVIA ----------
const OPTS = [['A', 'Valle del Cibao'], ['B', 'Lago Enriquillo'], ['C', 'Bahía de Samaná']];
function scene3(t) {
  const t0 = B[2]; const reveal = S(70) - .05; const exitT = S(71) + .45;
  // charco con el ojo del cocodrilo (pista)
  if (t < B[3] + .5) {
    const py = 1185 + 160 * ei(prog(t, B[3] - .2, .6)) + 160 * (1 - eo(prog(t, t0 + .2, .5)));
    ctx.save(); ctx.beginPath(); ctx.rect(196, 0, 884, 1335); ctx.clip();
    const rise = 60 * eo(prog(t, S(67) - .35, .6)) + Math.sin(t * 3) * 4;
    water(196, py, 884, 200, t);
    if (rise > 1) { crocEyes(780, py + 40, 1, rise, t); waterVeil(196, py + 18, 884, 200, t); }
    ctx.restore();
    const pp = pop(t, S(65) - .05, .4);
    if (pp > 0) withT(470, py - 60, pp, () => {
      pill(0, 0, 210, 66, C.yel); text('PISTA', -18, 3, { w: 400, fam: 'Archivo Black', size: 34, color: C.navy });
      ctx.fillStyle = C.navy; poly([[62, -14], [88, 0], [62, 14]]); ctx.fill();
    });
  }
  // tarjeta
  const cin = back(prog(t, t0, .55));
  const cy = lerp(-700, 0, cin) - 1100 * ei(prog(t, exitT, .45));
  if (cy < -1000) return;
  withT(628, 690 + cy, 1 + .015 * Math.sin(t * 2.5), () => {
    shadow(true, 30, 12); rr(-410, -360, 820, 730, 34); ctx.fillStyle = C.cream; ctx.fill(); shadow(false);
    ctx.save(); rr(-410, -360, 820, 730, 34); ctx.clip(); ctx.fillStyle = C.red; ctx.fillRect(-410, -360, 820, 96); ctx.restore();
    flag(-380, -340, 66, 44, t, .08);
    text('TRIVIA DOMINICANA', 20, -310, { w: 400, fam: 'Archivo Black', size: 44, maxW: 560 });
    text('¿DÓNDE ESTÁ EL PUNTO', 0, -200, { w: 800, size: 44, color: C.navy, maxW: 740 });
    rich([['MÁS ', C.navy], ['BAJO', C.red], [' DEL CARIBE?', C.navy]], 0, -140, { w: 800, size: 44, maxW: 740 });
    OPTS.forEach(([L, name], i) => {
      const op = back(prog(t, S(56) + i * .18, .45)); if (op <= 0) return;
      const y = -30 + i * 122; const ok = i === 1 && t >= reveal; const dim = i !== 1 && t >= reveal;
      withT(lerp(500, 0, op), y, ok ? 1 + .05 * bump(t, reveal, .5) : 1, () => alpha(dim ? .38 : 1, () => {
        rr(-370, -48, 740, 96, 48); ctx.fillStyle = ok ? C.green : '#fff'; ctx.fill();
        ctx.strokeStyle = ok ? C.green : 'rgba(11,42,91,.25)'; ctx.lineWidth = 4; ctx.stroke();
        ctx.fillStyle = ok ? '#fff' : C.navy; ctx.beginPath(); ctx.arc(-320, 0, 34, 0, 7); ctx.fill();
        text(L, -320, 2, { w: 400, fam: 'Archivo Black', size: 36, color: ok ? C.green : '#fff' });
        text(name, -265, 2, { w: 700, size: 42, color: ok ? '#fff' : C.navy, align: 'left', maxW: 520 });
        if (ok) check(320, 0, 44, '#fff', 10);
      }));
    });
    // cuenta regresiva
    const cs = S(62) - .2; const n = 3 - Math.floor((t - cs) / .75);
    if (t > cs - .1) {
      const s = pop(t, cs - .1, .35);
      withT(350, -350, s, () => {
        shadow(true); ctx.fillStyle = C.navy; ctx.beginPath(); ctx.arc(0, 0, 66, 0, 7); ctx.fill(); shadow(false);
        const fr = t < cs + 2.25 ? 1 - ((t - cs) % .75) / .75 : 0;
        ctx.strokeStyle = C.yel; ctx.lineWidth = 9; ctx.beginPath(); ctx.arc(0, 0, 56, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * fr); ctx.stroke();
        const lab = t < cs ? '3' : n >= 1 ? String(n) : (t >= reveal ? '✓' : '?');
        if (lab === '✓') check(0, 0, 50, C.green, 11);
        else { const k = 1 + .25 * (1 - clamp(((t - cs) % .75) / .25)); withT(0, 2, k, () => text(lab, 0, 0, { w: 400, fam: 'Archivo Black', size: 64, color: '#fff' })); }
      });
    }
  });
}

// ---------- ESCENA 4: LAGO ENRIQUILLO ----------
function scene4(t) {
  const tt = S(71) + .85;
  const tp = pop(t, tt, .5);
  if (tp > 0) withT(628, 450, tp * (1 + .02 * Math.sin(t * 3)), () => {
    shadow(true, 24, 8); rr(-400, -56, 800, 112, 24); ctx.fillStyle = C.navy; ctx.fill(); shadow(false);
    ctx.strokeStyle = C.yel; ctx.lineWidth = 5; ctx.stroke();
    rich([['LAGO ', '#fff'], ['ENRIQUILLO', C.yel]], 0, 4, { w: 400, fam: 'Archivo Black', size: 64, maxW: 740 });
  });
  // medalla
  const mIn = pop(t, S(75) - .1, .55), mOut = ei(prog(t, S(79) - .05, .35));
  const ms = mIn * (1 - mOut);
  if (ms > 0.01) withT(628, 700, ms, () => {
    ctx.fillStyle = C.red; poly([[-60, 40], [-110, 190], [-70, 170], [-45, 205], [-10, 60]]); ctx.fill();
    ctx.fillStyle = '#C93440'; poly([[60, 40], [110, 190], [70, 170], [45, 205], [10, 60]]); ctx.fill();
    shadow(true, 24, 8);
    const g = ctx.createRadialGradient(-30, -30, 10, 0, 0, 120); g.addColorStop(0, '#FFF1A8'); g.addColorStop(1, '#E8A90C');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, 112, 0, 7); ctx.fill(); shadow(false);
    ctx.strokeStyle = '#B07800'; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, 94, 0, 7); ctx.stroke();
    withT(0, 0, 1, () => text('Nº 1', 0, 4, { w: 400, fam: 'Archivo Black', size: 70, color: C.navy }), Math.sin(t * 3) * .06);
  });
  if (ms > 0.01) withT(628, 905, ms, () => {
    shadow(true); rr(-330, -62, 660, 124, 20); ctx.fillStyle = C.red; ctx.fill(); shadow(false);
    text('LAGO MÁS GRANDE', 0, -24, { w: 400, fam: 'Archivo Black', size: 42, maxW: 600 });
    text('DE LAS ANTILLAS', 0, 28, { w: 800, size: 38, color: C.yel, maxW: 600 });
  });
  // profundidad
  const bp = eo(prog(t, S(80) - .1, .8));
  if (bp > 0) {
    const y1 = 329, y2 = lerp(y1, 900, bp);
    ctx.strokeStyle = C.yel; ctx.lineWidth = 7; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(960, y1); ctx.lineTo(990, y1); ctx.lineTo(990, y2); ctx.lineTo(960, y2); ctx.stroke();
    for (let i = 0; i < 3; i++) { const yy = lerp(y1 + 60, y2 - 30, ((t * .8 + i / 3) % 1)); alpha(bp, () => { ctx.fillStyle = C.yel; poly([[975, yy + 18], [957, yy - 6], [993, yy - 6]].map(([x, y]) => [x + 15, y])); ctx.fill(); }); }
  }
  const dp = pop(t, S(83) - .1, .5);
  if (dp > 0) withT(590, 650, dp * (1 + .02 * Math.sin(t * 4)), () => {
    shadow(true, 24, 8); rr(-330, -120, 660, 240, 30); ctx.fillStyle = 'rgba(6,24,58,.88)'; ctx.fill(); shadow(false);
    text('ENTRE', 0, -78, { w: 800, size: 30, color: C.cream, ls: 4 });
    text('40 Y 50 m', 0, -8, { w: 400, fam: 'Archivo Black', size: 80, color: C.yel, maxW: 600 });
    alpha(prog(t, S(88) - .15, .3), () => text('BAJO EL NIVEL DEL MAR', 0, 66, { w: 800, size: 34, maxW: 600 }));
  });
}

// ---------- ESCENA 5: AGUA SALADA ----------
function scene5(t) {
  const t0 = B[4]; const outT = S(103) - .1;
  const cin = pop(t, t0 + .05, .5), cout = ei(prog(t, outT, .4));
  const cs = cin * (1 - cout);
  if (cs > .01) withT(628, 640, cs, () => {
    shadow(true, 30, 12); rr(-400, -300, 800, 600, 34); ctx.fillStyle = C.cream; ctx.fill(); shadow(false);
    text('MEDIDOR DE SALINIDAD', 0, -248, { w: 400, fam: 'Archivo Black', size: 42, color: C.navy, maxW: 720 });
    const base = 210, maxH = 360;
    const fm = eo(prog(t, S(95) - .1, 1.0)) * .52 + .015 * Math.sin(t * 5);
    const fl = eo(prog(t, S(97) - .1, 1.3)) * .96 + .015 * Math.sin(t * 6 + 1);
    [[-170, fm, '#3F8FE0', 'MAR'], [170, fl, C.red, 'LAGO']].forEach(([x, f, col, lab]) => {
      rr(x - 75, base - maxH, 150, maxH, 20); ctx.fillStyle = 'rgba(11,42,91,.12)'; ctx.fill();
      const h = maxH * clamp(f);
      if (h > 2) { rr(x - 75, base - h, 150, h, 20); ctx.fillStyle = col; ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,.85)'; for (let i = 0; i < 6; i++) { const yy = base - ((t * 40 + i * 60) % Math.max(1, h)); ctx.fillRect(x - 40 + (i % 3) * 30, yy, 10, 10); } }
      text(lab, x, base + 44, { w: 400, fam: 'Archivo Black', size: 40, color: C.navy });
    });
    const wp = pop(t, S(98) - .05, .45);
    if (wp > 0) withT(170, -150, wp, () => {
      shadow(true); pill(0, 0, 300, 76, C.yel); shadow(false);
      text('MÁS SALADA', 0, 3, { w: 400, fam: 'Archivo Black', size: 36, color: C.navy, maxW: 270 });
    }, -.08 + Math.sin(t * 6) * .03);
  });
  // sin salida
  const sIn = pop(t, S(106) - .2, .5), sOut = ei(prog(t, S(109) - .05, .35));
  const ss = sIn * (1 - sOut);
  if (ss > .01) withT(628, 610, ss, () => {
    shadow(true, 24, 8); ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(0, 0, 150, 0, 7); ctx.fill(); shadow(false);
    ctx.strokeStyle = C.red; ctx.lineWidth = 26; ctx.beginPath(); ctx.arc(0, 0, 124, 0, 7); ctx.stroke();
    ctx.fillStyle = C.teal; rr(-80, -26, 120, 52, 10); ctx.fill(); poly([[40, -52], [100, 0], [40, 52]]); ctx.fill();
    ctx.strokeStyle = C.red; ctx.lineWidth = 26; ctx.beginPath(); ctx.moveTo(-88, -88); ctx.lineTo(88, 88); ctx.stroke();
    const tp = pop(t, S(108) - .1, .4);
    withT(0, 220, tp, () => { shadow(true); pill(0, 0, 420, 90, C.red); shadow(false); text('SIN SALIDA', 0, 3, { w: 400, fam: 'Archivo Black', size: 50 }); });
  }, Math.sin(t * 4) * .03);
  // evaporación
  const eIn = prog(t, S(109) - .1, .5);
  if (eIn > 0) {
    withT(915, 560, back(eIn), () => sun(0, 0, 66, t));
    for (let i = 0; i < 5; i++) {
      const ph = ((t - S(109)) * .55 + i * .2) % 1;
      arrowUp(330 + i * 120, 880 - ph * 200, 170, t + i, eIn * Math.sin(Math.PI * ph));
    }
    const vp = pop(t, S(115) - .15, .5);
    if (vp > 0) withT(500, 440, vp * (1 + .03 * Math.sin(t * 5)), () => {
      shadow(true, 20, 8); rr(-290, -50, 580, 100, 22); ctx.fillStyle = C.yel; ctx.fill(); shadow(false);
      text('EVAPORACIÓN', 0, 4, { w: 400, fam: 'Archivo Black', size: 52, color: C.navy, maxW: 540 });
    });
    const r = seeded(21);
    for (let i = 0; i < 14; i++) { const ap = prog(t, S(111) + i * .12, .3); if (ap <= 0) continue; const side = i % 2 ? 1 : 0; const x = side ? 800 + r() * 50 : 240 + r() * 60; const y = 840 + r() * 40; withT(x, y, ap, () => { ctx.fillStyle = '#fff'; ctx.fillRect(-7, -7, 14, 14); }, .6); }
  }
}

// ---------- ESCENA 6: ANIMALES ----------
function tag(x, y, label, bg, fg, s) {
  if (s <= 0) return;
  withT(x, y, s, () => {
    ctx.font = F(800, 32); const w = ctx.measureText(label).width + 48;
    shadow(true, 14, 5); pill(0, 0, w, 64, bg); shadow(false);
    text(label, 0, 2, { w: 800, size: 32, color: fg });
  });
}
function scene6(t) {
  const t0 = B[5];
  const hp = pop(t, t0 + .05, .45);
  withT(628, 405, hp * (1 + .02 * Math.sin(t * 3)), () => {
    shadow(true); pill(0, 0, 560, 84, C.red); shadow(false);
    text('¿QUIÉN VIVE AHÍ?', 0, 3, { w: 400, fam: 'Archivo Black', size: 44, maxW: 520 });
  });
  // cocodrilo
  const ct = S(118) - .35;
  if (t > ct) {
    const x = lerp(1250, 520, eo(prog(t, ct, 1.0))) + Math.sin(t * 1.3) * 18;
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, 1340); ctx.clip();
    croc(x, 905 + Math.sin(t * 2) * 4, .95, t, -1); waterVeil(0, 905, W, 90, t);
    ctx.restore();
    tag(480, 790, 'COCODRILO AMERICANO', C.yel, C.navy, pop(t, S(119) - .1, .4));
  }
  // flamenco
  const ft = S(120) - .3;
  if (t > ft) {
    const fx = lerp(1200, 870, eo(prog(t, ft, .9)));
    flamingo(fx, 915, 1.0, t);
    waterVeil(0, 905, W, 70, t);
    tag(880, 505, 'FLAMENCO', '#FF8FB1', C.navy, pop(t, S(120) + .1, .4));
  }
  // iguanas
  const it = S(122) - .25;
  if (t > it) {
    const cy = lerp(1600, 1150, back(prog(t, it, .6)));
    withT(628, cy, 1, () => {
      shadow(true, 30, 12); rr(-410, -175, 820, 350, 30); ctx.fillStyle = C.cream; ctx.fill(); shadow(false);
      ctx.fillStyle = '#E3D2B0'; rr(-410, 40, 820, 135, 30); ctx.fill();
      shieldIcon(-300, -130, 1.3 * (1 + .08 * bump(t, S(125) - .1, .5)));
      rich([['2 ', C.navy], ['IGUANAS', C.red], [' PROTEGIDAS', C.navy]], 30, -128, { w: 400, fam: 'Archivo Black', size: 40, maxW: 600 });
      const r1 = prog(t, S(128) - .1, .5), r2 = prog(t, S(133) - .1, .5);
      withT(-200, 60, .95 * (1 + .1 * bump(t, S(128) - .1, .4)), () => iguana(0, 0, 1, t, 'ricord', r1 < .5 ? 1 : 0));
      withT(205, 60, .95 * (1 + .1 * bump(t, S(133) - .1, .4)), () => iguana(0, 0, 1, t + 1, 'rino', r2 < .5 ? 1 : 0));
      if (r1 < .5) text('?', -190, -40, { w: 400, fam: 'Archivo Black', size: 50, color: '#fff' });
      if (r2 < .5) text('?', 215, -40, { w: 400, fam: 'Archivo Black', size: 50, color: '#fff' });
    });
    tag(428, cy + 128, 'IGUANA DE RICORD', C.navy, '#fff', pop(t, S(130) - .2, .4) * .82);
    tag(833, cy + 128, 'IGUANA RINOCERONTE', C.navy, '#fff', pop(t, S(134) - .25, .4) * .82);
  }
}

// ---------- ESCENA 7: MAPA ----------
const ISL = [[-73.40, 19.85], [-73.0, 19.93], [-72.75, 19.94], [-72.2, 19.77], [-71.73, 19.73],
  [-71.3, 19.86], [-70.98, 19.9], [-70.7, 19.8], [-70.3, 19.67], [-69.95, 19.68], [-69.8, 19.47], [-69.6, 19.33], [-69.25, 19.36], [-69.13, 19.30], [-69.45, 19.19], [-69.62, 19.10], [-69.30, 19.08], [-69.0, 19.02], [-68.75, 18.95], [-68.45, 18.75], [-68.33, 18.60], [-68.42, 18.40], [-68.70, 18.20], [-68.90, 18.38], [-69.25, 18.43], [-69.65, 18.45], [-69.95, 18.43], [-70.20, 18.24], [-70.50, 18.20], [-70.65, 18.35], [-70.95, 18.27], [-71.10, 18.10], [-71.25, 17.85], [-71.42, 17.60], [-71.62, 17.75], [-71.73, 18.03],
  [-72.05, 18.23], [-72.55, 18.20], [-73.10, 18.15], [-73.75, 18.18], [-74.20, 18.30], [-74.47, 18.45], [-74.25, 18.62], [-73.90, 18.62], [-73.40, 18.53], [-72.80, 18.45], [-72.35, 18.55], [-72.55, 18.85], [-72.80, 19.10], [-72.75, 19.42], [-73.10, 19.55], [-73.45, 19.68]];
const BORDER = [[-71.73, 19.73], [-71.65, 19.45], [-71.75, 19.25], [-71.65, 19.05], [-71.80, 18.85], [-71.95, 18.62], [-71.85, 18.45], [-71.72, 18.30], [-71.73, 18.03]];
const MX = lon => 238 + (lon + 74.6) * 124, MY = lat => 600 + (20.0 - lat) * 130;
function mapPoly(pts) { ctx.beginPath(); pts.forEach(([lo, la], i) => i ? ctx.lineTo(MX(lo), MY(la)) : ctx.moveTo(MX(lo), MY(la))); ctx.closePath(); }
function scene7(t) {
  const t0 = B[6];
  const hp = pop(t, t0 + .05, .45);
  withT(628, 405, hp, () => rich([['DEL ', '#fff'], ['TECHO', C.yel], [' AL ', '#fff'], ['FONDO', '#5FE3EE']], 0, 0, { w: 400, fam: 'Archivo Black', size: 60, stroke: C.ink, sw: 12, maxW: 800 }));
  const mp = back(prog(t, t0 + .1, .55));
  withT(628, 760, mp * (1 + .025 * prog(t, t0, 5)), () => {
    ctx.translate(-628, -760);
    shadow(true, 30, 12); rr(210, 470, 836, 590, 34); ctx.fillStyle = 'rgba(6,24,58,.9)'; ctx.fill(); shadow(false);
    ctx.strokeStyle = 'rgba(255,255,255,.25)'; ctx.lineWidth = 3; ctx.stroke();
    // mar con olitas
    ctx.strokeStyle = 'rgba(95,227,238,.25)'; ctx.lineWidth = 3;
    for (let r = 0; r < 5; r++) { ctx.beginPath(); for (let x = 240; x < 1020; x += 12) { const y = 520 + r * 120 + Math.sin(x * .04 + t * 2 + r) * 5; x === 240 ? ctx.moveTo(x, y) : ctx.lineTo(x, y); } ctx.stroke(); }
    const bn = ISL.findIndex(p => p[0] === BORDER[0][0] && p[1] === BORDER[0][1]);
    const bs = ISL.findIndex(p => p[0] === BORDER.at(-1)[0] && p[1] === BORDER.at(-1)[1]);
    const dr = ISL.slice(bn, bs + 1).concat(BORDER.slice(1, -1).reverse());
    const ht = ISL.slice(bs).concat(ISL.slice(0, bn + 1)).concat(BORDER.slice(1, -1));
    mapPoly(ht); ctx.fillStyle = '#8D96A6'; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke();
    mapPoly(dr); ctx.fillStyle = '#2F74E0'; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 4; ctx.stroke();
    text('HAITÍ', MX(-73.05), MY(18.95), { w: 800, size: 28, color: '#E6E9EF' });
    text('REP. DOMINICANA', MX(-69.75), MY(18.72), { w: 800, size: 26, color: '#fff' });
    const P1 = [MX(-70.99), MY(19.02)], P2 = [MX(-71.58), MY(18.5)];
    // línea punteada entre pines
    const lp = eio(prog(t, S(140) + .1, .7));
    if (lp > 0) { ctx.setLineDash([12, 10]); ctx.lineDashOffset = -t * 40; ctx.strokeStyle = C.yel; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(P1[0], P1[1] - 6); ctx.lineTo(lerp(P1[0], P2[0], lp), lerp(P1[1] - 6, P2[1] - 6, lp)); ctx.stroke(); ctx.setLineDash([]); }
    const p1 = prog(t, S(136) - .15, .45), p2 = prog(t, S(140) - .15, .45);
    for (const [P, pp] of [[P1, p1], [P2, p2]]) {
      if (pp <= 0) continue;
      const ring = (t * 1.2) % 1; ctx.strokeStyle = `rgba(255,75,85,${1 - ring})`; ctx.lineWidth = 4; ctx.beginPath(); ctx.ellipse(P[0], P[1], 10 + ring * 30, (10 + ring * 30) * .45, 0, 0, 7); ctx.stroke();
      pin(P[0], P[1] - 160 * (1 - eo(pp)) , 1 + .3 * bump(pp, .7, .3), pp > .99 ? C.red : C.red);
    }
    // etiquetas
    const l1 = pop(t, S(136) + .15, .45);
    if (l1 > 0) {
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(P1[0] + 10, P1[1] - 60); ctx.lineTo(820, 590); ctx.stroke();
      withT(870, 540, l1, () => { shadow(true); rr(-160, -48, 320, 96, 18); ctx.fillStyle = C.yel; ctx.fill(); shadow(false);
        text('PICO DUARTE', 0, -16, { w: 400, fam: 'Archivo Black', size: 30, color: C.navy, maxW: 290 }); text('+3,098 m', 0, 22, { w: 800, size: 28, color: C.red }); });
    }
    const l2 = pop(t, S(140) + .15, .45);
    if (l2 > 0) {
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(P2[0] - 6, P2[1] + 4); ctx.lineTo(480, 940); ctx.stroke();
      withT(420, 985, l2, () => { shadow(true); rr(-170, -48, 340, 96, 18); ctx.fillStyle = '#5FE3EE'; ctx.fill(); shadow(false);
        text('LAGO ENRIQUILLO', 0, -16, { w: 400, fam: 'Archivo Black', size: 28, color: C.navy, maxW: 310 }); text('−45 m', 0, 22, { w: 800, size: 28, color: C.red }); });
    }
  });
  const fp = pop(t, S(146) - .2, .5);
  if (fp > 0) withT(628, 1185, fp, () => { shadow(true, 20, 8); ctx.fillStyle = 'rgba(0,0,0,.01)'; ctx.fillRect(-120, -80, 240, 160); shadow(false); flag(-120, -80, 240, 160, t, .08); });
}

// ---------- ESCENA 8: ENCUESTA + SEGUIR ----------
function iconMountain(x, y, s) { withT(x, y, s, () => { ctx.fillStyle = '#556A86'; poly([[-26, 16], [0, -20], [26, 16]]); ctx.fill(); ctx.fillStyle = '#fff'; poly([[-9, -7], [0, -20], [9, -7], [3, -10], [-3, -6]]); ctx.fill(); }); }
function iconCroc(x, y, s, t) { withT(x, y, s, () => { ctx.save(); ctx.beginPath(); ctx.arc(0, 0, 34, 0, 7); ctx.clip(); ctx.fillStyle = '#9EE6EE'; ctx.fillRect(-40, -40, 80, 80); crocEyes(0, 14, .42, 10, t); ctx.fillStyle = 'rgba(23,144,156,.8)'; ctx.fillRect(-40, 14, 80, 30); ctx.restore(); }); }
function scene8(t) {
  const t0 = B[7];
  const hp = pop(t, t0 + .05, .45);
  withT(628, 410, hp * (1 + .02 * Math.sin(t * 3)), () => {
    text('¿A CUÁL IRÍAS', 0, -36, { w: 400, fam: 'Archivo Black', size: 58, stroke: C.ink, sw: 12, maxW: 800 });
    text('PRIMERO?', 0, 34, { w: 400, fam: 'Archivo Black', size: 58, color: C.yel, stroke: C.ink, sw: 12, maxW: 800 });
  });
  const race = prog(t, S(158) - .3, .5);
  const p1 = Math.round(50 + race * 14 * Math.sin((t - S(158)) * 2.2) * Math.exp(-Math.max(0, t - S(158)) * .25));
  const BTN = [[580, 'PICO DUARTE', S(153) - .2, p1, C.red, 0], [720, 'LAGO ENRIQUILLO', S(157) - .2, 100 - p1, '#21B8C6', 1]];
  for (const [y, lab, ta, pc, col, kind] of BTN) {
    const s = pop(t, ta, .45); if (s <= 0) continue;
    const hl = 1 + .05 * bump(t, ta + .2, .5);
    withT(628, y, s * hl, () => {
      shadow(true, 20, 8); rr(-410, -58, 820, 116, 58); ctx.fillStyle = '#fff'; ctx.fill(); shadow(false);
      if (race > 0) { ctx.save(); rr(-410, -58, 820, 116, 58); ctx.clip(); ctx.fillStyle = col; ctx.globalAlpha = .28; ctx.fillRect(-410, -58, 820 * clamp(pc / 100) * race, 116); ctx.restore(); }
      ctx.fillStyle = kind ? '#fff' : '#DDEBFA'; ctx.beginPath(); ctx.arc(-345, 0, 40, 0, 7); ctx.fill();
      ctx.strokeStyle = col; ctx.lineWidth = 4; ctx.stroke();
      kind ? iconCroc(-345, 0, 1.1, t) : iconMountain(-345, 2, 1.2);
      text(lab, -285, 3, { w: 400, fam: 'Archivo Black', size: 40, color: C.navy, align: 'left', maxW: 470 });
      if (race > 0) text(pc + '%', 370, 3, { w: 800, size: 40, color: col === C.red ? C.red : C.teal, align: 'right' });
    });
  }
  const vp = pop(t, S(159) - .15, .45);
  if (vp > 0) withT(628, 880, vp, () => {
    shadow(true, 20, 8); rr(-380, -46, 760, 92, 22); ctx.fillStyle = C.yel; ctx.fill();
    poly([[-300, 40], [-320, 76], [-250, 44]]); ctx.fill(); shadow(false);
    text('¡VOTA EN LOS COMENTARIOS!', 0, 3, { w: 400, fam: 'Archivo Black', size: 40, color: C.navy, maxW: 700 });
  }, Math.sin(t * 5) * .025);
  // seguir
  const fp = pop(t, S(163) - .45, .5);
  if (fp > 0) {
    const click = S(164) + .2, pressed = t >= click;
    withT(628, 1140, fp, () => {
      shadow(true, 24, 10); rr(-410, -125, 820, 250, 30); ctx.fillStyle = 'rgba(6,24,58,.92)'; ctx.fill(); shadow(false);
      ctx.strokeStyle = 'rgba(255,255,255,.3)'; ctx.lineWidth = 3; ctx.stroke();
      ctx.fillStyle = C.red; ctx.beginPath(); ctx.arc(-320, -48, 50, 0, 7); ctx.fill();
      magnifier(-318, -46, 2.1, C.navy);
      text('@capitalcuriosoo', -250, -66, { w: 800, size: 40, align: 'left', maxW: 430 });
      text('Curiosidades de RD', -250, -22, { w: 600, size: 26, align: 'left', color: C.cream });
      flag(250, -96, 108, 72, t, .08);
      const k = 1 - .1 * bump(t, click, .25);
      withT(0, 70, k, () => {
        rr(-200, -40, 400, 80, 40); ctx.fillStyle = pressed ? '#fff' : C.red; ctx.fill();
        if (pressed) { text('SIGUIENDO', -22, 3, { w: 400, fam: 'Archivo Black', size: 34, color: C.navy }); check(118, 2, 30, C.green, 8); }
        else text('SEGUIR', 0, 3, { w: 400, fam: 'Archivo Black', size: 38, color: '#fff' });
      });
      if (pressed) { const rp = prog(t, click, .5); ctx.strokeStyle = `rgba(255,255,255,${1 - rp})`; ctx.lineWidth = 6; rr(-200 - rp * 40, 30 - rp * 20, 400 + rp * 80, 80 + rp * 40, 60); ctx.stroke(); }
    });
    // cursor
    const cm = eio(prog(t, S(163) - .2, .6));
    const cx = lerp(1010, 790, cm), cy = lerp(1330, 1228, cm);
    if (t > S(163) - .25) cursorArrow(cx, cy, pressed && t < click + .2 ? .85 : 1);
    if (pressed) { const r = seeded(4); for (let i = 0; i < 9; i++) { const hp2 = prog(t, click + i * .05, 1.4); if (hp2 <= 0 || hp2 >= 1) continue; heart(850 + (r() - .5) * 300, 1200 - hp2 * 420, .9 + r() * .8, i % 3 ? C.red : C.yel); } }
  }
}

// ---------- subtítulos palabra por palabra ----------
const KEYS = new Set(['ALTO', 'BAJO', 'CARIBE', 'NUESTRO', 'PICO', 'DUARTE', 'TECHO', 'COCODRILOS', 'ENRIQUILLO', 'SALADA', 'IGUANAS', 'IGUANA', 'FLAMENCOS']);
function buildGroups() {
  let phrases = [], cur = [];
  WORDS.forEach((w, i) => { cur.push(i); if (/[.,…:?!;]$/.test(w.text)) { phrases.push(cur); cur = []; } });
  if (cur.length) phrases.push(cur);
  const merged = [];
  for (const p of phrases) {
    if (p.length === 1 && merged.length && WORDS[p[0]].start - WORDS[merged.at(-1).at(-1)].end < .6) merged.at(-1).push(...p); else merged.push(p);
  }
  const out = [];
  for (const p of merged) {
    const k = Math.ceil(p.length / 4), base = Math.floor(p.length / k), extra = p.length % k; let j = 0;
    for (let c = 0; c < k; c++) { const n = base + (c < extra ? 1 : 0); out.push(p.slice(j, j + n)); j += n; }
  }
  return out.map((g, i) => ({ idx: g }));
}
function drawSubs(t) {
  for (let gi = 0; gi < GROUPS.length; gi++) {
    const g = GROUPS[gi]; const a = S(g.idx[0]) - .08;
    const nextStart = gi + 1 < GROUPS.length ? S(GROUPS[gi + 1].idx[0]) - .08 : 1e9;
    const end = Math.min(nextStart, E(g.idx.at(-1)) + .55);
    if (t < a || t >= end) continue;
    const words = g.idx.map(i => WORDS[i].text.toUpperCase());
    let size = 82; ctx.font = F(800, size);
    const sp0 = ctx.measureText(' ').width;
    const ws0 = words.map(w => ctx.measureText(w).width);
    const need = ws0.reduce((a, b) => a + b, 0) + sp0 * (words.length - 1) + Math.max(...ws0) * .2;
    if (need > 940) { size *= 940 / need; ctx.font = F(800, size); }
    const sp = ctx.measureText(' ').width;
    const ws = words.map(w => ctx.measureText(w).width);
    const scs = g.idx.map(wi => {
      const nxt = wi + 1 < WORDS.length ? S(wi + 1) : 1e9;
      const active = t >= S(wi) - .03 && t < Math.min(nxt - .03, E(wi) + .25);
      return active ? 1 + .2 * back(prog(t, S(wi) - .03, .18)) : 1;
    });
    const tot = ws.reduce((a, w, k) => a + w * scs[k], 0) + sp * (words.length - 1);
    const base = ws.reduce((a, b) => a + b, 0) + sp * (words.length - 1);
    const s = .75 + .25 * back(prog(t, a, .22));
    withT(540, 1525, s, () => {
      rr(-Math.max(tot, base) / 2 - 34, -size * .78, Math.max(tot, base) + 68, size * 1.56, 28); ctx.fillStyle = 'rgba(6,24,58,.55)'; ctx.fill();
      let x = -tot / 2;
      g.idx.forEach((wi, k) => {
        const active = scs[k] > 1;
        const key = KEYS.has(norm(WORDS[wi].text));
        const cx = x + ws[k] * scs[k] / 2;
        withT(cx, 0, scs[k], () => {
          ctx.font = F(800, size); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
          ctx.lineJoin = 'round'; ctx.strokeStyle = C.ink; ctx.lineWidth = size * .16; ctx.strokeText(words[k], 0, 4);
          ctx.fillStyle = active ? C.red : key ? C.yel : '#fff'; ctx.fillText(words[k], 0, 4);
        });
        x += ws[k] * scs[k] + sp;
      });
    });
  }
}

// ---------- marca de agua y barra ----------
function drawHUD(t) {
  ctx.fillStyle = 'rgba(255,255,255,.18)'; ctx.fillRect(0, 0, W, 12);
  ctx.fillStyle = C.red; ctx.fillRect(0, 0, W * clamp(t / ANIM_END), 12);
  ctx.font = F(700, 30); const tw = ctx.measureText('@capitalcuriosoo').width;
  const x1 = 1050 - tw - 70;
  rr(x1, 166, tw + 70, 58, 29); ctx.fillStyle = 'rgba(6,24,58,.55)'; ctx.fill();
  magnifier(x1 + 34, 196, 1.15);
  text('@capitalcuriosoo', 1036, 196, { w: 700, size: 30, align: 'right', color: '#fff' });
}

// ---------- render ----------
function render(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.clearRect(0, 0, W, H);
  drawBG(t);
  if (t < B[1]) scene1(t);
  else if (t < B[2]) scene2(t);
  if (t >= B[2] && t < S(71) + 1.2) scene3(t);
  if (t >= B[3] && t < B[4]) scene4(t);
  else if (t >= B[4] && t < B[5]) scene5(t);
  else if (t >= B[5] && t < B[6]) scene6(t);
  else if (t >= B[6] && t < B[7]) scene7(t);
  else if (t >= B[7]) scene8(t);
  drawAltimeter(t);
  for (let k = 1; k < B.length; k++) wipe(t, B[k]);
  drawSubs(t);
  drawHUD(t);
}

function init(words) {
  WORDS = words;
  const expect = { 3: 'alto', 8: 'bajo', 13: 'están', 18: 'Y', 23: 'nuestro.', 24: 'Arriba', 32: 'tres', 36: 'altura.', 40: 'techo', 48: 'no', 54: 'Ahora', 56: '¿dónde', 62: 'Te', 65: 'pista:', 67: 'cocodrilos.', 68: 'Es', 70: 'Lago', 71: 'Enriquillo,', 75: 'grande', 79: 'Su', 80: 'superficie', 83: 'cuarenta', 88: 'debajo', 93: 'Y', 95: 'agua', 97: 'más', 98: 'salada', 103: 'porque', 106: 'no', 108: 'salida:', 109: 'el', 111: 'solo', 115: 'evaporación.', 116: 'Ahí', 118: 'cocodrilos', 119: 'americanos,', 120: 'flamencos…', 122: 'dos', 125: 'iguanas', 128: 'iguana', 130: 'Ricord', 133: 'iguana', 134: 'rinoceronte.', 135: 'Del', 136: 'techo', 140: 'fondo', 146: 'República', 148: '¿A', 153: 'Pico', 157: 'Lago', 158: 'Enriquillo?', 159: 'Vota', 163: 'y', 164: 'sígueme', 166: 'más.' };
  for (const [i, w] of Object.entries(expect)) if (WORDS[i].text !== w) throw new Error(`palabra ${i}: "${WORDS[i].text}" != "${w}"`);
  const starts = [0, 24, 54, 68, 93, 116, 135, 148];
  B = starts.map(i => i === 0 ? 0 : (E(i - 1) + S(i)) / 2);
  VOICE_END = E(166);
  ANIM_END = VOICE_END + .75;
  GROUPS = buildGroups();
  return { ANIM_END, B, groups: GROUPS.map(g => g.idx.map(i => WORDS[i].text).join(' ')) };
}
window.init = init; window.render = render;
