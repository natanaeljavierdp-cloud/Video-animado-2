// Capital Curioso — "EE. UU. vs China... en RD"  (motor de animación por fotograma)
const C = document.getElementById('c'), X = C.getContext('2d');
const W = 1080, H = 1920;
const COL = {
  n0: '#050b1a', n1: '#0a1733', n2: '#122a5c', n3: '#1d3a78', blue: '#4f7ad6', lblue: '#9db8f2',
  red: '#d7263d', red2: '#ff4057', white: '#f4f6fb', gray: '#9aa6bf', paper: '#f3efe6', ink: '#0d1b3d', gold: '#ffd84d'
};
const IMG = {};
let SUBS, GEOW, F = {};
const BG = {};
const OFF = {};

// ---------- utilidades ----------
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, p) => a + (b - a) * p;
const P = (t, a, d) => clamp((t - a) / d);
const eo = p => 1 - Math.pow(1 - p, 3);
const eio = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
const ei = p => p * p * p;
const eback = p => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };
const EO = (t, a, d) => eo(P(t, a, d));
const EB = (t, a, d) => eback(P(t, a, d));

function rr(x, y, w, h, r, ctx = X) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function font(size, fam = 'Bebas', weight = 400) { return fam === 'Bebas' ? `${size}px Bebas` : `${weight} ${size}px Inter`; }
function txt(s, x, y, o = {}) {
  const ctx = o.ctx || X;
  ctx.save();
  ctx.font = font(o.size || 60, o.fam || 'Bebas', o.w || 800);
  ctx.textAlign = o.align || 'center'; ctx.textBaseline = o.base || 'alphabetic';
  ctx.letterSpacing = (o.ls || 0) + 'px';
  ctx.globalAlpha *= (o.a === undefined ? 1 : o.a);
  if (o.shadow) { ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = o.shadow; ctx.shadowOffsetY = o.shadow / 3; }
  if (o.stroke) { ctx.lineJoin = 'round'; ctx.lineWidth = o.stroke; ctx.strokeStyle = o.sc || '#000'; ctx.strokeText(s, x, y); }
  ctx.fillStyle = o.c || COL.white; ctx.fillText(s, x, y);
  ctx.restore();
}
function tw(s, size, fam = 'Bebas', w = 800, ls = 0) { X.save(); X.font = font(size, fam, w); X.letterSpacing = ls + 'px'; const m = X.measureText(s).width; X.restore(); return m; }
function wrap(s, size, fam, w, maxW) {
  const words = s.split(' '); const lines = []; let cur = '';
  for (const wd of words) { const tst = cur ? cur + ' ' + wd : wd; if (tw(tst, size, fam, w) > maxW && cur) { lines.push(cur); cur = wd; } else cur = tst; }
  if (cur) lines.push(cur); return lines;
}
function cover(img, x, y, w, h, zoom = 1, fx = .5, fy = .5, ctx = X) {
  const s = Math.max(w / img.width, h / img.height) * zoom;
  const iw = img.width * s, ih = img.height * s;
  ctx.drawImage(img, x + (w - iw) * fx, y + (h - ih) * fy, iw, ih);
}
function star(ctx, cx, cy, r, rot = -Math.PI / 2, inner = .382) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) { const rad = i % 2 ? r * inner : r; const a = rot + i * Math.PI / 5; ctx.lineTo(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad); }
  ctx.closePath(); ctx.fill();
}
function withA(a, fn) { if (a <= 0.001) return; X.save(); X.globalAlpha *= a; fn(); X.restore(); }
function scaleAt(cx, cy, s, fn) { X.save(); X.translate(cx, cy); X.scale(s, s); X.translate(-cx, -cy); fn(); X.restore(); }

// ---------- carga ----------
async function loadImg(n) { return new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = 'img/' + n + '.jpg'; }); }
async function init() {
  const names = ['banderas', 'carton_almacen', 'carton_linea', 'embajada_china', 'embajador_china', 'fabrica', 'fabrica_aerea', 'fabrica_mapa', 'santo_domingo', 'sanz_lovaton', 'segura'];
  await Promise.all(names.map(async n => IMG[n] = await loadImg(n)));
  SUBS = await (await fetch('subs.json')).json();
  const w10 = await (await fetch('node_modules/world-atlas/countries-10m.json')).json();
  const w50 = await (await fetch('node_modules/world-atlas/countries-50m.json')).json();
  const f10 = topojson.feature(w10, w10.objects.countries).features;
  const f50 = topojson.feature(w50, w50.objects.countries).features;
  F.dr = f10.find(f => f.id === '214'); F.ht = f10.find(f => f.id === '332');
  F.near = f10.filter(f => ['192', '630', '388', '044', '796'].includes(f.id)); // Cuba, PR, Jamaica, Bahamas, Turks
  F.cn = f50.find(f => f.id === '156');
  F.tw = f50.find(f => f.id === '158');
  const us = f50.find(f => f.id === '840');
  F.us = { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: us.geometry.coordinates.filter(p => { const [lo, la] = p[0][0]; return lo > -126 && lo < -65 && la > 24 && la < 50; }) } };
  await document.fonts.load('80px Bebas'); for (const w of [600, 700, 800, 900]) await document.fonts.load(`${w} 40px Inter`);
  await document.fonts.ready;
  buildOff();
  window.READY = true;
}

function mkCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function buildOff() {
  // fondos difuminados
  for (const n of ['santo_domingo', 'carton_linea', 'carton_almacen', 'carton_almacen']) {
    const c = mkCanvas(W, H), g = c.getContext('2d');
    g.filter = 'blur(14px) saturate(.6)'; cover(IMG[n], -40, -40, W + 80, H + 80, 1, .5, .5, g); g.filter = 'none';
    g.fillStyle = 'rgba(6,14,36,.78)'; g.fillRect(0, 0, W, H);
    BG[n] = c;
  }
  // grano
  const gn = mkCanvas(512, 512), gg = gn.getContext('2d'), id = gg.createImageData(512, 512);
  for (let i = 0; i < id.data.length; i += 4) { const v = Math.random() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
  gg.putImageData(id, 0, 0); OFF.grain = gn;
  // banderas
  OFF.us = flagUS(480, 300); OFF.cn = flagCN(480, 300);
  // sello
  OFF.stamp = stampCanvas();
}
function flagUS(w, h) {
  const c = mkCanvas(w, h), g = c.getContext('2d');
  for (let i = 0; i < 13; i++) { g.fillStyle = i % 2 ? '#ffffff' : '#b22234'; g.fillRect(0, i * h / 13, w, h / 13 + 1); }
  const cw = w * .4, ch = h * 7 / 13; g.fillStyle = '#3c3b6e'; g.fillRect(0, 0, cw, ch);
  g.fillStyle = '#fff';
  for (let r = 0; r < 9; r++) { const n = r % 2 ? 5 : 6; for (let k = 0; k < n; k++) { const x = cw / 12 * (2 * k + 1 + (r % 2)); const y = ch / 10 * (r + 1); star(g, x, y, ch / 22); } }
  return c;
}
function flagCN(w, h) {
  const c = mkCanvas(w, h), g = c.getContext('2d'); const u = w / 30;
  g.fillStyle = '#de2910'; g.fillRect(0, 0, w, h); g.fillStyle = '#ffde00';
  star(g, 5 * u, 5 * u, 3 * u);
  for (const [x, y] of [[10, 2], [12, 4], [12, 7], [10, 9]]) { const a = Math.atan2(5 - y, 5 - x); star(g, x * u, y * u, u, a); }
  return c;
}
function stampCanvas() {
  const c = mkCanvas(900, 420), g = c.getContext('2d');
  g.strokeStyle = COL.red; g.fillStyle = COL.red;
  g.lineWidth = 16; rr(20, 20, 860, 380, 26, g); g.stroke();
  g.lineWidth = 6; rr(46, 46, 808, 328, 16, g); g.stroke();
  g.font = '200px Bebas'; g.textAlign = 'center'; g.letterSpacing = '8px'; g.fillText('CLAUSURADA', 450, 245);
  g.font = '88px Bebas'; g.letterSpacing = '14px'; g.fillText('— 1 NOV —', 450, 340);
  g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 2600; i++) { g.globalAlpha = Math.random() * .8; const r = Math.random() * 4; g.beginPath(); g.arc(Math.random() * 900, Math.random() * 420, r, 0, 7); g.fill(); }
  return c;
}

