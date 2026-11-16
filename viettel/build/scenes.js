// Capital Curioso – Viettel en República Dominicana
// Motor de motion graphics en canvas: window.renderAt(t) dibuja el fotograma del segundo t.
'use strict';
const W = 1080, H = 1920, FPS = 30, DURATION = 78.5;
const C = document.getElementById('c');
const X = C.getContext('2d');

// ---------- Paleta de marca ----------
const NAVY = '#0A1D3D', NAVY2 = '#06112A', NAVY3 = '#13305F', RED = '#E3122C', RED2 = '#B00D22',
  WHITE = '#FFFFFF', SOFT = '#C9D4EA', RD_BLUE = '#002D62', RD_RED = '#CE1126';

// ---------- Utilidades ----------
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, k) => a + (b - a) * k;
const P = (t, a, b) => clamp((t - a) / (b - a));
const eOut = k => 1 - Math.pow(1 - k, 3);
const eIn = k => k * k * k;
const eIO = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const eExpo = k => k >= 1 ? 1 : 1 - Math.pow(2, -10 * k);
const eBack = k => { if (k <= 0) return 0; const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
// entra en [a,a+d] y sale en [b-d2,b]
const inout = (t, a, b, d = .35, d2 = .3) => Math.min(eOut(P(t, a, a + d)), 1 - eIn(P(t, b - d2, b)));
const fmt = n => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
function rr(x, y, w, h, r) { X.beginPath(); X.roundRect(x, y, w, h, r); }
function font(sz, fam = 'Anton', wt = '') { X.font = `${wt} ${sz}px ${fam}`.trim(); }
function txt(s, x, y, sz, col, fam = 'Anton', align = 'center', wt = '', ls = 0) {
  font(sz, fam, wt); X.fillStyle = col; X.textAlign = align; X.textBaseline = 'middle';
  X.letterSpacing = ls + 'px'; X.fillText(s, x, y); X.letterSpacing = '0px';
}
function tw(s, sz, fam = 'Anton', wt = '', ls = 0) { font(sz, fam, wt); X.letterSpacing = ls + 'px'; const m = X.measureText(s).width; X.letterSpacing = '0px'; return m; }
function wrap(s, maxw, sz, fam, wt) {
  font(sz, fam, wt); const ws = s.split(' '); const lines = []; let cur = '';
  for (const w of ws) { const tst = cur ? cur + ' ' + w : w; if (X.measureText(tst).width > maxw && cur) { lines.push(cur); cur = w; } else cur = tst; }
  if (cur) lines.push(cur); return lines;
}
function withA(a, fn) { if (a <= 0.001) return; X.save(); X.globalAlpha *= a; fn(); X.restore(); }
function shadow(blur = 30, col = 'rgba(0,0,0,.55)', oy = 10) { X.shadowColor = col; X.shadowBlur = blur; X.shadowOffsetY = oy; }
function noShadow() { X.shadowColor = 'transparent'; X.shadowBlur = 0; X.shadowOffsetY = 0; }

// ---------- Recursos ----------
const IMG = {};
const IMG_NAMES = ['celular', 'celular_2', 'torre_celular', 'santo_domingo', 'viettel_edificio', 'hanoi', 'bandera_eeuu', 'dinero', 'dinero_2', 'myanmar', 'myanmar_2', 'viettel_logo', 'torre_celular_2', 'hanoi_2'];
const BLUR = {};
function loadImg(n) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => { IMG[n] = i; res(); }; i.onerror = rej; i.src = '../assets/' + n + (n === 'viettel_logo' ? '.png' : '.jpg'); });
}
function makeBlur(n, px) {
  const i = IMG[n]; const s = Math.max(W / i.width, H / i.height);
  const c = document.createElement('canvas'); c.width = W / 2; c.height = H / 2; const x = c.getContext('2d');
  x.filter = `blur(${px}px)`; const w = i.width * s / 2, h = i.height * s / 2;
  x.drawImage(i, (W / 2 - w) / 2 - 20, (H / 2 - h) / 2 - 20, w + 40, h + 40); BLUR[n] = c;
}
// logo blanco (silueta) para fondos oscuros
let LOGO_W;
function makeWhiteLogo() {
  const i = IMG.viettel_logo; const c = document.createElement('canvas'); c.width = i.width; c.height = i.height;
  const x = c.getContext('2d'); x.drawImage(i, 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); LOGO_W = c;
}
const GRAIN = [];
function makeGrain() {
  for (let k = 0; k < 6; k++) {
    const c = document.createElement('canvas'); c.width = 540; c.height = 960; const x = c.getContext('2d');
    const d = x.createImageData(540, 960);
    for (let p = 0; p < d.data.length; p += 4) { const v = Math.random() * 255; d.data[p] = d.data[p + 1] = d.data[p + 2] = v; d.data[p + 3] = 255; }
    x.putImageData(d, 0, 0); GRAIN.push(c);
  }
}

// Ken Burns a pantalla completa
function cover(n, z = 1, ox = 0, oy = 0, a = 1, src) {
  const i = src || IMG[n]; const iw = src ? W : i.width, ih = src ? H : i.height;
  const s = Math.max(W / iw, H / ih) * z; const w = iw * s, h = ih * s;
  withA(a, () => X.drawImage(i, (W - w) / 2 + ox, (H - h) / 2 + oy, w, h));
}
function coverBlur(n, z = 1.05, a = 1) { withA(a, () => { const s = z; X.drawImage(BLUR[n], (W - W * s) / 2, (H - H * s) / 2, W * s, H * s); }); }
// capa de grado de color: azul marino + viñeta
function grade(strength = .55, top = .2) {
  let g = X.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, `rgba(6,17,42,${Math.min(1, strength + .35)})`);
  g.addColorStop(.25, `rgba(6,17,42,${strength})`);
  g.addColorStop(.7, `rgba(6,17,42,${strength})`);
  g.addColorStop(1, `rgba(6,17,42,${Math.min(1, strength + .3)})`);
  X.fillStyle = g; X.fillRect(0, 0, W, H);
  const r = X.createRadialGradient(W / 2, H / 2, H * .25, W / 2, H / 2, H * .75);
  r.addColorStop(0, 'rgba(0,0,0,0)'); r.addColorStop(1, 'rgba(0,0,0,.55)'); X.fillStyle = r; X.fillRect(0, 0, W, H);
}
function navyBG(t) {
  const g = X.createRadialGradient(W / 2, H * .45, 50, W / 2, H * .45, H * .8);
  g.addColorStop(0, '#163A72'); g.addColorStop(.55, NAVY); g.addColorStop(1, NAVY2);
  X.fillStyle = g; X.fillRect(0, 0, W, H);
  // retícula técnica en movimiento
  X.save(); X.strokeStyle = 'rgba(255,255,255,.045)'; X.lineWidth = 1.5;
  const off = (t * 18) % 90;
  for (let x = -90 + off; x < W + 90; x += 90) { X.beginPath(); X.moveTo(x, 0); X.lineTo(x, H); X.stroke(); }
  for (let y = -90 + off; y < H + 90; y += 90) { X.beginPath(); X.moveTo(0, y); X.lineTo(W, y); X.stroke(); }
  X.restore();
  // partículas de luz
  for (let k = 0; k < 26; k++) {
    const px = (k * 397 % W + Math.sin(t * .3 + k) * 40), py = ((k * 733 + t * (12 + k % 5 * 6)) % H);
    X.fillStyle = `rgba(160,190,255,${.05 + (k % 4) * .03})`; X.beginPath(); X.arc(px, H - py, 2 + k % 3, 0, 7); X.fill();
  }
}

