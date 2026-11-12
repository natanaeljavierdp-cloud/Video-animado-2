// ============================================================
//  "¿República Dominicana nuclear?" — Capital Curioso
//  Motor de animación: render(t) dibuja el fotograma en t (s).
// ============================================================
const W = 1080, H = 1920;
const cv = document.getElementById('c');
// (las funciones de dibujo usan la variable global ctx; withCtx() la cambia temporalmente)
let ctx = cv.getContext('2d');

// ---------- Paleta ----------
const NAVY = '#0A1F44', NAVY_D = '#050E22', NAVY_L = '#1C3F7A';
const RED = '#CE1126', RED_L = '#FF3B4E', WHITE = '#FFFFFF', ICE = '#C9D8F2';
const F = (w, s) => `${w} ${s}px Inter, "Inter Display", sans-serif`;
const SERIF = s => `italic 600 ${s}px "Liberation Serif", FreeSerif, serif`;

// ---------- Utilidades ----------
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const A = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const eOut = k => 1 - Math.pow(1 - k, 3);
const eIn = k => k * k * k;
const eIO = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const eBack = k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const eElastic = k => k === 0 ? 0 : k === 1 ? 1 : Math.pow(2, -10 * k) * Math.sin((k * 10 - .75) * (2 * Math.PI / 3)) + 1;
// envolvente: entra en [a,a+fi], sale en [b-fo,b]
const env = (t, a, b, fi = .35, fo = .3) => Math.min(eOut(A(t, a, a + fi)), 1 - eIn(A(t, b - fo, b)));
function hash(n) { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); }
function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function fmt(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

// ---------- Imágenes ----------
const IMG = {};
const IMG_LIST = ['apagon_calle', 'apagon_trafico', 'apagon_familia', 'apagon_vela', 'torre', 'torres',
  'palacio', 'washington', 'medicina1', 'medicina2', 'moscu', 'planta1', 'planta2'];
function loadAll() {
  return Promise.all(IMG_LIST.map(n => new Promise((res, rej) => {
    const im = new Image(); im.onload = () => { IMG[n] = im; res(); }; im.onerror = rej; im.src = `assets/${n}.jpg`;
  })));
}

// Clips de fondo (Ken Burns). u,v = punto focal normalizado; z = zoom.
const FADE = .35;
const CLIPS = [
  { n: 'apagon_calle',   t0: 0.00, t1: 3.00, z: [1.05, 1.20], u: [.45, .50], v: [.55, .55], br: t => t < 2.62 ? 1.35 : t < 2.95 ? (hash(Math.floor(t * 30)) > .45 ? 1.35 : .15) : .32 },
  { n: 'apagon_trafico', t0: 3.00, t1: 5.20, z: [1.10, 1.22], u: [.40, .48], v: [.55, .5], br: () => .6 },
  { n: 'apagon_familia', t0: 5.20, t1: 7.30, z: [1.08, 1.20], u: [.50, .48], v: [.45, .45], br: () => .78 },
  { n: 'torre',          t0: 7.30, t1: 9.20, z: [1.04, 1.16], u: [.5, .5], v: [.45, .40], br: () => .75 },
  { n: 'torres',         t0: 9.20, t1: 10.35, z: [1.10, 1.22], u: [.55, .58], v: [.6, .6], br: t => t < 9.25 ? .9 : t < 9.62 ? (hash(Math.floor(t * 30) + 7) > .5 ? 1 : .1) : .35 },
  { n: 'apagon_vela',    t0: 10.35, t1: 12.70, z: [1.05, 1.18], u: [.47, .50], v: [.55, .55], br: () => .95 },
  { n: 'palacio',        t0: 12.70, t1: 18.00, z: [1.02, 1.14], u: [.48, .48], v: [.45, .42], br: () => .8 },
  { n: 'washington',     t0: 18.00, t1: 24.10, z: [1.00, 1.12], u: [.42, .50], v: [.42, .40], br: () => .75 },
  { n: 'medicina1',      t0: 24.10, t1: 26.40, z: [1.06, 1.16], u: [.40, .38], v: [.45, .45], br: () => .8 },
  { n: 'medicina2',      t0: 26.40, t1: 28.15, z: [1.06, 1.16], u: [.45, .50], v: [.5, .5], br: () => .8 },
  { n: 'moscu',          t0: 28.15, t1: 37.60, z: [1.00, 1.16], u: [.5, .5], v: [.55, .30], br: () => .7 },
  { n: 'planta1',        t0: 41.20, t1: 49.25, z: [1.02, 1.18], u: [.50, .48], v: [.45, .48], br: () => .78 },
  { n: 'planta2',        t0: 49.25, t1: 54.90, z: [1.04, 1.16], u: [.52, .55], v: [.45, .45], br: () => .72 },
  { n: 'planta1',        t0: 54.90, t1: 62.95, z: [1.25, 1.40], u: [.55, .55], v: [.4, .4], br: () => .32, blur: 10 },
];

function drawCover(im, zoom, u, v, filter) {
  const s = Math.max(W / im.width, H / im.height) * zoom;
  const dw = im.width * s, dh = im.height * s;
  let x = W / 2 - u * dw, y = H / 2 - v * dh;
  x = Math.min(0, Math.max(W - dw, x)); y = Math.min(0, Math.max(H - dh, y));
  ctx.filter = filter || 'none';
  ctx.drawImage(im, x, y, dw, dh);
  ctx.filter = 'none';
}

function drawBackground(t) {
  for (let i = 0; i < CLIPS.length; i++) {
    const c = CLIPS[i];
    const end = c.t1 + FADE;
    if (t < c.t0 || t > end) continue;
    const k = A(t, c.t0, c.t1);
    const alphaIn = i === 0 ? 1 : eOut(A(t, c.t0, c.t0 + FADE));
    const punch = 1 + .07 * (1 - eOut(A(t, c.t0, c.t0 + .6)));
    const z = lerp(c.z[0], c.z[1], eIO(k)) * punch;
    const b = c.br(t);
    ctx.globalAlpha = alphaIn;
    drawCover(IMG[c.n], z, lerp(c.u[0], c.u[1], eIO(k)), lerp(c.v[0], c.v[1], eIO(k)),
      `brightness(${b}) contrast(1.12) saturate(.85)${c.blur ? ` blur(${c.blur}px)` : ''}`);
    ctx.globalAlpha = 1;
  }
}

// Gradación de color + viñeta + grano
let GRAIN;
function makeGrain() {
  GRAIN = document.createElement('canvas'); GRAIN.width = 512; GRAIN.height = 512;
  const g = GRAIN.getContext('2d'), d = g.createImageData(512, 512);
  for (let i = 0; i < d.data.length; i += 4) { const v = Math.random() * 255; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = 13; }
  g.putImageData(d, 0, 0);
}
function grade(t) {
  // tinte azul marino
  ctx.globalCompositeOperation = 'soft-light';
  ctx.fillStyle = 'rgba(20,50,120,.55)'; ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = 'source-over';
  // degradado superior para subtítulos
  let g = ctx.createLinearGradient(0, 0, 0, 640);
  g.addColorStop(0, 'rgba(5,14,34,.88)'); g.addColorStop(.6, 'rgba(5,14,34,.35)'); g.addColorStop(1, 'rgba(5,14,34,0)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, 640);
  g = ctx.createLinearGradient(0, H - 700, 0, H);
  g.addColorStop(0, 'rgba(5,14,34,0)'); g.addColorStop(1, 'rgba(5,14,34,.9)');
  ctx.fillStyle = g; ctx.fillRect(0, H - 700, W, 700);
  // viñeta
  g = ctx.createRadialGradient(W / 2, H * .52, H * .22, W / 2, H * .52, H * .78);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.78)');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}
function grain(t) {
  const f = Math.floor(t * 30);
  ctx.save(); ctx.globalCompositeOperation = 'overlay';
  const ox = -Math.floor(hash(f) * 512), oy = -Math.floor(hash(f + 3) * 512);
  for (let x = ox; x < W; x += 512) for (let y = oy; y < H; y += 512) ctx.drawImage(GRAIN, x, y);
  ctx.restore();
}

// ---------- Texto ----------
function text(str, x, y, { font = F(800, 60), color = WHITE, align = 'center', base = 'middle', ls = 0, shadow = true, alpha = 1, stroke = null, sw = 0 } = {}) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.font = font; ctx.textAlign = align; ctx.textBaseline = base; ctx.letterSpacing = ls + 'px';
  if (shadow) { ctx.shadowColor = 'rgba(0,0,0,.65)'; ctx.shadowBlur = 24; ctx.shadowOffsetY = 6; }
  if (stroke) { ctx.lineJoin = 'round'; ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.strokeText(str, x, y); ctx.shadowColor = 'transparent'; }
  ctx.fillStyle = color; ctx.fillText(str, x, y);
  ctx.restore();
}
function measure(str, font, ls = 0) { ctx.save(); ctx.font = font; ctx.letterSpacing = ls + 'px'; const w = ctx.measureText(str).width; ctx.restore(); return w; }

// Etiqueta tipo "pill"
function pill(str, cx, cy, { font = F(800, 40), bg = RED, fg = WHITE, padX = 28, h = 72, alpha = 1, ls = 3, scale = 1 } = {}) {
  const w = measure(str, font, ls) + padX * 2;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(cx, cy); ctx.scale(scale, scale);
  ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; ctx.shadowOffsetY = 8;
  rr(-w / 2, -h / 2, w, h, 12); ctx.fillStyle = bg; ctx.fill();
  ctx.restore();
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(cx, cy); ctx.scale(scale, scale);
  text(str, 0, 2, { font, color: fg, ls, shadow: false });
  ctx.restore();
  return w;
}

// ---------- Íconos ----------
function iconCross(cx, cy, s, col = WHITE) {
  ctx.save(); ctx.translate(cx, cy); ctx.fillStyle = col;
  rr(-s * .17, -s * .5, s * .34, s, s * .07); ctx.fill();
  rr(-s * .5, -s * .17, s, s * .34, s * .07); ctx.fill();
  ctx.restore();
}
function iconBolt(cx, cy, s, col = WHITE) {
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s / 100, s / 100); ctx.fillStyle = col;
  ctx.beginPath(); ctx.moveTo(12, -52); ctx.lineTo(-30, 8); ctx.lineTo(-2, 8); ctx.lineTo(-12, 52); ctx.lineTo(32, -12); ctx.lineTo(4, -12); ctx.closePath(); ctx.fill();
  ctx.restore();
}
function iconAtom(cx, cy, s, t, col = WHITE, nucleus = RED) {
  ctx.save(); ctx.translate(cx, cy);
  ctx.strokeStyle = col; ctx.lineWidth = s * .055; ctx.shadowColor = 'rgba(120,180,255,.8)'; ctx.shadowBlur = 18;
  for (let i = 0; i < 3; i++) {
    ctx.save(); ctx.rotate(i * Math.PI / 3 + t * .4);
    ctx.beginPath(); ctx.ellipse(0, 0, s * .5, s * .19, 0, 0, Math.PI * 2); ctx.stroke();
    const a = t * 3.2 + i * 2.1; ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(Math.cos(a) * s * .5, Math.sin(a) * s * .19, s * .05, 0, 7); ctx.fill();
    ctx.restore();
  }
  ctx.shadowColor = 'rgba(255,40,60,.9)'; ctx.fillStyle = nucleus;
  ctx.beginPath(); ctx.arc(0, 0, s * .1, 0, 7); ctx.fill();
  ctx.restore();
}
function iconDoc(cx, cy, s, k = 1) {
  ctx.save(); ctx.translate(cx, cy);
  const w = s * .74, h = s, f = s * .22;
  ctx.fillStyle = WHITE; ctx.beginPath();
  ctx.moveTo(-w / 2, -h / 2); ctx.lineTo(w / 2 - f, -h / 2); ctx.lineTo(w / 2, -h / 2 + f); ctx.lineTo(w / 2, h / 2); ctx.lineTo(-w / 2, h / 2); ctx.closePath(); ctx.fill();
  ctx.fillStyle = ICE; ctx.beginPath(); ctx.moveTo(w / 2 - f, -h / 2); ctx.lineTo(w / 2 - f, -h / 2 + f); ctx.lineTo(w / 2, -h / 2 + f); ctx.closePath(); ctx.fill();
  ctx.fillStyle = NAVY_L;
  for (let i = 0; i < 5; i++) { const ww = (i === 0 ? .5 : .62) * w * clamp(k * 5 - i); rr(-w * .34, -h * .28 + i * h * .13, ww, h * .05, 3); ctx.fill(); }
  ctx.restore();
}
function iconCheck(cx, cy, s, k = 1, col = '#1DB954') {
  ctx.save(); ctx.translate(cx, cy);
  ctx.fillStyle = col; ctx.beginPath(); ctx.arc(0, 0, s / 2, 0, 7); ctx.fill();
  ctx.strokeStyle = WHITE; ctx.lineWidth = s * .12; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const p = [[-s * .22, 0], [-s * .06, s * .16], [s * .24, -s * .16]];
  ctx.beginPath(); ctx.moveTo(...p[0]);
  const k1 = clamp(k * 2), k2 = clamp(k * 2 - 1);
  ctx.lineTo(lerp(p[0][0], p[1][0], k1), lerp(p[0][1], p[1][1], k1));
  if (k2 > 0) ctx.lineTo(lerp(p[1][0], p[2][0], k2), lerp(p[1][1], p[2][1], k2));
  ctx.stroke(); ctx.restore();
}
function iconEye(cx, cy, s, col = WHITE) {
  ctx.save(); ctx.translate(cx, cy); ctx.strokeStyle = col; ctx.lineWidth = s * .08;
  ctx.beginPath(); ctx.moveTo(-s / 2, 0); ctx.quadraticCurveTo(0, -s * .55, s / 2, 0); ctx.quadraticCurveTo(0, s * .55, -s / 2, 0); ctx.stroke();
  ctx.fillStyle = col; ctx.beginPath(); ctx.arc(0, 0, s * .16, 0, 7); ctx.fill();
  ctx.restore();
}
function iconCalendar(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy);
  rr(-s / 2, -s * .42, s, s * .9, s * .1); ctx.fillStyle = WHITE; ctx.fill();
  rr(-s / 2, -s * .42, s, s * .26, [s * .1, s * .1, 0, 0]); ctx.fillStyle = RED; ctx.fill();
  ctx.fillStyle = NAVY; for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) { rr(-s * .32 + i * s * .24, -s * .02 + j * s * .2, s * .16, s * .13, 2); ctx.fill(); }
  ctx.restore();
}
function iconPin(x, y, s, col) {
  ctx.save(); ctx.translate(x, y); ctx.fillStyle = col; ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 12;
  ctx.beginPath(); ctx.arc(0, -s * .9, s * .5, Math.PI * .85, Math.PI * .15); ctx.lineTo(0, 0); ctx.closePath(); ctx.fill();
  ctx.fillStyle = WHITE; ctx.beginPath(); ctx.arc(0, -s * .9, s * .2, 0, 7); ctx.fill();
  ctx.restore();
}
function iconBubble(cx, cy, s) {
  ctx.save(); ctx.translate(cx, cy); ctx.fillStyle = WHITE;
  rr(-s / 2, -s * .4, s, s * .64, s * .16); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-s * .2, s * .2); ctx.lineTo(-s * .3, s * .45); ctx.lineTo(0, s * .22); ctx.fill();
  ctx.fillStyle = NAVY; for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.arc(i * s * .22, -s * .08, s * .06, 0, 7); ctx.fill(); }
  ctx.restore();
}
function iconMag(cx, cy, s, k = 1, q = 1, col = WHITE, qcol = RED, t = 0) {
  // lupa con "?" — k: progreso trazo, q: progreso del "?"
  ctx.save(); ctx.translate(cx, cy);
  const r = s * .34;
  ctx.lineCap = 'round';
  ctx.strokeStyle = col; ctx.lineWidth = s * .075;
  ctx.beginPath(); ctx.arc(-s * .08, -s * .08, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * clamp(k * 1.4)); ctx.stroke();
  const hk = clamp(k * 3.3 - 2.3);
  if (hk > 0) {
    ctx.lineWidth = s * .12; const a = Math.PI / 4;
    const x0 = -s * .08 + Math.cos(a) * (r + s * .04), y0 = -s * .08 + Math.sin(a) * (r + s * .04);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + s * .26 * hk, y0 + s * .26 * hk); ctx.stroke();
  }
  if (q > 0) {
    ctx.save(); ctx.translate(-s * .08, -s * .06); ctx.scale(eBack(q), eBack(q));
    text('?', 0, 0, { font: F(900, s * .46), color: qcol, shadow: false });
    ctx.restore();
  }
  ctx.restore();
}