// ---------- elementos comunes ----------
function background(t, img, a = 1) {
  const g = X.createRadialGradient(540, 760, 80, 540, 900, 1300);
  g.addColorStop(0, COL.n2); g.addColorStop(.55, COL.n1); g.addColorStop(1, COL.n0);
  X.fillStyle = g; X.fillRect(0, 0, W, H);
  if (img && BG[img]) withA(a, () => { const z = 1 + .04 * Math.sin(t * .2); scaleAt(540, 960, z, () => X.drawImage(BG[img], 0, 0)); });
  // retícula de datos
  X.save(); X.strokeStyle = 'rgba(120,160,255,.07)'; X.lineWidth = 1.5;
  const off = (t * 12) % 90;
  for (let x = -90 + off; x < W + 90; x += 90) { X.beginPath(); X.moveTo(x, 0); X.lineTo(x, H); X.stroke(); }
  for (let y = -90 + off; y < H + 90; y += 90) { X.beginPath(); X.moveTo(0, y); X.lineTo(W, y); X.stroke(); }
  X.restore();
}
function finishFX(t) {
  // viñeta
  const g = X.createRadialGradient(540, 960, 500, 540, 960, 1250);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.55)');
  X.fillStyle = g; X.fillRect(0, 0, W, H);
  // grano
  X.save(); X.globalAlpha = .05; X.globalCompositeOperation = 'overlay';
  const ox = Math.floor((t * 977) % 512), oy = Math.floor((t * 613) % 512);
  for (let x = -ox; x < W; x += 512) for (let y = -oy; y < H; y += 512) X.drawImage(OFF.grain, x, y);
  X.restore();
}
function photoCard(img, x, y, w, h, t, t0, o = {}) {
  const p = EO(t, t0, .45); if (p <= 0) return;
  const z = lerp(o.z0 || 1.04, o.z1 || 1.14, P(t, t0, o.dur || 9));
  X.save();
  X.globalAlpha *= p;
  const s = lerp(.92, 1, p); X.translate(x + w / 2, y + h / 2 + (1 - p) * 40); X.scale(s, s); X.translate(-(x + w / 2), -(y + h / 2));
  X.shadowColor = 'rgba(0,0,0,.6)'; X.shadowBlur = 40; X.shadowOffsetY = 16;
  rr(x, y, w, h, 26); X.fillStyle = '#000'; X.fill(); X.shadowColor = 'transparent';
  X.save(); rr(x, y, w, h, 26); X.clip(); cover(img, x, y, w, h, z, o.fx ?? .5, o.fy ?? .5);
  if (o.img2) withA(EO(t, o.t2, .6), () => cover(o.img2, x, y, w, h, lerp(1.04, 1.12, P(t, o.t2, 6)), o.fx2 ?? .5, o.fy2 ?? .5));
  const gg = X.createLinearGradient(0, y + h * .55, 0, y + h); gg.addColorStop(0, 'rgba(5,11,26,0)'); gg.addColorStop(1, 'rgba(5,11,26,.75)');
  X.fillStyle = gg; X.fillRect(x, y, w, h);
  if (o.tag) { X.fillStyle = 'rgba(5,11,26,.65)'; X.fillRect(x, y, w, 0); }
  X.restore();
  X.lineWidth = 4; X.strokeStyle = 'rgba(255,255,255,.85)'; rr(x, y, w, h, 26); X.stroke();
  // esquinero rojo
  X.fillStyle = COL.red; X.fillRect(x + 30, y - 4, 120, 8);
  X.restore();
}
function lowerThird(name, role, x, y, t, t0) {
  const p1 = EO(t, t0, .4), p2 = EO(t, t0 + .25, .4);
  if (p1 <= 0) return;
  const nw = tw(name, 70, 'Bebas', 400, 2) + 60, rw = tw(role, 34, 'Inter', 700) + 50;
  X.save();
  X.beginPath(); X.rect(x, y - 10, Math.max(nw, rw) * p1 + 20, 200); X.clip();
  X.fillStyle = COL.red; X.fillRect(x, y, nw, 84);
  txt(name, x + 30, y + 66, { size: 70, align: 'left', ls: 2 });
  X.restore();
  if (p2 > 0) { X.save(); X.beginPath(); X.rect(x, y + 84, rw * p2, 70); X.clip();
    X.fillStyle = COL.ink; X.fillRect(x, y + 84, rw, 62); X.fillStyle = COL.white; X.fillRect(x, y + 84, 8, 62);
    txt(role, x + 30, y + 127, { size: 34, fam: 'Inter', w: 700, align: 'left' }); X.restore(); }
}
function sourceTag(s, t, t0, y = 1590) {
  const p = EO(t, t0, .4); if (p <= 0) return;
  const w = tw('FUENTE: ' + s, 30, 'Inter', 700) + 50;
  withA(p, () => {
    X.save(); X.translate((1 - p) * -30, 0);
    rr(540 - w / 2, y - 40, w, 58, 29); X.fillStyle = 'rgba(5,11,26,.82)'; X.fill();
    X.strokeStyle = 'rgba(255,255,255,.25)'; X.lineWidth = 2; X.stroke();
    X.font = font(30, 'Inter', 800); const fw = X.measureText('FUENTE: ').width;
    txt('FUENTE:', 540 - w / 2 + 25, y - 1, { size: 30, fam: 'Inter', w: 800, align: 'left', c: COL.red2 });
    txt(s, 540 - w / 2 + 25 + fw, y - 1, { size: 30, fam: 'Inter', w: 700, align: 'left', c: COL.white });
    X.restore();
  });
}
function headline(s, y, t, t0, o = {}) {
  const p = EB(t, t0, .45); if (P(t, t0, .01) <= 0) return;
  withA(clamp(P(t, t0, .2)), () => scaleAt(540, y - 40, lerp(.6, 1, p), () => {
    const size = o.size || 120; const w = tw(s, size, 'Bebas', 400, 3);
    if (o.box) { X.fillStyle = o.box; X.fillRect(540 - w / 2 - 30, y - size * .82, w + 60, size * 1.0); }
    txt(s, 540, y, { size, ls: 3, c: o.c || COL.white, shadow: o.box ? 0 : 20 });
  }));
}
function chip(s, x, y, t, t0, o = {}) {
  const p = EO(t, t0, .35); if (p <= 0) return;
  const size = o.size || 34; const w = tw(s, size, 'Inter', 800, 2) + 50;
  withA(p, () => { const xx = o.align === 'left' ? x : x - w / 2;
    rr(xx, y - size - 10, w * lerp(.3, 1, p), size + 30, 8); X.fillStyle = o.bg || COL.red; X.fill();
    if (p > .6) txt(s, xx + 25, y + 4, { size, fam: 'Inter', w: 800, align: 'left', ls: 2, c: o.c || COL.white, a: (p - .6) / .4 }); });
}