// ---------- Íconos ----------
function iconAlert(x, y, s, col = RED) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100);
  X.fillStyle = col; X.beginPath(); X.moveTo(0, -48); X.lineTo(52, 44); X.lineTo(-52, 44); X.closePath();
  X.lineJoin = 'round'; X.lineWidth = 14; X.strokeStyle = col; X.stroke(); X.fill();
  X.fillStyle = '#fff'; rr(-6, -22, 12, 40, 6); X.fill(); X.beginPath(); X.arc(0, 31, 7, 0, 7); X.fill(); X.restore();
}
function iconLock(x, y, s, col = '#fff', open = 0) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100);
  X.strokeStyle = col; X.lineWidth = 11; X.beginPath(); X.arc(0, -18 - open * 14, 26, Math.PI, 0); X.lineTo(26, 4 - open * 14); X.moveTo(-26, -18 - open * 14); X.lineTo(-26, 4); X.stroke();
  X.fillStyle = col; rr(-40, -4, 80, 58, 10); X.fill();
  X.fillStyle = NAVY; X.beginPath(); X.arc(0, 18, 8, 0, 7); X.fill(); X.fillRect(-4, 18, 8, 18); X.restore();
}
function iconLupa(x, y, s, ring = NAVY, handle = RED, q = RED, lw = 1, prog = 1) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100); X.lineCap = 'round';
  X.strokeStyle = handle; X.lineWidth = 20 * lw; const hp = clamp((prog - .55) / .3);
  if (hp > 0) { X.beginPath(); X.moveTo(34, 34); X.lineTo(34 + 32 * hp, 34 + 32 * hp); X.stroke(); }
  X.strokeStyle = ring; X.lineWidth = 13 * lw; X.beginPath(); X.arc(0, 0, 46, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * clamp(prog / .55)); X.stroke();
  const qp = clamp((prog - .75) / .25);
  if (qp > 0) { X.globalAlpha *= qp; txt('?', 0, 4, 74 * (0.6 + .4 * eBack(qp)), q, 'Anton'); }
  X.restore();
}
function iconCalendar(x, y, w, h, day, mon, yr, wd, flip) {
  X.save(); shadow(40, 'rgba(0,0,0,.5)', 16);
  X.fillStyle = '#fff'; rr(x, y, w, h, 26); X.fill(); noShadow();
  X.fillStyle = RED; X.beginPath(); X.roundRect(x, y, w, h * .26, [26, 26, 0, 0]); X.fill();
  txt(wd, x + w / 2, y + h * .13, h * .13, '#fff', 'Oswald', 'center', '600', 6);
  for (const rx of [x + w * .25, x + w * .75]) { X.fillStyle = NAVY; rr(rx - 9, y - 22, 18, 48, 9); X.fill(); }
  // número que "cae" (flip)
  X.save(); X.beginPath(); X.rect(x, y + h * .26, w, h * .74); X.clip();
  const oy = (1 - eBack(flip)) * -h * .5;
  txt(day, x + w / 2, y + h * .56 + oy, h * .44, NAVY, 'Anton');
  txt(mon + ' ' + yr, x + w / 2, y + h * .86 + oy, h * .11, RED, 'Oswald', 'center', '700', 4);
  X.restore(); X.restore();
}
function iconTower(x, y, s, col = '#fff', t = 0) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100); X.strokeStyle = col; X.lineWidth = 7; X.lineJoin = 'round';
  X.beginPath(); X.moveTo(-26, 50); X.lineTo(0, -30); X.lineTo(26, 50); X.moveTo(-17, 22); X.lineTo(17, 22); X.moveTo(-9, -2); X.lineTo(9, -2); X.moveTo(-17, 22); X.lineTo(9, -2); X.stroke();
  X.fillStyle = col; X.beginPath(); X.arc(0, -36, 8, 0, 7); X.fill();
  for (let k = 1; k <= 2; k++) {
    const a = .5 + .5 * Math.sin(t * 5 - k); X.globalAlpha = a; X.lineWidth = 6;
    X.beginPath(); X.arc(0, -36, 18 * k, -Math.PI * .8, -Math.PI * .2); X.stroke(); X.beginPath(); X.arc(0, -36, 18 * k, Math.PI * .2, Math.PI * .8, false); X.stroke();
  }
  X.restore();
}
function iconBuilding(x, y, s, col) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100); X.fillStyle = col;
  X.beginPath(); X.moveTo(-50, -16); X.lineTo(0, -46); X.lineTo(50, -16); X.closePath(); X.fill();
  for (let k = -2; k <= 2; k++) X.fillRect(k * 20 - 5, -10, 10, 42); X.fillRect(-52, 36, 104, 10); X.restore();
}
function iconPeople(x, y, s, col) {
  X.save(); X.translate(x, y); X.scale(s / 100, s / 100); X.fillStyle = col;
  for (const [dx, sc] of [[-30, .8], [30, .8], [0, 1]]) { X.beginPath(); X.arc(dx, -18 * sc, 15 * sc, 0, 7); X.fill(); X.beginPath(); X.ellipse(dx, 28 * sc, 26 * sc, 28 * sc, 0, Math.PI, 0); X.fill(); }
  X.restore();
}
function iconStar(x, y, r, col) {
  X.fillStyle = col; X.beginPath();
  for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + k * Math.PI / 5, rad = k % 2 ? r * .42 : r; X.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad); }
  X.closePath(); X.fill();
}
function flagVN(x, y, w, h) { X.fillStyle = '#DA251D'; X.fillRect(x, y, w, h); iconStar(x + w / 2, y + h / 2, h * .32, '#FFCD00'); }
function flagRD(x, y, w, h, shield = true) {
  const cw = w * .12, ch = h * .17;
  X.fillStyle = '#fff'; X.fillRect(x, y, w, h);
  const qw = (w - cw) / 2, qh = (h - ch) / 2;
  X.fillStyle = RD_BLUE; X.fillRect(x, y, qw, qh); X.fillRect(x + qw + cw, y + qh + ch, qw, qh);
  X.fillStyle = RD_RED; X.fillRect(x + qw + cw, y, qw, qh); X.fillRect(x, y + qh + ch, qw, qh);
  if (shield) { X.fillStyle = '#2E7D32'; X.beginPath(); X.arc(x + w / 2, y + h / 2, ch * .45, 0, 7); X.fill(); X.fillStyle = '#C8A12B'; X.fillRect(x + w / 2 - ch * .18, y + h / 2 - ch * .18, ch * .36, ch * .36); }
}
function flagUS(x, y, w, h) {
  for (let k = 0; k < 13; k++) { X.fillStyle = k % 2 ? '#fff' : '#B22234'; X.fillRect(x, y + k * h / 13, w, h / 13 + .5); }
  X.fillStyle = '#3C3B6E'; X.fillRect(x, y, w * .4, h * 7 / 13);
  for (let r = 0; r < 4; r++) for (let c = 0; c < 5; c++) { X.fillStyle = '#fff'; X.beginPath(); X.arc(x + w * .04 + c * w * .08, y + h * .06 + r * h * .125, w * .012, 0, 7); X.fill(); }
}

// ---------- Componentes ----------
// Tarjeta de cita con fuente abajo
function quoteCard(t, t0, x, y, w, quote, source, opt = {}) {
  const p = eOut(P(t, t0, t0 + .5)); if (p <= 0) return 0;
  const sz = opt.size || 54, pad = 48;
  const lines = wrap(quote, w - pad * 2 - 30, sz, 'Oswald', '600');
  const h = 110 + lines.length * sz * 1.18 + 92;
  const accent = opt.accent || RED;
  X.save(); X.globalAlpha *= p * (opt.alpha ?? 1); X.translate((1 - p) * (opt.fromLeft ? -120 : 120), 0);
  shadow(50, 'rgba(0,0,0,.55)', 18);
  X.fillStyle = opt.dark ? 'rgba(10,29,61,.94)' : 'rgba(255,255,255,.97)'; rr(x, y, w, h, 28); X.fill(); noShadow();
  X.fillStyle = accent; rr(x, y, 14, h, [28, 0, 0, 28]); X.fill();
  // comillas
  txt('“', x + pad + 8, y + 64, 150, accent, 'Anton', 'left');
  if (opt.tag) { const tw2 = tw(opt.tag, 28, 'Oswald', '700', 3) + 36; X.fillStyle = accent; rr(x + w - pad - tw2, y + 28, tw2, 48, 24); X.fill(); txt(opt.tag, x + w - pad - tw2 / 2, y + 53, 28, '#fff', 'Oswald', 'center', '700', 3); }
  const tc = opt.dark ? '#fff' : NAVY;
  lines.forEach((l, k) => {
    const lp = eOut(P(t, t0 + .2 + k * .12, t0 + .6 + k * .12));
    withA(lp, () => txt(l, x + pad + 22 + (1 - lp) * 30, y + 120 + k * sz * 1.18, sz, tc, 'Oswald', 'left', '600'));
  });
  const sy = y + h - 52;
  X.fillStyle = opt.dark ? 'rgba(255,255,255,.18)' : 'rgba(10,29,61,.14)'; X.fillRect(x + pad + 22, sy - 34, w - pad * 2 - 22, 2);
  txt('Fuente: ' + source, x + pad + 22, sy, 32, opt.dark ? SOFT : '#5A6886', 'Oswald', 'left', '500', 1);
  X.restore(); return h;
}
// Rótulo nombre/cargo (lower third)
function rotulo(t, t0, t1, y, name, role) {
  const p = eExpo(P(t, t0, t0 + .6)), q = 1 - eIn(P(t, t1 - .35, t1)); if (p <= 0 || q <= 0) return;
  X.save(); X.globalAlpha *= q;
  const w1 = Math.max(tw(name, 64, 'Anton', '', 2), 300) + 80, w2 = Math.max(tw(role, 38, 'Oswald', '500'), 200) + 70;
  X.fillStyle = RED; X.fillRect(40, y, 16, 190 * p);
  X.save(); X.beginPath(); X.rect(56, y - 10, W, 220); X.clip();
  X.fillStyle = '#fff'; X.fillRect(56 - w1 * (1 - p), y, w1, 104); txt(name, 56 + 40 - w1 * (1 - p), y + 54, 64, NAVY, 'Anton', 'left', '', 2);
  const p2 = eExpo(P(t, t0 + .25, t0 + .85));
  X.fillStyle = NAVY; X.fillRect(56 - w2 * (1 - p2), y + 104, w2, 76); txt(role, 56 + 36 - w2 * (1 - p2), y + 143, 38, '#fff', 'Oswald', 'left', '500');
  X.restore(); X.restore();
}
function sourceTag(t, t0, txt_, y = 1548, x = 60) {
  const p = eOut(P(t, t0, t0 + .4)); if (p <= 0) return;
  withA(p, () => {
    const s = 'FUENTE: ' + txt_; const w = tw(s, 30, 'Oswald', '600', 2) + 40;
    X.fillStyle = 'rgba(6,17,42,.82)'; rr(x, y - 26, w, 52, 10); X.fill(); X.fillStyle = RED; X.fillRect(x, y - 26, 6, 52);
    txt(s, x + 22, y + 1, 30, '#fff', 'Oswald', 'left', '600', 2);
  });
}
function pill(t, t0, cx, cy, s, sz = 36, bg = RED, col = '#fff') {
  const p = eBack(P(t, t0, t0 + .4)); if (p <= 0) return;
  const w = tw(s, sz, 'Oswald', '700', 4) + sz * 1.4;
  X.save(); X.translate(cx, cy); X.scale(p, p); X.fillStyle = bg; rr(-w / 2, -sz * .85, w, sz * 1.7, sz * .85); X.fill();
  txt(s, 0, 2, sz, col, 'Oswald', 'center', '700', 4); X.restore();
}
// texto grande con golpe
function slam(t, t0, s, x, y, sz, col = '#fff', fam = 'Anton', stroke = true) {
  const p = P(t, t0, t0 + .35); if (p <= 0) return;
  const sc = lerp(1.6, 1, eOut(p));
  X.save(); X.globalAlpha *= eOut(p); X.translate(x, y); X.scale(sc, sc);
  shadow(30, 'rgba(0,0,0,.6)', 8);
  txt(s, 0, 0, sz, col, fam); noShadow(); X.restore();
}
function lineReveal(t, t0, s, x, y, sz, col, fam = 'Oswald', wt = '600', align = 'center', ls = 0) {
  const p = eOut(P(t, t0, t0 + .45)); if (p <= 0) return;
  X.save(); X.beginPath(); X.rect(0, y - sz, W, sz * 2); X.clip();
  txt(s, x, y + (1 - p) * sz * 1.4, sz, col, fam, align, wt, ls); X.restore();
}