// ---------- Banderas ----------
function flagDR(x, y, w, h) {
  const c = h * .17, cw = w * .1;
  ctx.save(); ctx.fillStyle = WHITE; ctx.fillRect(x, y, w, h);
  const qw = (w - cw) / 2, qh = (h - c) / 2;
  ctx.fillStyle = '#002D62'; ctx.fillRect(x, y, qw, qh); ctx.fillRect(x + qw + cw, y + qh + c, qw, qh);
  ctx.fillStyle = RED; ctx.fillRect(x + qw + cw, y, qw, qh); ctx.fillRect(x, y + qh + c, qw, qh);
  // escudo simplificado
  const s = h * .2, ex = x + w / 2, ey = y + h / 2;
  ctx.fillStyle = '#0B6E3A'; ctx.beginPath(); ctx.arc(ex, ey, s * .62, 0, 7); ctx.fill();
  ctx.fillStyle = WHITE; ctx.beginPath(); ctx.arc(ex, ey, s * .42, 0, 7); ctx.fill();
  ctx.fillStyle = '#002D62'; ctx.fillRect(ex - s * .28, ey - s * .3, s * .28, s * .3); ctx.fillStyle = RED; ctx.fillRect(ex, ey - s * .3, s * .28, s * .3);
  ctx.fillStyle = RED; ctx.fillRect(ex - s * .28, ey, s * .28, s * .3); ctx.fillStyle = '#002D62'; ctx.fillRect(ex, ey, s * .28, s * .3);
  ctx.restore();
}
function star(x, y, r) {
  ctx.beginPath();
  for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, rad = i % 2 ? r * .4 : r; ctx.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad); }
  ctx.closePath(); ctx.fill();
}
function flagUS(x, y, w, h) {
  ctx.save(); const sh = h / 13;
  for (let i = 0; i < 13; i++) { ctx.fillStyle = i % 2 ? WHITE : '#B22234'; ctx.fillRect(x, y + i * sh, w, sh + .5); }
  const cw = w * .4, ch = sh * 7; ctx.fillStyle = '#3C3B6E'; ctx.fillRect(x, y, cw, ch);
  ctx.fillStyle = WHITE;
  for (let r = 0; r < 9; r++) { const n = r % 2 ? 5 : 6; for (let c = 0; c < n; c++) { const sx = x + cw * ((c * 2 + (r % 2 ? 2 : 1)) / 12), sy = y + ch * ((r + 1) / 10); star(sx, sy, ch * .045); } }
  ctx.restore();
}
function flagRU(x, y, w, h) {
  ctx.save(); const s = h / 3;
  ctx.fillStyle = WHITE; ctx.fillRect(x, y, w, s + .5); ctx.fillStyle = '#0039A6'; ctx.fillRect(x, y + s, w, s + .5); ctx.fillStyle = '#D52B1E'; ctx.fillRect(x, y + 2 * s, w, s);
  ctx.restore();
}
// bandera ondeando (render a buffer y dibujo en tiras)
const FBUF = {};
function wavingFlag(kind, x, y, w, h, t, amp = 14) {
  const key = kind + w + 'x' + h;
  if (!FBUF[key]) {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    withCtx(c.getContext('2d'), () => (kind === 'us' ? flagUS : kind === 'ru' ? flagRU : flagDR)(0, 0, w, h));
    FBUF[key] = c;
  }
  const buf = FBUF[key], strip = 6;
  for (let sx = 0; sx < w; sx += strip) {
    const ph = sx / w * Math.PI * 2.2 - t * 4.5;
    const dy = Math.sin(ph) * amp;
    ctx.drawImage(buf, sx, 0, strip, h, x + sx, y + dy, strip + 1, h);
    const sh = Math.cos(ph) * .22;
    ctx.fillStyle = sh > 0 ? `rgba(255,255,255,${sh * .5})` : `rgba(0,0,0,${-sh})`;
    ctx.fillRect(x + sx, y + dy, strip + 1, h);
  }
}
function withCtx(g, fn) { const prev = ctx; ctx = g; try { fn(); } finally { ctx = prev; } }