// ---------- íconos ----------
function factoryIcon(cx, by, s, col) {
  X.save(); X.translate(cx, by); X.scale(s / 100, s / 100); X.fillStyle = col;
  X.beginPath(); X.moveTo(-50, 0); X.lineTo(-50, -40); X.lineTo(-25, -60); X.lineTo(-25, -40); X.lineTo(0, -60); X.lineTo(0, -40); X.lineTo(25, -60); X.lineTo(25, -40);
  X.lineTo(30, -40); X.lineTo(30, -95); X.lineTo(44, -95); X.lineTo(44, -40); X.lineTo(50, -40); X.lineTo(50, 0); X.closePath(); X.fill();
  X.fillStyle = COL.n1; for (let i = 0; i < 4; i++) X.fillRect(-42 + i * 22, -28, 13, 12);
  X.fillRect(-8, -16, 16, 16);
  X.restore();
}
function buildingIcon(cx, by, s, col) {
  X.save(); X.translate(cx, by); X.scale(s / 100, s / 100); X.fillStyle = col;
  X.fillRect(-32, -110, 64, 110); X.fillRect(-40, -114, 80, 8);
  X.fillStyle = COL.n1; for (let r = 0; r < 5; r++) for (let k = 0; k < 3; k++) X.fillRect(-24 + k * 18, -98 + r * 19, 11, 11);
  X.fillRect(-8, -16, 16, 16); X.restore();
}
function xMark(cx, cy, r, p) {
  if (p <= 0) return; const s = eback(clamp(p * 1.6));
  X.save(); X.translate(cx, cy); X.scale(s, s); X.beginPath(); X.arc(0, 0, r, 0, 7); X.fillStyle = COL.red; X.fill();
  X.strokeStyle = '#fff'; X.lineWidth = r * .22; X.lineCap = 'round';
  const a = clamp((p - .3) / .35), b = clamp((p - .55) / .35), q = r * .45;
  if (a > 0) { X.beginPath(); X.moveTo(-q, -q); X.lineTo(-q + 2 * q * a, -q + 2 * q * a); X.stroke(); }
  if (b > 0) { X.beginPath(); X.moveTo(q, -q); X.lineTo(q - 2 * q * b, -q + 2 * q * b); X.stroke(); }
  X.restore();
}
function calendar(cx, cy, s, day, month, o = {}) {
  X.save(); X.translate(cx, cy); X.scale(s, s);
  X.shadowColor = 'rgba(0,0,0,.5)'; X.shadowBlur = 30; rr(-150, -150, 300, 300, 26); X.fillStyle = '#fff'; X.fill(); X.shadowColor = 'transparent';
  X.save(); rr(-150, -150, 300, 300, 26); X.clip(); X.fillStyle = COL.red; X.fillRect(-150, -150, 300, 84); X.restore();
  X.fillStyle = COL.ink; for (const x of [-80, 80]) { rr(x - 10, -172, 20, 50, 10); X.fill(); }
  txt(month, 0, -88, { size: 56, ls: 6 });
  txt(String(day), 0, 108, { size: 210, c: COL.ink, ...(o.dayOpts || {}) });
  X.restore();
}
function warnIcon(cx, cy, s) {
  X.save(); X.translate(cx, cy); X.scale(s / 100, s / 100);
  X.beginPath(); X.moveTo(0, -50); X.lineTo(50, 40); X.lineTo(-50, 40); X.closePath(); X.fillStyle = COL.gold; X.lineJoin = 'round'; X.lineWidth = 10; X.strokeStyle = COL.gold; X.stroke(); X.fill();
  X.fillStyle = COL.ink; X.fillRect(-5, -20, 10, 36); X.fillRect(-5, 22, 10, 10); X.restore();
}
function padlock(cx, cy, s, label) {
  X.save(); X.translate(cx, cy); X.scale(s / 100, s / 100);
  X.strokeStyle = '#cfd6e6'; X.lineWidth = 16; X.beginPath(); X.arc(0, -40, 34, Math.PI, 0); X.lineTo(34, -10); X.moveTo(-34, -40); X.lineTo(-34, -10); X.stroke();
  rr(-60, -16, 120, 100, 14); X.fillStyle = COL.gold; X.fill(); X.strokeStyle = '#b8920d'; X.lineWidth = 4; X.stroke();
  txt(label, 0, 54, { size: 64, c: COL.ink, ls: 2 });
  X.restore();
}
function lupa(cx, cy, r, p1, p2, col = '#fff') {
  X.save(); X.lineCap = 'round'; X.strokeStyle = col; X.lineWidth = r * .2;
  X.beginPath(); X.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * p1); X.stroke();
  if (p2 > 0) { const a = Math.PI / 4, x0 = cx + Math.cos(a) * r * 1.1, y0 = cy + Math.sin(a) * r * 1.1, L = r * .95 * p2;
    X.lineWidth = r * .3; X.beginPath(); X.moveTo(x0, y0); X.lineTo(x0 + Math.cos(a) * L, y0 + Math.sin(a) * L); X.stroke(); }
  X.restore();
}
function wavingFlag(img, x, y, w, h, t, poleSide, amp = 10) {
  const N = 48, sw = w / N;
  for (let i = 0; i < N; i++) {
    const u = poleSide === 'left' ? i / N : 1 - i / N;
    const ph = t * 7 - u * 7;
    const dy = Math.sin(ph) * amp * u;
    const sx = img.width / N * i;
    X.drawImage(img, sx, 0, img.width / N + 1, img.height, x + i * sw, y + dy, sw + 1, h);
    const sh = Math.cos(ph) * .22 * u;
    X.fillStyle = sh > 0 ? `rgba(255,255,255,${sh * .5})` : `rgba(0,0,0,${-sh})`; X.fillRect(x + i * sw, y + dy, sw + 1, h);
  }
  // asta
  const px = poleSide === 'left' ? x - 10 : x + w + 2;
  X.fillStyle = '#d9dde6'; X.fillRect(px, y - 30, 10, h + 260); X.beginPath(); X.arc(px + 5, y - 34, 12, 0, 7); X.fillStyle = COL.gold; X.fill();
}
function cardboardBox(cx, cy, s) {
  X.save(); X.translate(cx, cy); X.scale(s, s);
  // sombra
  X.fillStyle = 'rgba(0,0,0,.45)'; X.beginPath(); X.ellipse(0, 175, 300, 40, 0, 0, 7); X.fill();
  // cara frontal
  X.fillStyle = '#c48a4e'; X.beginPath(); X.moveTo(-250, -40); X.lineTo(60, -40); X.lineTo(60, 170); X.lineTo(-250, 170); X.closePath(); X.fill();
  // lateral
  X.fillStyle = '#9c6a36'; X.beginPath(); X.moveTo(60, -40); X.lineTo(230, -120); X.lineTo(230, 90); X.lineTo(60, 170); X.closePath(); X.fill();
  // tapa
  X.fillStyle = '#d9a466'; X.beginPath(); X.moveTo(-250, -40); X.lineTo(-80, -120); X.lineTo(230, -120); X.lineTo(60, -40); X.closePath(); X.fill();
  // cinta
  X.fillStyle = 'rgba(240,210,150,.9)'; X.beginPath(); X.moveTo(-110, -40); X.lineTo(60, -120); X.lineTo(100, -120); X.lineTo(-70, -40); X.closePath(); X.fill();
  X.fillRect(-110, -40, 40, 60);
  // impresión
  X.strokeStyle = 'rgba(70,40,15,.7)'; X.lineWidth = 5; X.strokeRect(-215, 40, 240, 100);
  txt('CARTÓN', -95, 88, { size: 50, c: 'rgba(70,40,15,.8)', ls: 4 });
  txt('SANTO DOMINGO · RD', -95, 126, { size: 26, fam: 'Inter', w: 800, c: 'rgba(70,40,15,.8)' });
  // flechas "este lado arriba"
  X.fillStyle = 'rgba(70,40,15,.7)'; for (const ax of [120, 175]) { X.beginPath(); X.moveTo(ax, -10); X.lineTo(ax + 18, 15); X.lineTo(ax - 18, 15); X.fill(); X.fillRect(ax - 5, 14, 10, 30); }
  X.restore();
}