// ---------- Mapas ----------
const D2R = Math.PI / 180;
const merc = (lon, lat) => [lon * D2R, -Math.log(Math.tan(Math.PI / 4 + clamp(lat, -80, 84) * D2R / 2))];
function mkView(lon, lat, pxPerDeg, cx, cy) { const [mx, my] = merc(lon, lat); return { mx, my, s: pxPerDeg / D2R, cx, cy }; }
function lerpView(a, b, k) {
  // zoom en espacio logarítmico para que se vea natural
  const s = Math.exp(lerp(Math.log(a.s), Math.log(b.s), k));
  const kk = (s - a.s) / ((b.s - a.s) || 1);
  return { mx: lerp(a.mx, b.mx, b.s === a.s ? k : kk), my: lerp(a.my, b.my, b.s === a.s ? k : kk), s, cx: lerp(a.cx, b.cx, k), cy: lerp(a.cy, b.cy, k) };
}
const proj = (v, lon, lat) => { const [mx, my] = merc(lon, lat); return [v.cx + (mx - v.mx) * v.s, v.cy + (my - v.my) * v.s]; };
function pathCountry(v, rings) {
  X.beginPath();
  for (const r of rings) { r.forEach(([lo, la], k) => { const [x, y] = proj(v, lo, la); k ? X.lineTo(x, y) : X.moveTo(x, y); }); X.closePath(); }
}
const CENT = {};
function centroid(code, set = 'world') {
  const key = set + code; if (CENT[key]) return CENT[key];
  const rings = GEO[set][code]; let best = rings[0];
  for (const r of rings) if (r.length > best.length) best = r;
  let sx = 0, sy = 0; for (const [a, b] of best) { sx += a; sy += b; }
  return CENT[key] = [sx / best.length, sy / best.length];
}
function ringLen(v, rings) { let L = 0; for (const r of rings) for (let k = 1; k < r.length; k++) { const a = proj(v, ...r[k - 1]), b = proj(v, ...r[k]); L += Math.hypot(a[0] - b[0], a[1] - b[1]); } return L; }

function drawWorld(t, v, hl, opt = {}) {
  const set = GEO[opt.set || 'world'];
  X.save(); X.lineJoin = 'round';
  for (const code in set) {
    if (hl[code] !== undefined) continue;
    pathCountry(v, set[code]); X.fillStyle = opt.base || 'rgba(120,150,210,.16)'; X.fill();
    X.strokeStyle = 'rgba(160,190,255,.22)'; X.lineWidth = 1.2; X.stroke();
  }
  for (const code in hl) {
    const k = hl[code]; if (!set[code]) continue;
    pathCountry(v, set[code]);
    X.fillStyle = 'rgba(120,150,210,.16)'; X.fill();
    if (k > 0) {
      X.save(); X.globalAlpha = k; shadow(26 * k, 'rgba(227,18,44,.9)', 0); X.fillStyle = code === 'DOM' ? '#FF2D47' : RED; X.fill(); noShadow();
      X.strokeStyle = '#FF8A98'; X.lineWidth = 1.6; X.stroke(); X.restore();
    }
  }
  X.restore();
}
function pulse(t, x, y, r, col = RED, speed = 1.4) {
  for (let k = 0; k < 3; k++) {
    const ph = ((t * speed + k / 3) % 1);
    X.strokeStyle = col; X.globalAlpha = (1 - ph) * .9; X.lineWidth = 4; X.beginPath(); X.arc(x, y, r * (0.3 + ph * 1.6), 0, 7); X.stroke();
  }
  X.globalAlpha = 1; X.fillStyle = '#fff'; X.beginPath(); X.arc(x, y, r * .28, 0, 7); X.fill();
  X.fillStyle = col; X.beginPath(); X.arc(x, y, r * .18, 0, 7); X.fill();
}
function mapLabel(x, y, s, col = RED, p = 1, side = 1, dy = -34) {
  if (p <= 0) return; withA(eOut(p), () => {
    const w = tw(s, 30, 'Oswald', '700', 2) + 28; const lx = side > 0 ? x + 18 : x - 18 - w;
    X.strokeStyle = '#fff'; X.lineWidth = 2; X.beginPath(); X.moveTo(x, y); X.lineTo(side > 0 ? lx : lx + w, y + dy); X.stroke();
    X.fillStyle = col; rr(lx, y + dy - 24, w, 46, 8); X.fill(); txt(s, lx + w / 2, y + dy, 30, '#fff', 'Oswald', 'center', '700', 2);
  });
}

// =================================================================
//                              ESCENAS
// =================================================================
const SCENES = [];
const scene = (a, b, fn, name) => SCENES.push({ a, b, fn, name });

// ---------- 1. GANCHO (0 – 6.75) ----------
scene(0, 6.75, (t) => {
  cover('celular', 1.08 + t * .025, 0, -40 + t * 6);
  grade(.42);
  // tag "Empresa del ejército de Vietnam"
  const pt = inout(t, .55, 6.75, .4);
  withA(pt, () => {
    const s = 'EMPRESA DEL EJÉRCITO DE VIETNAM'; const w = tw(s, 34, 'Oswald', '700', 3) + 130;
    const x = W / 2 - w / 2 + (1 - pt) * -60, y = 470;
    X.fillStyle = 'rgba(6,17,42,.88)'; rr(x, y, w, 70, 35); X.fill(); flagVN(x + 22, y + 17, 54, 36);
    txt(s, x + 92, y + 37, 34, '#fff', 'Oswald', 'left', '700', 3);
  });
  // celular dibujado
  const pp = eBack(P(t, .9, 1.6)); const exitK = eIn(P(t, 6.35, 6.75));
  if (pp > 0) {
    const pw = 470, ph = 900, px = W / 2 - pw / 2, py = 620 + (1 - pp) * 900 + exitK * -40;
    X.save(); X.globalAlpha *= 1 - exitK;
    X.translate(W / 2, py + ph / 2); X.rotate((1 - pp) * .15 + Math.sin(t * .8) * .012); X.translate(-W / 2, -(py + ph / 2));
    shadow(80, 'rgba(0,0,0,.7)', 30); X.fillStyle = '#0B0F18'; rr(px, py, pw, ph, 70); X.fill(); noShadow();
    X.strokeStyle = '#3A4458'; X.lineWidth = 6; rr(px + 3, py + 3, pw - 6, ph - 6, 67); X.stroke();
    // pantalla
    const sx = px + 22, sy = py + 22, sw = pw - 44, sh = ph - 44;
    const lg = P(t, 2.0, 2.4);
    const g = X.createLinearGradient(0, sy, 0, sy + sh); g.addColorStop(0, '#0E2550'); g.addColorStop(1, '#050B1A');
    X.fillStyle = g; rr(sx, sy, sw, sh, 52); X.fill();
    X.save(); rr(sx, sy, sw, sh, 52); X.clip();
    if (lg > 0) {
      X.fillStyle = '#fff'; X.globalAlpha = eOut(lg); X.fillRect(sx, sy, sw, sh); X.globalAlpha = 1;
      // destello rojo
      const fl = Math.max(0, 1 - P(t, 2.0, 2.9));
      const rg = X.createRadialGradient(W / 2, sy + sh * .45, 10, W / 2, sy + sh * .45, sh * .7);
      rg.addColorStop(0, `rgba(227,18,44,${fl})`); rg.addColorStop(1, 'rgba(227,18,44,0)'); X.fillStyle = rg; X.fillRect(sx, sy, sw, sh);
      const ls = eBack(P(t, 2.05, 2.55)); const lw = 380 * ls, lh = lw * 350 / 992;
      X.drawImage(IMG.viettel_logo, W / 2 - lw / 2, sy + sh * .42 - lh / 2, lw, lh);
      // barra de "pago"
      const bp = P(t, 3.0, 4.6);
      withA(P(t, 2.9, 3.1), () => {
        txt('Conectando…', W / 2, sy + sh * .62, 30, '#5A6886', 'Oswald', 'center', '500', 2);
        X.fillStyle = '#E4E8F0'; rr(sx + 60, sy + sh * .67, sw - 120, 14, 7); X.fill();
        X.fillStyle = RED; rr(sx + 60, sy + sh * .67, (sw - 120) * eIO(bp), 14, 7); X.fill();
      });
      withA(P(t, 3.3, 3.6), () => txt('≈ RD$1,000 MILLONES', W / 2, sy + sh * .76, 40, NAVY, 'Anton', 'center', '', 1));
    }
    // destello que barre la pantalla
    const sw2 = P(t, 2.0, 2.6); if (sw2 > 0 && sw2 < 1) { X.fillStyle = 'rgba(255,255,255,.6)'; X.save(); X.translate(sx + sw2 * (sw + 300) - 150, sy); X.rotate(.3); X.fillRect(-40, -200, 80, sh + 400); X.restore(); }
    X.restore();
    X.fillStyle = '#000'; rr(W / 2 - 70, sy + 16, 140, 36, 18); X.fill();
    X.restore();
  }
  // flash rojo global
  const fl = Math.max(0, 1 - P(t, 2.0, 2.5)) * (t > 2.0 ? 1 : 0); if (fl > 0) { X.fillStyle = `rgba(227,18,44,${fl * .35})`; X.fillRect(0, 0, W, H); }
  // ¿QUIÉN ES VIETTEL?
  const q = P(t, 4.6, 5.0);
  if (q > 0) {
    X.save(); X.fillStyle = `rgba(6,17,42,${.55 * eOut(q)})`; X.fillRect(0, 0, W, H); X.restore();
    const sc = lerp(1.8, 1, eOut(q)); X.save(); X.translate(W / 2, 1080); X.scale(sc, sc); X.globalAlpha = eOut(q);
    X.rotate(-.03);
    X.fillStyle = RED; X.fillRect(-470, -140, 940, 150); X.fillStyle = '#fff'; X.fillRect(-470, 10, 940, 150);
    txt('¿QUIÉN ES', 0, -62, 130, '#fff', 'Anton', 'center', '', 4);
    txt('VIETTEL?', 0, 88, 140, NAVY, 'Anton', 'center', '', 6); X.restore();
  }
}, 'gancho');