// ---------- subtítulos (arriba, palabra por palabra) ----------
function subtitles(t) {
  if (t > 86) return;
  let ci = -1;
  for (let i = 0; i < SUBS.length; i++) if (SUBS[i][0][0] <= t + .02) ci = i;
  if (ci < 0) return;
  const ch = SUBS[ci]; const last = ch[ch.length - 1];
  const next = SUBS[ci + 1];
  if (t > last[1] + .6 && !(next && next[0][0] - last[1] < .8 && t < next[0][0])) return;
  const size = 96, gap = 24, y = 300;
  const ws = ch.map(w => w[2].toUpperCase());
  let widths = ws.map(s => tw(s, size, 'Bebas', 400, 2));
  let total = widths.reduce((a, b) => a + b, 0) + gap * (ws.length - 1);
  const sc = Math.min(1, 960 / total);
  X.save(); X.translate(540, y); X.scale(sc, sc);
  let x = -total / 2;
  ch.forEach((w, i) => {
    const st = w[0], en = (i < ch.length - 1 ? ch[i + 1][0] : w[1] + .25);
    if (t + .02 >= st) {
      const p = EB(t, st, .18);
      const active = t >= st && t < en;
      X.save(); X.translate(x + widths[i] / 2, -30); X.scale(lerp(.7, 1, p), lerp(.7, 1, p));
      if (active) { rr(-widths[i] / 2 - 14, -66, widths[i] + 28, 98, 12); X.fillStyle = COL.red; X.fill(); }
      txt(ws[i], 0, 30, { size, ls: 2, stroke: active ? 0 : 10, sc: 'rgba(0,0,0,.85)', c: COL.white });
      X.restore();
    }
    x += widths[i] + gap;
  });
  X.restore();
}
function brand(t) {
  if (t > 85.9) return;
  X.save(); lupa(76, 92, 15, 1, 1, COL.white); txt('?', 76, 103, { size: 30, c: COL.red2 });
  txt('CAPITAL CURIOSO', 108, 108, { size: 44, align: 'left', ls: 3 });
  X.fillStyle = COL.red; X.fillRect(108, 120, 90, 5);
  X.restore();
}

// ---------- ESCENA 1: banderas sobre la caja ----------
function s1(t) {
  background(t, 'santo_domingo', 1);
  // caja
  const bp = EB(t, 0, .45);
  cardboardBox(560, 1290, lerp(.4, 1, bp) * 1.0);
  // banderas
  const IMPACT = 3.62;
  const fw = 400, fh = 250, fy = 880;
  let push = 0;
  let offL, offR;
  if (t < IMPACT) { const p = ei(P(t, .4, IMPACT - .4)); offL = lerp(-640, 0, p); offR = lerp(640, 0, p); }
  else { const d = t - IMPACT; push = 26 * Math.sin(d * 5.2) * (0.5 + .5 * Math.exp(-d * .8)); const rb = 40 * Math.exp(-d * 9) * Math.sin(d * 30); offL = -Math.abs(rb) + push; offR = Math.abs(rb) + push; }
  wavingFlag(OFF.us, 540 - fw + offL - 2, fy + Math.sin(t * 3) * 4, fw, fh, t, 'left');
  wavingFlag(OFF.cn, 540 + offR + 2, fy + Math.sin(t * 3 + 1) * 4, fw, fh, t + .5, 'right');
  // impacto
  if (t >= IMPACT && t < IMPACT + .7) {
    const d = (t - IMPACT) / .7; const cx = 540 + push, cy = fy + fh / 2;
    X.save(); X.globalAlpha = 1 - d; X.strokeStyle = COL.gold; X.lineWidth = 8; X.lineCap = 'round';
    for (let i = 0; i < 14; i++) { const a = i / 14 * Math.PI * 2 + .3; const r0 = 40 + d * 120, r1 = r0 + 80 * (1 - d); X.beginPath(); X.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); X.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1); X.stroke(); }
    X.beginPath(); X.arc(cx, cy, 30 + d * 240, 0, 7); X.lineWidth = 6 * (1 - d); X.strokeStyle = '#fff'; X.stroke();
    X.restore();
  }
  // título
  headline('EE. UU. vs CHINA', 600, t, 0, { size: 158 });
  if (t >= 0) { // colorear "vs"
  }
  const p2 = EB(t, 1.5, .4);
  if (t >= 1.5) withA(P(t, 1.5, .15), () => scaleAt(540, 690, lerp(.5, 1, p2), () => {
    const s = '...EN RD'; const w = tw(s, 140, 'Bebas', 400, 4);
    X.fillStyle = COL.red; X.fillRect(540 - w / 2 - 34, 610, w + 68, 130);
    txt(s, 540, 724, { size: 140, ls: 4 });
  }));
}

// ---------- ESCENA 2: mapa ----------
const SD = [-69.93, 18.48], SADG = [-69.61, 18.56];
function s2(t) {
  background(t);
  const px = 40, py = 540, pw = 1000, ph = 760;
  const ap = EO(t, 5.56, .5);
  // encabezado
  chip('FÁBRICA DE CARTÓN', 540, 470, t, 5.7, { size: 30, bg: COL.ink });
  withA(ap, () => {
    X.save(); rr(px, py, pw, ph, 28); X.clip();
    X.fillStyle = '#081430'; X.fillRect(px, py, pw, ph);
    const k = lerp(1, 3.2, eio(P(t, 6.0, 2.3)));
    const c0 = [-70.3, 18.85], c = [lerp(c0[0], -69.74, eio(P(t, 6.0, 2.3))), lerp(c0[1], 18.53, eio(P(t, 6.0, 2.3)))];
    const proj = d3.geoMercator().center(c).scale(8200 * k).translate([px + pw / 2, py + ph / 2]);
    const path = d3.geoPath(proj, X);
    X.strokeStyle = 'rgba(120,160,255,.12)'; X.lineWidth = 1.5; X.beginPath(); path(d3.geoGraticule().step([k > 3 ? .1 : .5, k > 3 ? .1 : .5])()); X.stroke();
    X.beginPath(); for (const f of F.near) path(f); X.fillStyle = '#10234b'; X.fill();
    X.beginPath(); path(F.ht); X.fillStyle = '#13285a'; X.fill(); X.strokeStyle = 'rgba(160,190,255,.35)'; X.lineWidth = 2; X.stroke();
    X.beginPath(); path(F.dr); X.fillStyle = COL.n3; X.fill(); X.strokeStyle = COL.lblue; X.lineWidth = 3; X.stroke();
    if (k < 2.5) withA(1 - P(k, 1.6, .8), () => { const [x, y] = proj([-70.6, 19.0]); txt('REPÚBLICA DOMINICANA', x, y, { size: 56, ls: 4, c: 'rgba(255,255,255,.85)' }); });
    // Santo Domingo
    const sd = proj(SD);
    withA(EO(t, 6.0, .4), () => { X.beginPath(); X.arc(sd[0], sd[1], 12, 0, 7); X.fillStyle = '#fff'; X.fill();
      txt('SANTO DOMINGO', sd[0], sd[1] + 60, { size: 46, ls: 2, shadow: 10 }); });
    // San Antonio de Guerra
    const sg = proj(SADG);
    const hp = EO(t, 8.16, .5);
    if (hp > 0) {
      const pulse = (t * 1.2) % 1;
      X.beginPath(); X.arc(sg[0], sg[1], 110 * hp, 0, 7); X.fillStyle = 'rgba(215,38,61,.28)'; X.fill();
      X.strokeStyle = COL.red2; X.lineWidth = 5; X.setLineDash([14, 10]); X.lineDashOffset = -t * 30; X.stroke(); X.setLineDash([]);
      X.beginPath(); X.arc(sg[0], sg[1], 30 + pulse * 120, 0, 7); X.strokeStyle = `rgba(255,64,87,${1 - pulse})`; X.lineWidth = 4; X.stroke();
      X.beginPath(); X.arc(sg[0], sg[1], 16, 0, 7); X.fillStyle = COL.red2; X.fill(); X.lineWidth = 5; X.strokeStyle = '#fff'; X.stroke();
      // etiqueta
      const lp = EB(t, 8.3, .4); const s = 'SAN ANTONIO DE GUERRA'; const w = tw(s, 54, 'Bebas', 400, 2) + 44;
      const lx = clamp(sg[0] - w / 2, px + 20, px + pw - w - 20), ly = sg[1] - 200;
      scaleAt(sg[0], ly + 40, lerp(.5, 1, lp), () => withA(P(t, 8.3, .1), () => {
        X.strokeStyle = '#fff'; X.lineWidth = 3; X.beginPath(); X.moveTo(sg[0], sg[1] - 20); X.lineTo(sg[0], ly + 74); X.stroke();
        X.fillStyle = COL.red; X.fillRect(lx, ly, w, 74); txt(s, lx + w / 2, ly + 58, { size: 54, ls: 2 });
      }));
      // inset satelital
      const ip = EB(t, 8.9, .45);
      if (ip > 0) withA(P(t, 8.9, .15), () => {
        const ix = px + pw - 190, iy = py + ph - 190, ir = 150 * ip;
        X.strokeStyle = 'rgba(255,255,255,.7)'; X.lineWidth = 3; X.setLineDash([8, 8]); X.beginPath(); X.moveTo(sg[0], sg[1]); X.lineTo(ix, iy); X.stroke(); X.setLineDash([]);
        X.save(); X.beginPath(); X.arc(ix, iy, ir, 0, 7); X.clip(); cover(IMG.fabrica_mapa, ix - ir, iy - ir, ir * 2, ir * 2, 1.25 + .1 * P(t, 8.9, 4), .5, .4); X.restore();
        X.beginPath(); X.arc(ix, iy, ir, 0, 7); X.lineWidth = 7; X.strokeStyle = '#fff'; X.stroke();
        txt('VISTA SATELITAL', ix, iy + ir + 10, { size: 30, c: '#fff', shadow: 8, a: ip });
      });
    }
    X.restore();
    X.lineWidth = 3; X.strokeStyle = 'rgba(255,255,255,.5)'; rr(px, py, pw, ph, 28); X.stroke();
  });
  // nombre
  if (t >= 6.44) {
    const p = EB(t, 6.44, .4);
    withA(P(t, 6.44, .12), () => scaleAt(540, 610, lerp(.6, 1, p), () => {
      const w = tw('CARTESA', 110, 'Bebas', 400, 6) + 70;
      X.fillStyle = COL.white; X.fillRect(540 - w / 2, 540, w, 120); txt('CARTESA', 540, 640, { size: 110, ls: 6, c: COL.ink });
    }));
  }
  // íconos: 3 naves + 1 edificio
  const iy = 1530;
  const times = [9.52, 9.8, 10.04];
  times.forEach((tt, i) => { const p = EB(t, tt, .35); if (P(t, tt, .01) > 0) factoryIcon(170 + i * 150, iy, 130 * p, COL.white); });
  withA(EO(t, 10.1, .3), () => txt('3 NAVES INDUSTRIALES', 320, iy + 62, { size: 46, ls: 2 }));
  withA(EO(t, 10.9, .3), () => txt('+', 620, iy - 30, { size: 90, c: COL.red2 }));
  { const p = EB(t, 11.08, .35); if (P(t, 11.08, .01) > 0) buildingIcon(830, iy, 120 * p, COL.white); }
  withA(EO(t, 11.2, .3), () => txt('1 EDIFICIO', 830, iy + 62, { size: 46, ls: 2 }));
  withA(EO(t, 12.2, .3), () => txt('VIVIENDA DE TRABAJADORES', 830, iy + 102, { size: 26, fam: 'Inter', w: 700, c: COL.gray }));
}

// ---------- ESCENA 2b: clausura ----------
function s2b(t) {
  background(t);
  photoCard(IMG.fabrica_aerea, 60, 430, 960, 900, t, 12.6, { dur: 6, img2: IMG.fabrica, t2: 15.0, fy2: .6 });
  // fecha
  const cp = EB(t, 14.1, .4);
  if (P(t, 14.1, .01) > 0) withA(P(t, 14.1, .12), () => calendar(200, 1480, .62 * lerp(.6, 1, cp), 1, 'NOV'));
  withA(EO(t, 15.5, .4), () => {
    txt('EL GOBIERNO', 350, 1440, { size: 64, align: 'left', ls: 2 });
    txt('DOMINICANO LA CIERRA', 350, 1510, { size: 64, align: 'left', ls: 2, c: COL.red2 });
  });
  // sello
  const T = 17.04;
  if (t >= T) {
    const p = P(t, T, .16); const s = lerp(2.4, 1, ei(p)) * (1 + .03 * Math.exp(-(t - T) * 10) * Math.sin((t - T) * 50));
    withA(clamp(p * 2), () => { X.save(); X.translate(540, 880); X.rotate(-.18); X.scale(s * .95, s * .95); X.drawImage(OFF.stamp, -450, -210); X.restore(); });
  }
}

// ---------- ESCENA 3: expediente ----------
const FALTAS = [['Sin permiso de uso de suelo', 20.84], ['Normas de construcción', 22.78], ['Almacenamiento de combustibles', 24.4], ['Extranjeros contratados irregularmente', 26.1]];
function s3(t) {
  background(t, 'carton_linea', 1);
  headline('¿POR QUÉ?', 520, t, 18.0, { size: 150 });
  const p = EO(t, 18.4, .5);
  withA(p, () => {
    X.save(); X.translate(0, (1 - p) * 120);
    const x = 70, y = 610, w = 940, h = 900;
    // pestaña
    rr(x, y - 50, 420, 90, 14); X.fillStyle = '#e2d9c3'; X.fill();
    txt('EXPEDIENTE · CARTESA', x + 30, y - 2, { size: 40, align: 'left', c: COL.ink, ls: 3 });
    X.shadowColor = 'rgba(0,0,0,.5)'; X.shadowBlur = 40; rr(x, y, w, h, 18); X.fillStyle = COL.paper; X.fill(); X.shadowColor = 'transparent';
    X.fillStyle = COL.red; X.fillRect(x, y, 14, h);
    txt('FALTAS SEÑALADAS', x + 60, y + 80, { size: 34, fam: 'Inter', w: 900, align: 'left', c: COL.red, ls: 3 });
    X.fillStyle = 'rgba(13,27,61,.2)'; X.fillRect(x + 60, y + 104, w - 120, 3);
    FALTAS.forEach(([s, tt], i) => {
      const ry = y + 210 + i * 175;
      const q = P(t, tt, .5);
      X.fillStyle = 'rgba(13,27,61,.12)'; X.fillRect(x + 60, ry + 70, w - 120, 2);
      xMark(x + 115, ry, 46, q);
      const lines = wrap(s, 46, 'Inter', 800, 690);
      withA(EO(t, tt + .1, .35), () => lines.forEach((l, j) => txt(l, x + 190 + (1 - EO(t, tt + .1, .35)) * 40, ry + 16 - (lines.length - 1) * 27 + j * 54, { size: 46, fam: 'Inter', w: 800, align: 'left', c: COL.ink })));
    });
    X.restore();
  });
  sourceTag('Ministerio de Industria y Comercio', t, 19.0, 1620);
}