// ---------- 2. EL PAGO (6.75 – 17.9) ----------
scene(6.75, 17.9, (t) => {
  navyBG(t);
  // logo grande "Se llama Viettel"
  const lp = inout(t, 6.8, 8.75, .5, .35);
  withA(lp, () => {
    const sc = lerp(.7, 1, eBack(P(t, 6.8, 7.4))) * (1 + (t - 6.8) * .02);
    X.save(); X.translate(W / 2, 960); X.scale(sc, sc);
    shadow(60, 'rgba(0,0,0,.5)', 20); X.fillStyle = '#fff'; rr(-430, -210, 860, 420, 40); X.fill(); noShadow();
    X.drawImage(IMG.viettel_logo, -360, -127, 720, 254); X.restore();
    lineReveal(t, 7.3, 'GRUPO DE TELECOMUNICACIONES · VIETNAM', W / 2, 1250, 36, SOFT, 'Oswald', '600', 'center', 4);
  });
  // calendario
  const cp = inout(t, 8.6, 17.9, .5);
  withA(cp, () => {
    const cy = 490 + (1 - cp) * -200;
    iconCalendar(W / 2 - 340, cy, 300, 330, '13', 'NOV', '2026', 'VIERNES', P(t, 9.1, 9.7));
    lineReveal(t, 9.2, 'TRANSFERENCIA', W / 2 + 200, cy + 120, 58, '#fff', 'Anton', '', 'center', 4);
    lineReveal(t, 9.5, 'VIETTEL ➜ INDOTEL', W / 2 + 200, cy + 200, 42, RED, 'Oswald', '700', 'center', 2);
  });
  // contador RD$
  const kp = P(t, 10.75, 14.0);
  const cn = inout(t, 10.6, 17.9, .4);
  withA(cn, () => {
    const val = 972519255 * eIO(kp); const s = 'RD$' + fmt(val);
    const y = 1000;
    X.fillStyle = 'rgba(6,17,42,.7)'; rr(40, y - 120, W - 80, 250, 30); X.fill();
    X.strokeStyle = kp >= 1 ? RED : 'rgba(255,255,255,.2)'; X.lineWidth = 4; rr(40, y - 120, W - 80, 250, 30); X.stroke();
    let sz = 104; const ww = tw(s, sz, 'Anton', '', 2); if (ww > W - 140) sz *= (W - 140) / ww;
    const bump = kp >= 1 ? 1 + .08 * (1 - eOut(P(t, 14.0, 14.4))) : 1;
    X.save(); X.translate(W / 2, y - 18); X.scale(bump, bump); shadow(20, 'rgba(227,18,44,.6)', 0); txt(s, 0, 0, sz, '#fff', 'Anton', 'center', '', 2); noShadow(); X.restore();
    txt(kp >= 1 ? 'PESOS DOMINICANOS · AL INDOTEL' : 'PESOS DOMINICANOS', W / 2, y + 80, 34, kp >= 1 ? '#FF8A98' : SOFT, 'Oswald', 'center', '600', 5);
    // banderita RD
    flagRD(70, y - 100, 66, 44);
  });
  // tarjeta de cita
  quoteCard(t, 15.75, 60, 1210, W - 120, 'Primer pago por su licencia', 'El Día', { size: 64 });
}, 'pago');

// ---------- 3. LA LICITACIÓN (17.9 – 24.05) ----------
scene(17.9, 24.05, (t) => {
  cover('torre_celular', 1.12 + (t - 17.9) * .02, 0, 60 - (t - 17.9) * 12);
  grade(.66);
  pill(t, 18.0, W / 2, 500, 'AGOSTO 2026 · LICITACIÓN', 36);
  // 240 MHz
  const k = P(t, 20.2, 21.3);
  if (k > 0) {
    const v = Math.round(240 * eOut(k));
    slam(t, 20.2, v + ' MHz', W / 2, 660, 190, '#fff');
    lineReveal(t, 20.6, 'DE ESPECTRO RADIOELÉCTRICO', W / 2, 790, 40, SOFT, 'Oswald', '600', 'center', 5);
  }
  // 20 AÑOS
  const yp = eBack(P(t, 22.85, 23.25));
  if (yp > 0) {
    X.save(); X.translate(W / 2, 890); X.scale(yp, yp); X.fillStyle = RED; rr(-220, -58, 440, 116, 18); X.fill();
    txt('POR 20 AÑOS', 0, 3, 72, '#fff', 'Anton', 'center', '', 3); X.restore();
  }
  // barras por banda
  const bands = [['700 MHz', 40], ['2.3 GHz', 100], ['3.6 GHz', 100]];
  const bx = 120, by0 = 1040, bw = 760;
  withA(eOut(P(t, 20.9, 21.3)), () => {
    X.fillStyle = 'rgba(6,17,42,.75)'; rr(60, by0 - 70, W - 120, 470, 26); X.fill();
    txt('MHz ASIGNADOS POR BANDA', 100, by0 - 26, 32, SOFT, 'Oswald', 'left', '600', 4);
  });
  bands.forEach(([lab, v], i) => {
    const t0 = 21.2 + i * .45; const p = eIO(P(t, t0, t0 + .8)); if (P(t, t0 - .1, t0) <= 0) return;
    const y = by0 + 50 + i * 125;
    txt(lab, bx, y, 44, '#fff', 'Anton', 'left', '', 1);
    const x0 = bx + 230, len = (bw - 230) * (v / 100) * p;
    X.fillStyle = 'rgba(255,255,255,.1)'; rr(x0, y - 26, bw - 230, 52, 10); X.fill();
    const g = X.createLinearGradient(x0, 0, x0 + len, 0); g.addColorStop(0, RED2); g.addColorStop(1, RED);
    X.fillStyle = g; rr(x0, y - 26, Math.max(len, 1), 52, 10); X.fill();
    txt(Math.round(v * p) + '', x0 + len + (v === 100 ? -16 : 18), y + 2, 40, '#fff', 'Anton', v === 100 ? 'right' : 'left');
  });
  sourceTag(t, 21.8, 'INDOTEL / ACENTO', 1470);
}, 'licitacion');

// ---------- 4. LA INVERSIÓN (24.05 – 35.3) ----------
scene(24.05, 35.3, (t) => {
  cover('santo_domingo', 1.1 + (t - 24) * .012, 0, (t - 24) * -8);
  grade(t < 28.3 ? .62 : .72);
  // Fase 1: contador US$560 millones
  const ph1 = 1 - eIO(P(t, 28.1, 28.7));
  const k = P(t, 25.9, 27.4);
  const y1 = lerp(500, 900, ph1);
  const s1 = lerp(.55, 1, ph1);
  withA(eOut(P(t, 24.15, 24.6)), () => {
    X.save(); X.translate(W / 2, y1); X.scale(s1, s1);
    if (ph1 > .02) withA(ph1, () => { txt('SU CASA MATRIZ APROBÓ INVERTIR', 0, -200, 42, SOFT, 'Oswald', 'center', '600', 4); iconBuilding(0, -310, 100, RED); });
    const v = Math.round(560 * eOut(k));
    shadow(40, 'rgba(227,18,44,.55)', 0); txt('US$' + v, 0, -30, 220, '#fff', 'Anton', 'center', '', 2); noShadow();
    X.fillStyle = RED; rr(-250, 95, 500, 100, 14); X.fill(); txt('MILLONES', 0, 148, 76, '#fff', 'Anton', 'center', '', 10);
    X.restore();
  });
  // Fase 2: mapa RD
  const mp = P(t, 28.3, 30.0);
  if (mp > 0) {
    const v = mkView(-70.25, 18.85, 205, W / 2, 870);
    const rings = GEO.hisp.DOM, hti = GEO.hisp.HTI;
    X.save(); X.lineJoin = 'round';
    withA(eOut(P(t, 28.3, 28.8)) * .7, () => { pathCountry(v, hti); X.fillStyle = 'rgba(255,255,255,.12)'; X.fill(); X.strokeStyle = 'rgba(255,255,255,.35)'; X.lineWidth = 2; X.stroke(); });
    // relleno con la bandera dominicana
    const fp = eOut(P(t, 29.1, 29.9));
    if (fp > 0) {
      X.save(); pathCountry(v, rings); X.clip(); X.globalAlpha = fp * .92;
      const [x0, y0] = proj(v, -72.1, 20.0), [x1, y1] = proj(v, -68.3, 17.4);
      flagRD(x0, y0, x1 - x0, y1 - y0, false); X.restore();
    }
    pathCountry(v, rings); const L = ringLen(v, rings);
    X.setLineDash([L, L]); X.lineDashOffset = L * (1 - eIO(mp)); X.strokeStyle = '#fff'; X.lineWidth = 5; shadow(20, 'rgba(255,255,255,.7)', 0); X.stroke(); noShadow(); X.setLineDash([]);
    X.restore();
    withA(eOut(P(t, 28.8, 29.2)), () => {
      txt('REPÚBLICA DOMINICANA', W / 2, 1175, 46, '#fff', 'Anton', 'center', '', 8);
    });
    // "4ª compañía"
    const cp = eBack(P(t, 29.2, 29.6));
    if (cp > 0) {
      X.save(); X.translate(880, 640); X.scale(cp, cp); X.rotate(-.08); X.fillStyle = RED; X.beginPath(); X.arc(0, 0, 110, 0, 7); X.fill();
      X.strokeStyle = '#fff'; X.lineWidth = 6; X.stroke(); txt('4ª', 0, -18, 92, '#fff', 'Anton'); txt('TELEFÓNICA', 0, 48, 28, '#fff', 'Oswald', 'center', '700', 2); X.restore();
    }
    // tarjetas de operadores
    const ops = [['CLARO', 32.0, '#1D3E78'], ['ALTICE', 32.55, '#1D3E78'], ['VIVA', 33.15, '#1D3E78'], ['VIETTEL', 33.7, RED]];
    ops.forEach(([n, t0, col], i) => {
      const p = eBack(P(t, t0, t0 + .45)); if (p <= 0) return;
      const cx = i % 2 ? W / 2 + 250 : W / 2 - 250, cy = 1260 + Math.floor(i / 2) * 175;
      X.save(); X.translate(cx + (1 - p) * (i % 2 ? 400 : -400), cy); X.scale(p > 1 ? p : 1, p > 1 ? p : 1);
      const isV = n === 'VIETTEL'; const glow = isV ? .5 + .5 * Math.sin(t * 8) : 0;
      shadow(isV ? 30 + glow * 30 : 25, isV ? 'rgba(227,18,44,.9)' : 'rgba(0,0,0,.5)', isV ? 0 : 10);
      X.fillStyle = col; rr(-225, -70, 450, 140, 22); X.fill(); noShadow();
      X.strokeStyle = isV ? '#fff' : 'rgba(255,255,255,.25)'; X.lineWidth = isV ? 5 : 2; rr(-225, -70, 450, 140, 22); X.stroke();
      iconTower(-160, 6, 70, '#fff', t);
      txt(n, 30, 4, 62, '#fff', 'Anton', 'center', '', 4);
      txt((i + 1) + '', -205, -46, 26, 'rgba(255,255,255,.6)', 'Oswald', 'left', '700');
      if (isV) { const np = eBack(P(t, 34.0, 34.35)); if (np > 0) { X.save(); X.translate(190, -72); X.scale(np, np); X.rotate(.12); X.fillStyle = '#fff'; rr(-78, -28, 156, 56, 10); X.fill(); txt('NUEVO', 0, 2, 36, RED, 'Anton', 'center', '', 3); X.restore(); } }
      X.restore();
    });
  }
}, 'inversion');