// ---------- ESCENA 4: EE. UU. ----------
function s4(t) {
  background(t);
  if (t < 32.3) {
    // calendario 1 → 9 NOV
    const p = EB(t, 28.9, .45);
    const day = Math.round(lerp(1, 9, eio(P(t, 29.0, 1.1))));
    withA(P(t, 28.9, .15), () => calendar(540, 820, 1.35 * lerp(.6, 1, p), day, 'NOVIEMBRE'));
    const k = Math.round(lerp(0, 8, eio(P(t, 29.0, 1.1))));
    withA(EO(t, 29.0, .3), () => txt('+' + k + ' DÍAS', 540, 1180, { size: 120, c: COL.red2, ls: 4 }));
    withA(EO(t, 30.6, .35), () => {
      const y = 1380; const s = 'WASHINGTON REACCIONA'; const w = tw(s, 80, 'Bebas', 400, 3);
      X.save(); X.translate(0, (1 - EO(t, 30.6, .35)) * 40);
      X.drawImage(OFF.us, 540 - w / 2 - 20 - 120, y - 70, 110, 69);
      txt(s, 540 + 20 - 65, y, { size: 80, ls: 3 }); X.restore();
    });
    return;
  }
  photoCard(IMG.segura, 60, 420, 960, 780, t, 32.3, { fy: .28, z0: 1.05, z1: 1.15, dur: 10 });
  lowerThird('JUAN PABLO SEGURA', 'Subsecretario de Estado de EE. UU.', 60, 1030, t, 32.5);
  // tarjeta de publicación
  const T = 36.34, p = EO(t, T, .45);
  if (p <= 0) return;
  withA(p, () => {
    X.save(); X.translate(0, (1 - p) * 200);
    const x = 60, y = 1240, w = 960, h = 400;
    X.shadowColor = 'rgba(0,0,0,.6)'; X.shadowBlur = 40; rr(x, y, w, h, 26); X.fillStyle = '#0d1117'; X.fill(); X.shadowColor = 'transparent';
    X.strokeStyle = 'rgba(255,255,255,.18)'; X.lineWidth = 2; X.stroke();
    X.save(); X.beginPath(); X.arc(x + 80, y + 76, 44, 0, 7); X.clip(); cover(IMG.segura, x + 36, y + 32, 88, 88, 2.1, .5, .22); X.restore();
    txt('Juan Pablo Segura', x + 145, y + 70, { size: 38, fam: 'Inter', w: 800, align: 'left' });
    txt('Publicación en X  ·  9 NOV', x + 145, y + 112, { size: 28, fam: 'Inter', w: 600, align: 'left', c: '#8b98a5' });
    // comillas
    txt('“', x + w - 70, y + 120, { size: 160, c: COL.red2, fam: 'Bebas' });
    const quote = 'Felicitamos a las autoridades... por cerrar una enorme fábrica ilegal operada por chinos.';
    const lines = wrap(quote, 42, 'Inter', 700, 840);
    const words = quote.split(' ').length; const shown = Math.ceil(lerp(0, words, P(t, T + .2, 41.6 - T - .2)));
    let cnt = 0;
    lines.forEach((l, j) => { const lw = l.split(' '); const vis = lw.slice(0, Math.max(0, shown - cnt)).join(' '); cnt += lw.length;
      if (vis) txt(vis, x + 50, y + 200 + j * 58, { size: 42, fam: 'Inter', w: 700, align: 'left', c: COL.white }); });
    X.restore();
  });
}

// ---------- ESCENA 5: China ----------
function s5(t) {
  background(t);
  photoCard(IMG.embajada_china, 60, 420, 960, 700, t, 42.4, { fy: .4, dur: 14, img2: IMG.embajador_china, t2: 49.1, fx2: .62 });
  lowerThird('EMBAJADA DE CHINA EN RD', 'Comunicado oficial', 60, 950, t, 42.7);
  const T = 45.24, p = EO(t, T, .45);
  if (p > 0) withA(p, () => {
    X.save(); X.translate(0, (1 - p) * 200);
    const x = 60, y = 1160, w = 960, h = 470;
    X.shadowColor = 'rgba(0,0,0,.6)'; X.shadowBlur = 40; rr(x, y, w, h, 20); X.fillStyle = COL.paper; X.fill(); X.shadowColor = 'transparent';
    X.save(); rr(x, y, w, h, 20); X.clip(); X.fillStyle = COL.ink; X.fillRect(x, y, w, 74); X.restore();
    txt('COMUNICADO OFICIAL', x + 40, y + 54, { size: 48, align: 'left', ls: 4 });
    // cita 1
    const q1 = EO(t, 47.6, .4);
    if (q1 > 0) {
      const s = '“SEMBRAR DISCORDIA”'; const sw = tw(s, 96, 'Bebas', 400, 3);
      X.fillStyle = 'rgba(215,38,61,.18)'; X.fillRect(x + 40, y + 108, (sw + 30) * q1, 100);
      txt(s, x + 55, y + 192, { size: 96, align: 'left', c: COL.red, ls: 3, a: q1 });
    } else { X.fillStyle = 'rgba(13,27,61,.15)'; for (let i = 0; i < 2; i++) X.fillRect(x + 40, y + 120 + i * 40, 820 - i * 200, 18); }
    // cita 2
    const q2 = EO(t, 53.9, .5);
    const l2 = ['“...felicitaciones con aires', 'de superioridad”'];
    if (q2 > 0) {
      l2.forEach((l, j) => { const lw = tw(l, 52, 'Inter', 900); X.fillStyle = 'rgba(255,216,77,.7)'; X.fillRect(x + 40, y + 250 + j * 68, (lw + 30) * clamp(q2 * 2 - j), 58); });
      l2.forEach((l, j) => txt(l, x + 55, y + 296 + j * 68, { size: 52, fam: 'Inter', w: 900, align: 'left', c: COL.ink }));
    } else { X.fillStyle = 'rgba(13,27,61,.15)'; for (let i = 0; i < 3; i++) X.fillRect(x + 40, y + 250 + i * 40, 860 - i * 150, 18); }
    X.fillStyle = 'rgba(13,27,61,.2)'; X.fillRect(x + 40, y + 400, w - 80, 2);
    txt('FUENTE: EMBAJADA DE CHINA EN RD', x + 40, y + 446, { size: 28, fam: 'Inter', w: 800, align: 'left', c: COL.ink, ls: 1 });
    X.restore();
  });
}

// ---------- ESCENA 6: 24 empresas + 80/20 ----------
function s6(t) {
  background(t, 'carton_almacen', 1);
  const SW = 65.0;
  const outA = 1 - EO(t, SW - .1, .3);
  if (outA > 0) withA(outA, () => {
    headline('NO ES UN CASO AISLADO', 510, t, 57.04, { size: 104 });
    chip('MINISTERIO DE TRABAJO', 540, 640, t, 58.68, { size: 34 });
    const n = Math.round(lerp(0, 24, eo(P(t, 60.82, .9))));
    if (t >= 60.7) withA(P(t, 60.7, .15), () => {
      const pop = 1 + .08 * Math.exp(-(t - 61.72) * 8) * (t > 61.72 ? 1 : 0);
      scaleAt(540, 880, pop, () => txt(String(n), 540, 1000, { size: 360, c: COL.white, shadow: 30 }));
    });
    withA(EO(t, 61.4, .35), () => {
      const s = 'EMPRESAS SUSPENDIDAS'; const w = tw(s, 84, 'Bebas', 400, 3);
      X.fillStyle = COL.red; X.fillRect(540 - w / 2 - 30, 1030, w + 60, 100); txt(s, 540, 1110, { size: 84, ls: 3 });
    });
    // cuadrícula de 24 edificios
    for (let i = 0; i < 24; i++) {
      const col = i % 8, row = Math.floor(i / 8); const x = 155 + col * 110, y = 1290 + row * 110;
      const on = n > i; const a = EO(t, 60.82 + i * .035, .2);
      withA(.25 + .75 * a, () => factoryIcon(x, y, 80, on ? COL.red2 : 'rgba(255,255,255,.35)'));
    }
    withA(EO(t, 62.5, .35), () => { warnIcon(150, 1555, 64); txt('Por poner en peligro a sus empleados', 205, 1572, { size: 40, fam: 'Inter', w: 800, align: 'left' }); });
  });
  if (t >= SW) {
    const a = EO(t, SW, .35);
    withA(a, () => {
      headline('LO QUE EXIGE LA LEY', 520, t, 65.1, { size: 110 });
      const cx = 540, cy = 930, r = 270, th = 96;
      const d = eio(P(t, 65.3, 1.4));
      X.lineWidth = th; X.lineCap = 'butt';
      X.beginPath(); X.arc(cx, cy, r, 0, 7); X.strokeStyle = 'rgba(255,255,255,.08)'; X.stroke();
      const a0 = -Math.PI / 2, a80 = a0 + Math.PI * 2 * .8 * d;
      X.beginPath(); X.arc(cx, cy, r, a0, a80); X.strokeStyle = COL.blue; X.stroke();
      const d2 = eio(P(t, 66.4, .8));
      if (d2 > 0) { X.beginPath(); X.arc(cx, cy, r, a0 + Math.PI * 1.6, a0 + Math.PI * 1.6 + Math.PI * .4 * d2); X.strokeStyle = COL.red; X.stroke(); }
      // separadores
      X.strokeStyle = COL.n1; X.lineWidth = 8;
      for (const ang of [a0, a0 + Math.PI * 1.6]) if (d > .99 || ang === a0) { X.beginPath(); X.moveTo(cx + Math.cos(ang) * (r - th / 2), cy + Math.sin(ang) * (r - th / 2)); X.lineTo(cx + Math.cos(ang) * (r + th / 2), cy + Math.sin(ang) * (r + th / 2)); X.stroke(); }
      const pct = Math.round(lerp(0, 80, eo(P(t, 65.4, 1.5))));
      txt(pct + '%', cx, cy + 50, { size: 200 });
      txt('DOMINICANOS', cx, cy + 105, { size: 34, fam: 'Inter', w: 900, ls: 4, c: COL.lblue });
      if (d2 > .6) withA((d2 - .6) / .4, () => { const ang = a0 + Math.PI * 1.8; txt('20%', cx + Math.cos(ang) * (r + 115), cy + Math.sin(ang) * (r + 115) + 30, { size: 90, c: COL.red2, shadow: 10 }); });
      // leyenda
      withA(EO(t, 67.6, .4), () => {
        const y = 1330;
        X.fillStyle = COL.blue; X.fillRect(150, y - 36, 44, 44); txt('Mínimo 80% trabajadores dominicanos', 215, y, { size: 40, fam: 'Inter', w: 800, align: 'left' });
        X.fillStyle = COL.red; X.fillRect(150, y + 44, 44, 44); txt('Máximo 20% extranjeros', 215, y + 80, { size: 40, fam: 'Inter', w: 800, align: 'left' });
      });
    });
  }
  sourceTag('Ministerio de Trabajo', t, 59.2, 1690);
}

// ---------- ESCENA 7: gobierno dominicano ----------
function door(cx, by, p, t) {
  const dw = 190, dh = 320, x = cx - dw / 2, y = by - dh;
  // luz
  if (p > 0) { const g = X.createLinearGradient(x, 0, x + dw + 200, 0); g.addColorStop(0, `rgba(255,236,170,${.55 * p})`); g.addColorStop(1, 'rgba(255,236,170,0)');
    X.fillStyle = g; X.beginPath(); X.moveTo(x, y); X.lineTo(x + dw, y); X.lineTo(x + dw + 220 * p, by + 40); X.lineTo(x - 40 * p, by + 40); X.closePath(); X.fill();
    X.fillStyle = `rgba(255,240,190,${.9 * p})`; X.fillRect(x, y, dw, dh); }
  else { X.fillStyle = '#0a1430'; X.fillRect(x, y, dw, dh); }
  // marco
  X.strokeStyle = COL.white; X.lineWidth = 12; X.strokeRect(x - 6, y - 6, dw + 12, dh + 6);
  // hoja de la puerta
  const ow = dw * (1 - .78 * p);
  X.fillStyle = COL.n3; X.beginPath(); X.moveTo(x, y); X.lineTo(x + ow, y + 26 * p); X.lineTo(x + ow, by - 26 * p); X.lineTo(x, by); X.closePath(); X.fill();
  X.strokeStyle = COL.lblue; X.lineWidth = 4; X.stroke();
  X.beginPath(); X.arc(x + ow - 22 * (1 - .6 * p), y + dh / 2, 9, 0, 7); X.fillStyle = COL.gold; X.fill();
}
function s7(t) {
  background(t);
  photoCard(IMG.sanz_lovaton, 60, 420, 960, 720, t, 70.4, { fx: .42, fy: .3, dur: 8 });
  lowerThird('EDUARDO SANZ LOVATÓN', 'Ministro de Industria y Comercio', 60, 970, t, 70.6);
  const ap = EO(t, 72.6, .4);
  withA(ap, () => {
    const by = 1600;
    door(250, by, EO(t, 74.3, .7), t);
    txt('INVERSIÓN EXTRANJERA', 420, 1330, { size: 36, fam: 'Inter', w: 900, align: 'left', c: COL.gray, ls: 2 });
    withA(EO(t, 74.34, .3), () => txt('BIENVENIDA...', 420, 1430, { size: 104, align: 'left', ls: 3 }));
    withA(EO(t, 76.1, .3), () => txt('SI CUMPLE LA LEY', 420, 1525, { size: 84, align: 'left', ls: 3, c: COL.red2 }));
    // candado LEY
    if (t >= 76.0) {
      const d = t - 76.0; const yy = lerp(1120, 1420, eback(clamp(d / .3))); const sw = Math.sin(d * 9) * .25 * Math.exp(-d * 3);
      X.save(); X.translate(250, 1250); X.rotate(sw);
      X.strokeStyle = '#cfd6e6'; X.lineWidth = 5; X.beginPath(); X.moveTo(0, 0); X.lineTo(0, yy - 1250 - 60); X.stroke();
      padlock(0, yy - 1250, 110, 'LEY'); X.restore();
    }
  });
}