// ---------- 5. ES MILITAR (35.3 – 43.3) ----------
const OPS11 = [['VNM', 39.95], ['KHM', 40.2], ['LAO', 40.4], ['MMR', 40.6], ['TLS', 40.8], ['MOZ', 41.0], ['TZA', 41.15], ['BDI', 41.3], ['CMR', 41.5], ['HTI', 42.0], ['PER', 42.6], ['DOM', 43.0]];
scene(35.3, 43.3, (t) => {
  const mp = P(t, 39.6, 40.2);
  // fondo: Hanói
  cover('hanoi', 1.15 + (t - 35.3) * .02, 120 - (t - 35.3) * 25, 0);
  grade(.5 + .4 * mp);
  // foto del edificio en marco
  const fp = inout(t, 35.35, 39.95, .5, .4);
  withA(fp, () => {
    const fw = 940, fh = 940 * 607 / 1080, fx = (W - fw) / 2, fy = 560 + (1 - fp) * 60;
    X.save(); shadow(60, 'rgba(0,0,0,.6)', 20); X.fillStyle = '#fff'; X.fillRect(fx - 12, fy - 12, fw + 24, fh + 24); noShadow();
    X.beginPath(); X.rect(fx, fy, fw, fh); X.clip(); const z = 1.05 + (t - 35.3) * .025;
    X.drawImage(IMG.viettel_edificio, fx - (z - 1) * fw / 2, fy - (z - 1) * fh / 2, fw * z, fh * z); X.restore();
    txt('SEDE DE VIETTEL · HANÓI, VIETNAM', fx, fy + fh + 50, 30, SOFT, 'Oswald', 'left', '600', 3);
    // sello "MILITAR"
    const sp = P(t, 36.0, 36.3);
    if (sp > 0) {
      X.save(); X.translate(fx + fw - 170, fy + 110); X.rotate(-.2); const sc = lerp(2.2, 1, eOut(sp)); X.scale(sc, sc); X.globalAlpha *= eOut(sp);
      X.strokeStyle = RED; X.lineWidth = 9; rr(-150, -55, 300, 110, 12); X.stroke(); txt('MILITAR', 0, 3, 80, RED, 'Anton', 'center', '', 6); X.restore();
    }
  });
  rotulo(t, 37.05, 39.9, 1210, 'VIETTEL GROUP', 'Propiedad del Ministerio de Defensa de Vietnam');
  // mapa mundial
  if (mp > 0) {
    const v = mkView(22, 2, 4.7, W / 2, 1080);
    const hl = {}; OPS11.forEach(([c, t0]) => { hl[c] = eOut(P(t, t0, t0 + .35)); });
    withA(eOut(mp), () => {
      drawWorld(t, v, hl);
      // arcos desde Vietnam
      const hq = proj(v, 105.8, 21);
      OPS11.forEach(([c, t0]) => {
        if (c === 'VNM') return; const k = eIO(P(t, t0 - .1, t0 + .4)); if (k <= 0) return;
        const cc = centroid(c); const tgt = proj(v, cc[0], cc[1]);
        const mx = (hq[0] + tgt[0]) / 2, my = Math.min(hq[1], tgt[1]) - Math.hypot(tgt[0] - hq[0], tgt[1] - hq[1]) * .28;
        X.strokeStyle = c === 'DOM' ? '#fff' : 'rgba(255,120,135,.85)'; X.lineWidth = c === 'DOM' ? 4 : 2.5;
        X.beginPath(); for (let s = 0; s <= 1.0001; s += .04) { const u = s * k; const x = (1 - u) * (1 - u) * hq[0] + 2 * (1 - u) * u * mx + u * u * tgt[0]; const y = (1 - u) * (1 - u) * hq[1] + 2 * (1 - u) * u * my + u * u * tgt[1]; s ? X.lineTo(x, y) : X.moveTo(x, y); } X.stroke();
      });
      X.fillStyle = '#FFCD00'; X.beginPath(); iconStar(hq[0], hq[1], 14, '#FFCD00');
      const lab = (c, txt_, t0, side, dy) => { const cc = centroid(c); const [x, y] = proj(v, cc[0], cc[1]); mapLabel(x, y, txt_, RED, P(t, t0, t0 + .3), side, dy); };
      lab('HTI', 'HAITÍ', 42.0, 1, -90); lab('PER', 'PERÚ', 42.6, 1, 60); lab('VNM', 'VIETNAM', 40.0, -1, -70);
      const dc = centroid('DOM'); const [dx, dy] = proj(v, dc[0], dc[1]); if (t > 42.9) pulse(t, dx, dy, 34, '#FF2D47');
      if (t > 43.0) withA(eOut(P(t, 43.0, 43.2)), () => { X.fillStyle = '#fff'; rr(dx + 20, dy + 14, 72, 40, 8); X.fill(); txt('RD', dx + 56, dy + 35, 30, RED, 'Anton'); });
    });
    // contador de países
    withA(eOut(P(t, 40.0, 40.4)), () => {
      const n = OPS11.filter(([c, t0]) => c !== 'DOM' && t >= t0).length;
      txt('YA OPERA EN', W / 2, 600, 48, SOFT, 'Oswald', 'center', '600', 8);
      shadow(30, 'rgba(227,18,44,.7)', 0); txt(n + '', W / 2 - 140, 760, 220, '#fff', 'Anton'); noShadow();
      txt('PAÍSES', W / 2 + 120, 770, 110, RED, 'Anton', 'center', '', 4);
      // leyenda
      const ly = 1400; X.fillStyle = RED; rr(150, ly - 16, 32, 32, 6); X.fill(); txt('Países donde opera Viettel', 200, ly, 34, '#fff', 'Oswald', 'left', '500');
      if (t > 43.0) { X.fillStyle = '#FF2D47'; X.beginPath(); X.arc(166, ly + 60, 16, 0, 7); X.fill(); txt('República Dominicana (nuevo)', 200, ly + 60, 34, '#fff', 'Oswald', 'left', '500'); }
    });
  }
}, 'militar');