// ---------- ESCENA 8: tira y jala + encuesta ----------
function rope(x0, y0, x1, y1, sag, t) {
  const mx = (x0 + x1) / 2, my = (y0 + y1) / 2 + sag;
  X.save(); X.lineCap = 'round';
  X.beginPath(); X.moveTo(x0, y0); X.quadraticCurveTo(mx, my, x1, y1); X.strokeStyle = '#8a6a3c'; X.lineWidth = 16; X.stroke();
  X.setLineDash([10, 10]); X.lineDashOffset = t * 20; X.strokeStyle = '#c9a46a'; X.lineWidth = 9; X.stroke(); X.setLineDash([]);
  X.restore();
}
function s8(t) {
  background(t);
  const T0 = 77.3;
  const tug = Math.sin((t - T0) * 2.4), tug2 = Math.sin((t - T0) * 1.9 + 1.3);
  // EE. UU. arriba
  const up = EO(t, T0, .6);
  const usB = [[200, 420 - (1 - up) * 300], [880, 660 - (1 - up) * 300]];
  const pUS = d3.geoAlbers().fitExtent([[usB[0][0], usB[0][1] - tug * 8], [usB[1][0], usB[1][1] - tug * 8]], F.us);
  X.beginPath(); d3.geoPath(pUS, X)(F.us); X.fillStyle = '#1c3466'; X.fill(); X.strokeStyle = COL.lblue; X.lineWidth = 2.5; X.stroke();
  withA(up, () => txt('EE. UU.', 540, 560 - tug * 8, { size: 90, ls: 4, shadow: 16 }));
  // China derecha
  const cp = EO(t, T0 + .15, .6);
  const off = (1 - cp) * 400 + tug2 * 8;
  const pCN = d3.geoMercator().fitExtent([[760 + off, 790], [1240 + off, 1150]], F.cn);
  X.beginPath(); d3.geoPath(pCN, X)(F.cn); X.fillStyle = '#4a1724'; X.fill(); X.strokeStyle = '#ff8a98'; X.lineWidth = 2.5; X.stroke();
  withA(cp, () => txt('CHINA', 960 + off, 990, { size: 90, ls: 4, shadow: 16 }));
  // RD centro
  const rp = EB(t, T0 + .1, .5);
  const dx = tug2 * 10, dy = -tug * 10;
  const rb = [[230 + dx, 860 + dy], [700 + dx, 1110 + dy]];
  const pDR = d3.geoMercator().fitExtent(rb, F.dr);
  // cuerdas
  const rpp = EO(t, T0 + .4, .6);
  if (rpp > 0) {
    const a = [470 + dx, 900 + dy], b = [540, 660 - tug * 8];
    rope(a[0], a[1], lerp(a[0], b[0], rpp), lerp(a[1], b[1], rpp), 30 * (1 - Math.abs(tug)), t);
    const c = [670 + dx, 990 + dy], d = [850 + off, 990];
    rope(c[0], c[1], lerp(c[0], d[0], rpp), lerp(c[1], d[1], rpp), 20 * (1 - Math.abs(tug2)), t);
  }
  scaleAt(465, 985, lerp(.3, 1, rp), () => {
    X.beginPath(); d3.geoPath(pDR, X)(F.dr); X.fillStyle = COL.white; X.fill(); X.strokeStyle = COL.red; X.lineWidth = 4; X.stroke();
    txt('RD', 500 + dx, 1010 + dy, { size: 84, c: COL.ink, ls: 3 });
  });
  // marcas de tensión
  withA(.6 * rpp, () => { X.strokeStyle = COL.gold; X.lineWidth = 5; X.lineCap = 'round';
    for (const [x, y, a] of [[300 + dx, 860 + dy, -2.4], [250 + dx, 900 + dy, -2.8], [690 + dx, 1100 + dy, .8]]) { const L = 30 + 10 * Math.abs(tug); X.beginPath(); X.moveTo(x, y); X.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); X.stroke(); } });
  // encuesta
  const qp = EO(t, 78.94, .45);
  if (qp > 0) withA(qp, () => {
    X.save(); X.translate(0, (1 - qp) * 160);
    const x = 60, y = 1190, w = 960, h = 460;
    X.shadowColor = 'rgba(0,0,0,.6)'; X.shadowBlur = 40; rr(x, y, w, h, 26); X.fillStyle = 'rgba(8,18,44,.95)'; X.fill(); X.shadowColor = 'transparent';
    X.strokeStyle = 'rgba(255,255,255,.2)'; X.lineWidth = 2; X.stroke(); X.fillStyle = COL.red; X.fillRect(x + 40, y, 160, 8);
    chip('ENCUESTA', x + 40, y + 70, t, 79.0, { size: 28, align: 'left' });
    txt('¿RD EN MEDIO DE UNA PELEA', 540, y + 170, { size: 78, ls: 2 });
    txt('ENTRE POTENCIAS?', 540, y + 248, { size: 78, ls: 2, c: COL.red2 });
    const op = (lab, cx, col, tt) => { const p = EB(t, tt, .4); if (P(t, tt, .01) <= 0) return; scaleAt(cx, y + 360, lerp(.4, 1, p), () => {
      rr(cx - 200, y + 290, 400, 130, 22); X.fillStyle = col; X.fill(); txt(lab, cx, y + 392, { size: 110, ls: 4 }); }); };
    op('1 = SÍ', 300, COL.blue, 83.94); op('2 = NO', 780, COL.red, 85.04);
    X.restore();
  });
  withA(EO(t, 83.5, .3), () => txt('COMENTA TU RESPUESTA ↓', 540, 1735, { size: 60, ls: 3, shadow: 10 }));
}

// ---------- CIERRE: lupa Capital Curioso ----------
function close(t) {
  const g = X.createRadialGradient(540, 860, 50, 540, 900, 1200); g.addColorStop(0, COL.n2); g.addColorStop(1, COL.n0);
  X.fillStyle = g; X.fillRect(0, 0, W, H);
  const T = 86.0, cx = 520, cy = 820, r = 180;
  lupa(cx, cy, r, eio(P(t, T + .1, .6)), eo(P(t, T + .55, .3)));
  if (t >= T + .2) withA(P(t, T + .2, .4) * .25, () => { X.beginPath(); X.arc(cx, cy, r - 18, 0, 7); X.fillStyle = COL.lblue; X.fill(); });
  const qp = EB(t, T + .85, .45);
  if (P(t, T + .85, .01) > 0) scaleAt(cx, cy, lerp(.2, 1, qp), () => txt('?', cx, cy + 92, { size: 280, c: COL.red2 }));
  // brillo
  withA(P(t, T + 1.2, .3) * .6, () => { X.strokeStyle = '#fff'; X.lineWidth = 12; X.lineCap = 'round'; X.beginPath(); X.arc(cx, cy, r - 50, -2.6, -1.9); X.stroke(); });
  const s = 'CAPITAL CURIOSO'; const lp = P(t, T + 1.1, .7);
  const n = Math.floor(s.length * lp);
  txt(s.slice(0, n), 540, 1220, { size: 140, ls: 6 });
  X.fillStyle = COL.red; X.fillRect(540 - 300 * EO(t, T + 1.6, .4), 1250, 600 * EO(t, T + 1.6, .4), 10);
  withA(EO(t, T + 1.8, .4), () => txt('@capitalcuriosoo', 540, 1340, { size: 52, fam: 'Inter', w: 800 }));
  withA(EO(t, T + 2.3, .4), () => { const w = tw('SÍGUENOS PARA MÁS', 50, 'Bebas', 400, 4) + 70; rr(540 - w / 2, 1400, w, 80, 40); X.fillStyle = COL.red; X.fill(); txt('SÍGUENOS PARA MÁS', 540, 1458, { size: 50, ls: 4 }); });
}

// ---------- línea de tiempo ----------
const SCENES = [[0, 5.56, s1], [5.56, 12.6, s2], [12.6, 17.95, s2b], [17.95, 28.9, s3], [28.9, 42.4, s4], [42.4, 57.0, s5], [57.0, 70.4, s6], [70.4, 77.3, s7], [77.3, 86.0, s8], [86.0, 99, close]];
const IMPACTS = [[3.62, 16], [17.04, 18], [42.44, 10], [61.72, 8], [76.25, 8]];
const TOTAL = 90.6;
function wipe(t) {
  for (const b of [5.56, 12.6, 17.95, 28.9, 32.3, 42.4, 57.0, 70.4, 77.3, 86.0]) {
    const p = (t - (b - .22)) / .44; if (p < 0 || p > 1) continue;
    const x = lerp(-1900, 1300, eio(p));
    X.save(); X.translate(x, 0);
    X.beginPath(); X.moveTo(0, 0); X.lineTo(1500, 0); X.lineTo(1200, H); X.lineTo(-300, H); X.closePath(); X.fillStyle = COL.n1; X.fill();
    X.beginPath(); X.moveTo(1500, 0); X.lineTo(1570, 0); X.lineTo(1270, H); X.lineTo(1200, H); X.closePath(); X.fillStyle = COL.red; X.fill();
    X.restore();
  }
}
window.renderFrame = function (t) {
  X.save();
  let sx = 0, sy = 0;
  for (const [ti, a] of IMPACTS) if (t >= ti && t < ti + .45) { const d = t - ti; const k = a * Math.exp(-d * 9); sx += Math.sin(d * 90) * k; sy += Math.cos(d * 77) * k; }
  X.setTransform(1, 0, 0, 1, 0, 0);
  X.fillStyle = '#000'; X.fillRect(0, 0, W, H);
  X.translate(sx, sy);
  if (sx || sy) { X.translate(540, 960); X.scale(1.02, 1.02); X.translate(-540, -960); }
  const sc = SCENES.find(s => t >= s[0] && t < s[1]) || SCENES[SCENES.length - 1];
  sc[2](t);
  X.restore();
  // destello del choque
  if (t >= 3.62 && t < 3.85) withA((1 - (t - 3.62) / .23) * .55, () => { X.fillStyle = '#fff'; X.fillRect(0, 0, W, H); });
  brand(t);
  subtitles(t);
  wipe(t);
  finishFX(t);
  if (t > TOTAL - .5) withA(P(t, TOTAL - .5, .5), () => { X.fillStyle = '#000'; X.fillRect(0, 0, W, H); });
};
init();