// ---------- 6. ALERTA DE EE. UU. (43.3 – 52.8) ----------
scene(43.3, 52.8, (t) => {
  cover('bandera_eeuu', 1.1 + (t - 43.3) * .015, 0, -(t - 43.3) * 10);
  grade(.62);
  // íconos alerta + candado
  const ip = eBack(P(t, 43.4, 43.85));
  if (ip > 0) {
    const out = 1 - eIn(P(t, 48.9, 49.3));
    withA(out, () => {
      X.save(); X.translate(W / 2 - 110, 560); X.scale(ip, ip); const pu = 1 + .06 * Math.sin(t * 7);
      X.scale(pu, pu); shadow(40, 'rgba(227,18,44,.8)', 0); iconAlert(0, 0, 150); noShadow(); X.restore();
      X.save(); X.translate(W / 2 + 110, 565); X.scale(ip, ip);
      X.fillStyle = 'rgba(6,17,42,.85)'; X.beginPath(); X.arc(0, 0, 92, 0, 7); X.fill(); X.strokeStyle = RED; X.lineWidth = 5; X.stroke();
      iconLock(0, -8, 100, '#fff'); X.restore();
      // ojo / ondas de espionaje
      for (let k = 0; k < 3; k++) { const ph = (t * .9 + k / 3) % 1; X.strokeStyle = `rgba(255,255,255,${(1 - ph) * .5})`; X.lineWidth = 3; X.beginPath(); X.arc(W / 2 + 110, 565, 92 + ph * 90, -1.1, 1.1); X.stroke(); }
      const tp = eOut(P(t, 44.1, 44.5));
      withA(tp, () => { X.save(); const s = 'EMBAJADA DE EE. UU. · AGOSTO 2026'; const w = tw(s, 32, 'Oswald', '700', 3) + 120; X.fillStyle = 'rgba(6,17,42,.88)'; rr(W / 2 - w / 2, 700, w, 64, 32); X.fill(); flagUS(W / 2 - w / 2 + 22, 714, 60, 36); txt(s, W / 2 - w / 2 + 98, 733, 32, '#fff', 'Oswald', 'left', '700', 3); X.restore(); });
    });
  }
  // cita 1
  const c1y = lerp(830, 480, eIO(P(t, 48.9, 49.4)));
  const h1 = quoteCard(t, 45.6, 60, c1y, W - 120, 'Alerta sobre riesgos de espionaje con tecnología china', 'Embajada de EE. UU. en X / Diario Libre', { size: 54, tag: 'ALERTA' });
  // cita 2 (respuesta)
  quoteCard(t, 49.15, 60, 480 + (h1 || 330) + 40, W - 120, 'El Indotel niega vínculo con la licitación de Viettel', 'Diario Libre', { size: 54, dark: true, tag: 'RESPUESTA', fromLeft: true });
  rotulo(t, 49.6, 52.8, 1290, 'GUIDO GÓMEZ MAZARA', 'Presidente del Indotel');
}, 'alerta');

// ---------- 7. PIDEN INVESTIGAR (52.8 – 56.35) ----------
scene(52.8, 56.35, (t) => {
  cover('dinero', 1.15 + (t - 52.8) * .035, 0, 0);
  grade(.5);
  // lupa que recorre los billetes
  const lp = eOut(P(t, 52.9, 53.4));
  const lx = W / 2 + Math.sin((t - 52.8) * 1.6) * 220, ly = 980 + Math.cos((t - 52.8) * 1.2) * 120;
  withA(lp, () => {
    // zona ampliada
    X.save(); X.beginPath(); X.arc(lx, ly, 175, 0, 7); X.clip(); cover('dinero', (1.15 + (t - 52.8) * .035) * 1.6, -(lx - W / 2) * .6, -(ly - H / 2) * .6); X.restore();
    shadow(30, 'rgba(0,0,0,.6)', 10); iconLupa(lx, ly, 380, '#fff', RED, 'rgba(0,0,0,0)', .9, 1); noShadow();
    X.strokeStyle = 'rgba(255,255,255,.5)'; X.lineWidth = 3; X.beginPath(); X.arc(lx - 40, ly - 40, 120, Math.PI * 1.05, Math.PI * 1.4); X.stroke();
  });
  // sello INVESTIGAR
  const sp = P(t, 54.9, 55.15);
  if (sp > 0) {
    X.save(); X.translate(W / 2, 640); X.rotate(-.12); const sc = lerp(2.4, 1, eOut(sp)); X.scale(sc, sc); X.globalAlpha *= eOut(sp);
    X.fillStyle = 'rgba(6,17,42,.55)'; rr(-330, -85, 660, 170, 16); X.fill();
    X.strokeStyle = RED; X.lineWidth = 12; rr(-330, -85, 660, 170, 16); X.stroke(); txt('¿INVESTIGAR?', 0, 4, 104, RED, 'Anton', 'center', '', 6); X.restore();
  }
  // titular
  const hp = eOut(P(t, 53.85, 54.3));
  withA(hp, () => {
    const y = 1300; X.fillStyle = 'rgba(255,255,255,.97)'; rr(60, y, W - 120, 210, 24); X.fill();
    X.fillStyle = RED; rr(60, y, 220 * hp, 64, [24, 0, 18, 0]); X.fill(); txt('PARTIDO FNP', 80, y + 33, 30, '#fff', 'Oswald', 'left', '700', 3);
    txt('FNP pide investigar la licitación', W / 2, y + 125, 58, NAVY, 'Oswald', 'center', '700');
  });
  sourceTag(t, 54.4, 'EL NACIONAL', 1570);
}, 'investigar');

// ---------- 8. MYANMAR (56.35 – 64.0) ----------
scene(56.35, 64.0, (t) => {
  cover('myanmar', 1.12 + (t - 56.35) * .02, -(t - 56.35) * 18, 0);
  const mp = P(t, 57.3, 58.0);
  grade(.45 + .45 * mp);
  // título
  withA(inout(t, 56.4, 64, .4), () => {
    const y = 470; X.fillStyle = 'rgba(6,17,42,.9)'; rr(W / 2 - 230, y, 460, 84, 14); X.fill(); X.fillStyle = RED; X.fillRect(W / 2 - 230, y, 10, 84);
    txt('MYANMAR', W / 2 + 5, y + 44, 64, '#fff', 'Anton', 'center', '', 10);
  });
  if (mp > 0) {
    const zk = eIO(P(t, 57.4, 59.3));
    const v0 = mkView(100, 12, 6, W / 2, 870), v1 = mkView(96.5, 19.5, 26, W / 2, 860);
    const v = lerpView(v0, v1, zk);
    X.save(); X.beginPath(); rr(40, 590, W - 80, 560, 30); X.clip();
    withA(eOut(mp), () => {
      X.fillStyle = 'rgba(6,17,42,.6)'; X.fillRect(0, 0, W, H);
      drawWorld(t, v, { MMR: eOut(P(t, 57.6, 58.2)) }, { set: 'sea' });
      for (const [c, n] of [['THA', 'TAILANDIA'], ['LAO', 'LAOS'], ['CHN', 'CHINA'], ['IND', 'INDIA'], ['BGD', 'BANGLADÉS']]) {
        const cc = c === 'CHN' ? [100, 25] : c === 'IND' ? [92.5, 24.5] : centroid(c, 'sea'); const [x, y] = proj(v, cc[0], cc[1]);
        txt(n, x, y, 26, 'rgba(200,215,240,.55)', 'Oswald', 'center', '600', 3);
      }
      const [nx, ny] = proj(v, 96.1, 19.75); if (zk > .6) pulse(t, nx, ny, 28, '#fff');
      withA(P(t, 58.6, 59.0), () => txt('NAIPYIDÓ', nx, ny + 46, 28, '#fff', 'Oswald', 'center', '700', 3));
    });
    X.restore();
    X.strokeStyle = 'rgba(255,255,255,.2)'; X.lineWidth = 2; rr(40, 590, W - 80, 560, 30); X.stroke();
  }
  // esquema VIETTEL → MYTEL ← empresas militares
  const sy = 1290;
  const box = (cx, cy, w, h, label, sub, col, t0) => {
    const p = eBack(P(t, t0, t0 + .4)); if (p <= 0) return;
    X.save(); X.translate(cx, cy); X.scale(p, p); shadow(30, 'rgba(0,0,0,.5)', 10); X.fillStyle = col; rr(-w / 2, -h / 2, w, h, 18); X.fill(); noShadow();
    X.strokeStyle = 'rgba(255,255,255,.5)'; X.lineWidth = 2; rr(-w / 2, -h / 2, w, h, 18); X.stroke();
    const subs = sub ? sub.split('|') : []; txt(label, 0, -14 - (subs.length - 1) * 14, 48, '#fff', 'Anton', 'center', '', 3); subs.forEach((ss, j) => txt(ss, 0, 34 + (j - (subs.length - 1) / 2) * 28 + (subs.length - 1) * 6, 24, 'rgba(255,255,255,.9)', 'Oswald', 'center', '600', 1)); X.restore();
  };
  const arrow = (x0, y0, x1, y1, t0) => {
    const k = eIO(P(t, t0, t0 + .5)); if (k <= 0) return; const x = lerp(x0, x1, k), y = lerp(y0, y1, k);
    X.strokeStyle = '#fff'; X.lineWidth = 7; X.lineCap = 'round'; X.beginPath(); X.moveTo(x0, y0); X.lineTo(x, y); X.stroke();
    const a = Math.atan2(y1 - y0, x1 - x0); X.fillStyle = '#fff'; X.beginPath(); X.moveTo(x + Math.cos(a) * 14, y + Math.sin(a) * 14);
    X.lineTo(x + Math.cos(a + 2.5) * 30, y + Math.sin(a + 2.5) * 30); X.lineTo(x + Math.cos(a - 2.5) * 30, y + Math.sin(a - 2.5) * 30); X.fill();
  };
  withA(eOut(P(t, 59.3, 59.6)), () => { X.fillStyle = 'rgba(6,17,42,.85)'; rr(30, sy - 100, W - 60, 300, 26); X.fill(); });
  box(175, sy + 50, 260, 130, 'VIETTEL', 'VIETNAM', RED, 59.45);
  box(W / 2, sy + 50, 240, 130, 'MYTEL', 'OPERADORA', NAVY3, 59.9);
  box(W - 185, sy + 50, 290, 170, 'EMPRESAS', 'VINCULADAS AL|EJÉRCITO BIRMANO', '#5A1626', 60.4);
  arrow(310, sy + 50, W / 2 - 128, sy + 50, 59.95);
  arrow(W - 335, sy + 50, W / 2 + 128, sy + 50, 60.6);
  withA(eOut(P(t, 61.5, 61.9)), () => txt('SEÑALADA POR ORGANIZACIONES DE DD. HH.', W / 2, sy - 58, 32, '#FF8A98', 'Oswald', 'center', '700', 3));
  sourceTag(t, 61.2, 'JUSTICE FOR MYANMAR', 1555);
}, 'myanmar');

// ---------- 9. EL OTRO LADO (64.0 – 68.8) ----------
scene(64.0, 68.8, (t) => {
  navyBG(t);
  pill(t, 64.05, W / 2, 490, 'EL OTRO LADO', 40, '#fff', NAVY);
  withA(eOut(P(t, 64.3, 64.7)), () => txt('LO QUE DICEN SUS DEFENSORES', W / 2, 580, 36, SOFT, 'Oswald', 'center', '600', 5));
  // 4 operadores compitiendo
  const ops = ['CLARO', 'ALTICE', 'VIVA', 'VIETTEL'];
  ops.forEach((n, i) => {
    const p = eBack(P(t, 64.5 + i * .18, 64.9 + i * .18)); if (p <= 0) return;
    const cx = 165 + i * 250, cy = 720 + Math.sin(t * 4 + i) * 8;
    X.save(); X.translate(cx, cy); X.scale(p, p); X.fillStyle = n === 'VIETTEL' ? RED : NAVY3; X.beginPath(); X.arc(0, 0, 82, 0, 7); X.fill();
    X.strokeStyle = 'rgba(255,255,255,.6)'; X.lineWidth = 4; X.stroke(); iconTower(0, 2, 70, '#fff', t + i);
    txt(n, 0, 120, 36, '#fff', 'Anton', 'center', '', 3); X.restore();
    // flechas de competencia
    if (i < 3 && t > 65.3) { const ax = cx + 125; withA(.5 + .5 * Math.sin(t * 6 + i), () => txt('⇄', ax, cy, 50, '#FF8A98', 'Oswald')); }
  });
  // gráfico de precio que baja
  const gx = 120, gy = 930, gw = 840, gh = 470;
  withA(eOut(P(t, 65.4, 65.8)), () => {
    X.fillStyle = 'rgba(6,17,42,.75)'; rr(60, gy - 40, W - 120, gh + 120, 26); X.fill();
    txt('PRECIOS', gx, gy + 14, 34, SOFT, 'Oswald', 'left', '700', 5);
    X.strokeStyle = 'rgba(255,255,255,.15)'; X.lineWidth = 2;
    for (let k = 0; k < 4; k++) { const y = gy + 60 + k * (gh - 60) / 3; X.beginPath(); X.moveTo(gx, y); X.lineTo(gx + gw, y); X.stroke(); }
    X.strokeStyle = 'rgba(255,255,255,.5)'; X.beginPath(); X.moveTo(gx, gy + 40); X.lineTo(gx, gy + gh); X.lineTo(gx + gw, gy + gh); X.stroke();
    txt('3 OPERADORAS', gx + 20, gy + gh + 40, 26, SOFT, 'Oswald', 'left', '600', 2); txt('4 OPERADORAS', gx + gw - 20, gy + gh + 40, 26, '#FF8A98', 'Oswald', 'right', '700', 2);
  });
  const pts = [[0, .08], [.15, .12], [.3, .1], [.42, .16], [.55, .35], [.68, .52], [.8, .66], [.9, .78], [1, .86]];
  const k = eIO(P(t, 65.7, 68.1));
  if (k > 0) {
    const pp = pts.map(([a, b]) => [gx + 20 + a * (gw - 60), gy + 70 + b * (gh - 110)]);
    const n = (pp.length - 1) * k; const i0 = Math.floor(n), f = n - i0;
    X.save(); X.strokeStyle = RED; X.lineWidth = 9; X.lineJoin = 'round'; X.lineCap = 'round'; shadow(20, 'rgba(227,18,44,.8)', 0);
    X.beginPath(); X.moveTo(pp[0][0], pp[0][1]); let ex = pp[0][0], ey = pp[0][1];
    for (let i = 1; i <= i0 && i < pp.length; i++) { X.lineTo(pp[i][0], pp[i][1]); ex = pp[i][0]; ey = pp[i][1]; }
    if (i0 < pp.length - 1) { ex = lerp(pp[i0][0], pp[i0 + 1][0], f); ey = lerp(pp[i0][1], pp[i0 + 1][1], f); X.lineTo(ex, ey); }
    X.stroke(); noShadow();
    X.fillStyle = '#fff'; X.beginPath(); X.arc(ex, ey, 13, 0, 7); X.fill(); X.restore();
    // área bajo la curva
  }
  const bp = eBack(P(t, 67.9, 68.3));
  if (bp > 0) { X.save(); X.translate(W / 2 + 230, gy + 130); X.scale(bp, bp); X.fillStyle = RED; rr(-200, -60, 400, 120, 20); X.fill(); txt('↓ MÁS BAJOS', 0, 3, 62, '#fff', 'Anton', 'center', '', 3); X.restore(); }
  withA(eOut(P(t, 65.6, 66.0)), () => txt('+ COMPETENCIA  =  ↓ PRECIOS', W / 2, 1520, 52, '#fff', 'Anton', 'center', '', 3));
}, 'otrolado');

// ---------- 10. ENCUESTA (68.8 – 74.3) ----------
scene(68.8, 74.3, (t) => {
  coverBlur('celular_2', 1.08 + (t - 68.8) * .01);
  grade(.55);
  const p = eBack(P(t, 68.85, 69.4)); if (p <= 0) return;
  const cx = W / 2, y0 = 520, cw = 940, ch = 960;
  X.save(); X.translate(cx, y0 + ch / 2); X.scale(lerp(.6, 1, p), lerp(.6, 1, p)); X.translate(-cx, -(y0 + ch / 2)); X.globalAlpha *= clamp(p);
  shadow(70, 'rgba(0,0,0,.6)', 30); X.fillStyle = '#fff'; rr(cx - cw / 2, y0, cw, ch, 40); X.fill(); noShadow();
  X.fillStyle = NAVY; X.beginPath(); X.roundRect(cx - cw / 2, y0, cw, 140, [40, 40, 0, 0]); X.fill();
  iconLupa(cx - cw / 2 + 85, y0 + 66, 72, '#fff', RED, RED, 1.2, 1);
  txt('ENCUESTA', cx - cw / 2 + 160, y0 + 72, 56, '#fff', 'Anton', 'left', '', 8);
  flagRD(cx + cw / 2 - 120, y0 + 45, 80, 52);
  const q = wrap('¿Te cambiarías a Viettel si fuera más barata?', cw - 120, 70, 'Anton');
  q.forEach((l, i) => txt(l, cx, y0 + 230 + i * 86, 70, NAVY, 'Anton', 'center', '', 1));
  const opts = [['SÍ, quiero precios bajos', '#1D7A46', 'SÍ'], ['NO, no confío', RED, 'NO']];
  opts.forEach(([s, col], i) => {
    const op = eOut(P(t, 70.1 + i * .35, 70.5 + i * .35)); if (op <= 0) return;
    const oy = y0 + 470 + i * 170; const hov = Math.max(0, Math.sin((t - 71.5) * 3 - i * Math.PI)) * (t > 71.5 ? 1 : 0);
    X.save(); X.globalAlpha *= op; X.translate((1 - op) * 80, 0);
    X.fillStyle = '#F1F4FA'; rr(cx - cw / 2 + 50, oy, cw - 100, 136, 68); X.fill();
    X.strokeStyle = col; X.lineWidth = 5 + hov * 4; rr(cx - cw / 2 + 50, oy, cw - 100, 136, 68); X.stroke();
    X.fillStyle = col; X.beginPath(); X.arc(cx - cw / 2 + 130, oy + 68, 44, 0, 7); X.fill();
    txt(i ? '✕' : '✓', cx - cw / 2 + 130, oy + 70, 50, '#fff', 'DejaVu Sans', 'center', 'bold');
    txt(s, cx - cw / 2 + 200, oy + 70, 54, NAVY, 'Oswald', 'left', '700');
    X.restore();
  });
  X.restore();
  // CTA comentarios
  const cp = eOut(P(t, 72.0, 72.4));
  withA(cp, () => {
    const by = 1555 + Math.abs(Math.sin(t * 4)) * -14;
    X.fillStyle = RED; rr(cx - 390, 1500, 780, 110, 55); X.fill();
    txt('DÉJALO EN LOS COMENTARIOS', cx - 30, 1557, 50, '#fff', 'Anton', 'center', '', 2);
    // flecha hacia abajo
    X.fillStyle = '#fff'; X.save(); X.translate(cx + 330, by); X.beginPath(); X.moveTo(-10, -26); X.lineTo(10, -26); X.lineTo(10, 2); X.lineTo(24, 2); X.lineTo(0, 28); X.lineTo(-24, 2); X.lineTo(-10, 2); X.closePath(); X.fill(); X.restore();
  });
}, 'encuesta');

// ---------- 11. CIERRE (74.3 – 78.5) ----------
scene(74.3, DURATION, (t) => {
  const r = eIO(P(t, 74.3, 74.75));
  X.fillStyle = RED; X.fillRect(0, 0, W, H);
  X.save(); X.beginPath(); X.arc(W / 2, H / 2, Math.hypot(W, H) * eIO(P(t, 74.45, 75.0)), 0, 7); X.clip();
  const g = X.createLinearGradient(0, 0, 0, H); g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, '#E7ECF5'); X.fillStyle = g; X.fillRect(0, 0, W, H);
  // líneas decorativas
  X.strokeStyle = 'rgba(10,29,61,.06)'; X.lineWidth = 2; for (let k = 0; k < 14; k++) { X.beginPath(); X.arc(W / 2, 860, 200 + k * 70 + ((t * 40) % 70), 0, 7); X.stroke(); }
  const lp = P(t, 74.9, 76.2);
  const sc = 1 + .03 * Math.sin(t * 2);
  X.save(); X.translate(W / 2, 860); X.scale(sc, sc); iconLupa(-30, -30, 520, NAVY, RED, RED, 1.05, lp); X.restore();
  const tp = eOut(P(t, 76.0, 76.5));
  withA(tp, () => {
    txt('CAPITAL', W / 2 - 4, 1260 + (1 - tp) * 40, 130, NAVY, 'Anton', 'center', '', 10);
    txt('CURIOSO', W / 2, 1390 + (1 - tp) * 40, 130, RED, 'Anton', 'center', '', 10);
  });
  const hp = eBack(P(t, 76.5, 76.9));
  if (hp > 0) { X.save(); X.translate(W / 2, 1530); X.scale(hp, hp); X.fillStyle = NAVY; rr(-280, -50, 560, 100, 50); X.fill(); txt('@capitalcuriosoo', 0, 2, 54, '#fff', 'Oswald', 'center', '700', 1); X.restore(); }
  withA(eOut(P(t, 77.0, 77.4)), () => txt('SÍGUENOS PARA MÁS', W / 2, 1640, 36, '#5A6886', 'Oswald', 'center', '600', 8));
  X.restore();
  // fundido final
  const fo = P(t, 78.1, 78.5); if (fo > 0) { X.fillStyle = `rgba(0,0,0,${fo})`; X.fillRect(0, 0, W, H); }
}, 'cierre');

// ---------- Subtítulos palabra por palabra (arriba) ----------
function subtitles(t) {
  if (t > 74.2) return;
  let ci = -1;
  for (let i = 0; i < CHUNKS.length; i++) {
    const c = CHUNKS[i], st = c[0].s - .05, nx = i + 1 < CHUNKS.length ? CHUNKS[i + 1][0].s - .05 : c[c.length - 1].e + 1.2;
    const en = Math.min(nx, c[c.length - 1].e + .7);
    if (t >= st && t < en) { ci = i; break; }
  }
  if (ci < 0) return;
  const c = CHUNKS[ci], sz = 78, maxw = 960, gap = 22;
  font(sz, 'Anton'); X.letterSpacing = '1px';
  const ws = c.map(o => ({ ...o, w2: X.measureText(o.w).width }));
  X.letterSpacing = '0px';
  const lines = [[]]; let lw = 0;
  for (const o of ws) { if (lw + o.w2 > maxw && lines[lines.length - 1].length) { lines.push([]); lw = 0; } lines[lines.length - 1].push(o); lw += o.w2 + gap; }
  const lh = 100, y0 = 300 - (lines.length - 1) * lh / 2;
  lines.forEach((ln, li) => {
    const tot = ln.reduce((a, o) => a + o.w2, 0) + gap * (ln.length - 1); let x = W / 2 - tot / 2;
    for (const o of ln) {
      const k = P(t, o.s - .04, o.s + .12);
      if (k > 0) {
        const idx = c.indexOf(c.find(q => q.s === o.s)); const nextS = idx + 1 < c.length ? c[idx + 1].s : o.e + .15;
        const active = t >= o.s - .04 && t < Math.max(nextS, o.e) - .02;
        const sc = lerp(.6, 1, eBack(k)) * (active ? 1.06 : 1);
        X.save(); X.translate(x + o.w2 / 2, y0 + li * lh); X.scale(sc, sc);
        if (active) { X.fillStyle = RED; rr(-o.w2 / 2 - 14, -sz * .62, o.w2 + 28, sz * 1.24, 14); X.fill(); }
        font(sz, 'Anton'); X.letterSpacing = '1px'; X.textAlign = 'center'; X.textBaseline = 'middle';
        X.lineJoin = 'round'; X.lineWidth = 12; X.strokeStyle = 'rgba(6,17,42,.95)'; if (!active) X.strokeText(o.w, 0, 3);
        X.fillStyle = '#fff'; X.fillText(o.w, 0, 3); X.letterSpacing = '0px';
        X.restore();
      }
      x += o.w2 + gap;
    }
  });
}

// ---------- Elementos fijos de marca ----------
function brandBug(t) {
  if (t > 74.3) return;
  const a = eOut(P(t, .3, .8)) * .95;
  withA(a, () => {
    const y = 1700;
    X.fillStyle = 'rgba(6,17,42,.78)'; rr(40, y - 34, 395, 68, 34); X.fill();
    X.fillStyle = '#fff'; X.beginPath(); X.arc(74, y, 26, 0, 7); X.fill();
    iconLupa(71, y - 3, 30, NAVY, RED, RED, 1.3, 1);
    txt('@capitalcuriosoo', 112, y + 1, 34, '#fff', 'Oswald', 'left', '600');
    X.fillStyle = 'rgba(6,17,42,.78)'; rr(W - 250, y - 34, 210, 68, 34); X.fill();
    flagRD(W - 232, y - 17, 52, 34); txt('RD · TELECOM', W - 168, y + 1, 26, '#fff', 'Oswald', 'left', '700', 1);
  });
}
function topShade() {
  const g = X.createLinearGradient(0, 0, 0, 520); g.addColorStop(0, 'rgba(6,17,42,.85)'); g.addColorStop(.6, 'rgba(6,17,42,.45)'); g.addColorStop(1, 'rgba(6,17,42,0)');
  X.fillStyle = g; X.fillRect(0, 0, W, 520);
}
// transición entre escenas: barrido rojo/azul
function transition(t) {
  for (const s of SCENES) {
    if (s.a === 0) continue; const d = t - s.a;
    if (d > -.18 && d < .22) {
      const k = (d + .18) / .4;
      X.save(); X.translate(W / 2, H / 2); X.rotate(-.35);
      const x = lerp(-W * 1.4, W * 1.4, eIO(k));
      X.fillStyle = RED; X.fillRect(x - 160, -H, 120, H * 2); X.fillStyle = 'rgba(255,255,255,.85)'; X.fillRect(x - 30, -H, 26, H * 2);
      X.fillStyle = NAVY; X.fillRect(x + 10, -H, 200, H * 2); X.restore();
      X.fillStyle = `rgba(255,255,255,${Math.max(0, .25 - Math.abs(d) * 1.3)})`; X.fillRect(0, 0, W, H);
    }
  }
}

let frameNo = 0;
window.renderAt = function (t) {
  X.setTransform(1, 0, 0, 1, 0, 0); X.globalAlpha = 1; X.clearRect(0, 0, W, H);
  const s = SCENES.find(s => t >= s.a && t < s.b) || SCENES[SCENES.length - 1];
  // pequeño "punch-in" al inicio de cada escena
  const d = t - s.a; const z = s.a > 0 ? 1 + .04 * Math.max(0, 1 - d / .35) : 1;
  X.save(); X.translate(W / 2, H / 2); X.scale(z, z); X.translate(-W / 2, -H / 2);
  s.fn(t); X.restore();
  if (t < 74.3) topShade();
  subtitles(t);
  brandBug(t);
  transition(t);
  // grano de película
  X.save(); X.globalAlpha = .05; X.globalCompositeOperation = 'overlay'; X.drawImage(GRAIN[(frameNo++) % GRAIN.length], 0, 0, W, H); X.restore();
};

// Efectos de sonido: [tiempo, tipo, volumen]
window.CUES = (() => {
  const c = [];
  SCENES.forEach(s => { if (s.a > 0) c.push([s.a - .25, 'whoosh', .8]); });
  c.push([.9, 'whoosh', .6], [2.0, 'impact', .9], [2.0, 'shimmer', .5], [4.6, 'hit', 1], [0.55, 'pop', .5]);
  c.push([6.8, 'pop', .6], [9.1, 'click', .8], [9.2, 'whoosh_s', .5], [10.75, 'ticker:3.25', .55], [14.0, 'ding', .8], [15.75, 'whoosh_s', .6]);
  c.push([18.0, 'pop', .6], [20.2, 'hit', .8], [20.2, 'ticker:1.1', .4], [21.2, 'blip', .5], [21.65, 'blip', .5], [22.1, 'blip', .5], [22.85, 'pop', .8]);
  c.push([25.9, 'ticker:1.5', .5], [27.4, 'ding', .7], [28.3, 'riser', .5], [29.2, 'pop', .7], [32.0, 'click', .8], [32.55, 'click', .8], [33.15, 'click', .8], [33.7, 'hit', .9], [34.0, 'pop', .8]);
  c.push([36.0, 'stamp', .9], [37.05, 'whoosh_s', .6], [39.7, 'riser', .45]);
  OPS11.forEach(([cc, t0]) => c.push([t0, cc === 'DOM' ? 'ding' : 'blip', cc === 'DOM' ? .8 : .45]));
  c.push([43.4, 'alarm', .55], [45.6, 'whoosh_s', .6], [49.15, 'whoosh_s', .6], [49.6, 'whoosh_s', .5]);
  c.push([52.9, 'whoosh_s', .5], [53.85, 'click', .6], [54.9, 'stamp', 1], [54.4, 'pop', .4]);
  c.push([57.4, 'riser', .45], [57.6, 'impact', .5], [59.45, 'pop', .7], [59.9, 'pop', .7], [60.4, 'pop', .7], [59.95, 'whoosh_s', .4], [60.6, 'whoosh_s', .4], [61.2, 'click', .5]);
  c.push([64.05, 'pop', .6], [64.5, 'blip', .4], [64.68, 'blip', .4], [64.86, 'blip', .4], [65.04, 'blip', .4], [65.7, 'riser_down', .5], [67.9, 'hit', .8]);
  c.push([68.85, 'pop', .8], [70.1, 'click', .7], [70.45, 'click', .7], [72.0, 'pop', .7]);
  c.push([74.45, 'whoosh', .8], [74.9, 'shimmer', .6], [76.0, 'hit', .8], [76.5, 'pop', .7]);
  return c;
})();

window.ready = (async () => {
  const ff = [['Anton', 'Anton-Regular.ttf'], ['Oswald', 'Oswald.ttf'], ['Bebas', 'BebasNeue-Regular.ttf']];
  for (const [n, f] of ff) { const fc = new FontFace(n, `url(../fonts/${f})`, n === 'Oswald' ? { weight: '200 700' } : {}); await fc.load(); document.fonts.add(fc); }
  await Promise.all(IMG_NAMES.map(loadImg));
  makeBlur('celular_2', 18); makeWhiteLogo(); makeGrain();
  window.DURATION = DURATION; window.FPS = FPS;
  window.renderAt(0);
  return true;
})();
