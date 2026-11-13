// =====================================================================
//  MOTOR "LOS MORENOS CHOCOLATE"  (se ejecuta dentro de Chromium)
//  - Escenario fijo de la serie (cruce, isleta, árbol, locales, casa)
//  - Personajes por piezas a partir de los SVG originales (sin tocar caras)
//  - Utilidades: cámara, subtítulos, motores, sillas, utilería
// =====================================================================
/* global window, document */
const W = 1080, H = 1920;
const CHAR_H = 420;               // alto de un personaje en el mundo
const S = CHAR_H / 780;           // escala viewBox -> mundo
const PX = 2;                     // resolución de las piezas (px por unidad del viewBox)

const M = (window.M = {});
M.W = W; M.H = H; M.S = S;

// ---------------------------------------------------------------- utilidades
M.clamp = (v, a, b) => Math.max(a, Math.min(b, v));
M.lerp = (a, b, k) => a + (b - a) * k;
M.smooth = (k) => { k = M.clamp(k, 0, 1); return k * k * (3 - 2 * k); };
M.ease = (k) => { k = M.clamp(k, 0, 1); return k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2; };
// peso suave dentro de [t0,t1] con rampas de r segundos
M.win = (t, t0, t1, r = 0.25) => M.smooth((t - t0) / r) * M.smooth((t1 - t) / r);
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
M.rng = rng;

// ---------------------------------------------------------------- personajes
const PARTS = ['back', 'armL', 'armR', 'legL', 'legR', 'body', 'head'];

async function svgToCanvas(inner) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${400 * PX}" height="${780 * PX}" viewBox="0 0 400 780">${inner}</svg>`;
  const img = new Image();
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  await img.decode();
  const c = document.createElement('canvas');
  c.width = 400 * PX; c.height = 780 * PX;
  c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
  return c;
}

M.loadCharacter = async function (svgText) {
  const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
  const ser = (el) => (el ? new XMLSerializer().serializeToString(el) : '');
  const pers = doc.getElementById('personaje');
  const back = [...pers.children].filter((k) => !k.id).map(ser).join('');
  const armL = doc.getElementById('brazo-izq'), armR = doc.getElementById('brazo-der');
  const piv = (el, dflt) => {
    const m = /rotate\(\s*[-\d.]+\s+([-\d.]+)\s+([-\d.]+)\s*\)/.exec(el.getAttribute('transform') || '');
    return m ? [parseFloat(m[1]), parseFloat(m[2])] : dflt;
  };
  const legs = ser(doc.getElementById('piernas'));
  const half = (x0, x1, id) => `<defs><clipPath id="${id}"><rect x="${x0}" y="300" width="${x1 - x0}" height="500"/></clipPath></defs><g clip-path="url(#${id})">${legs}</g>`;
  const src = {
    back, armL: ser(armL), armR: ser(armR),
    legL: half(-100, 200, 'mitadIzq'), legR: half(200, 500, 'mitadDer'),
    body: ser(doc.getElementById('cuerpo')), head: ser(doc.getElementById('cabeza')),
  };
  const ch = { img: {}, shL: piv(armL, [124, 266]), shR: piv(armR, [276, 266]) };
  for (const p of PARTS) ch.img[p] = src[p] ? await svgToCanvas(src[p]) : null;
  return ch;
};

// pose: {x,y, bob, lean, head, headDX, headDY, armL, armR, legL, legR, sit, cross, prop, alpha}
M.drawCharacter = function (ctx, ch, P) {
  const I = ch.img;
  const sit = P.sit || 0;
  const drop = sit * 150;               // cuánto baja la cadera al sentarse
  const legSY = (320 - drop) / 320;     // las piernas se comprimen (pies fijos)
  const draw = (im) => im && ctx.drawImage(im, 0, 0, 400, 780);
  const rot = (px, py, deg, fn) => {
    ctx.save(); ctx.translate(px, py); ctx.rotate((deg * Math.PI) / 180); ctx.translate(-px, -py); fn(); ctx.restore();
  };
  ctx.save();
  if (P.alpha !== undefined) ctx.globalAlpha = P.alpha;
  ctx.translate(P.x, P.y);
  ctx.scale(S, S);
  ctx.translate(-200, -760);
  // inclinación general desde los pies
  ctx.translate(200, 760); ctx.rotate(((P.lean || 0) * Math.PI) / 180); ctx.translate(-200, -760);
  // silla (cuando se sienta) — va detrás de todo
  if (P.chair) M.drawChairVB(ctx, P.chair, sit);
  ctx.translate(0, P.bob || 0);
  const upper = () => { ctx.translate(0, drop); };
  const sh = (fn) => { ctx.save(); upper(); fn(); ctx.restore(); };
  // pelo de atrás (Bolen, Doblón) se mueve con la cabeza
  const headT = (fn) => sh(() => rot(200, 262, P.head || 0, () => { ctx.translate(P.headDX || 0, P.headDY || 0); fn(); }));
  headT(() => draw(I.back));
  // brazos detrás del cuerpo (salvo brazos cruzados)
  const cross = P.cross || 0;
  const aL = M.lerp(P.armL || 0, -38, cross), aR = M.lerp(P.armR || 0, 38, cross);
  const drawArms = () => {
    sh(() => rot(ch.shL[0], ch.shL[1], aL, () => draw(I.armL)));
    sh(() => rot(ch.shR[0], ch.shR[1], aR, () => draw(I.armR)));
  };
  if (cross < 0.5) drawArms();
  // piernas: cadera baja, pies en el piso
  for (const [im, hx, ang] of [[I.legL, 166, P.legL || 0], [I.legR, 234, P.legR || 0]]) {
    ctx.save();
    ctx.translate(0, drop);
    ctx.translate(hx, 440);
    ctx.rotate((ang * Math.PI) / 180);
    ctx.scale(1, legSY);
    ctx.translate(-hx, -440);
    draw(im);
    ctx.restore();
  }
  sh(() => draw(I.body));
  headT(() => draw(I.head));
  if (cross >= 0.5) drawArms();
  if (P.prop) sh(() => M.drawPropVB(ctx, P.prop, P.propT || 0));
  ctx.restore();
};

// silla plástica (en coordenadas del viewBox del personaje)
M.drawChairVB = function (ctx, color) {
  ctx.save();
  ctx.fillStyle = color; ctx.strokeStyle = 'rgba(0,0,0,0.18)'; ctx.lineWidth = 4;
  // espaldar
  rr(ctx, 92, 300, 216, 210, 30); ctx.fill(); ctx.stroke();
  ctx.fillStyle = 'rgba(0,0,0,0.10)';
  for (let i = 0; i < 4; i++) { rr(ctx, 120 + i * 44, 330, 26, 120, 10); ctx.fill(); }
  // patas
  ctx.fillStyle = color;
  ctx.fillRect(96, 600, 22, 160); ctx.fillRect(282, 600, 22, 160);
  ctx.fillStyle = 'rgba(0,0,0,0.12)';
  ctx.fillRect(96, 600, 22, 160); ctx.fillRect(282, 600, 22, 160);
  // asiento
  ctx.fillStyle = color;
  rr(ctx, 80, 580, 240, 34, 14); ctx.fill(); ctx.stroke();
  ctx.restore();
};

// utilería en las manos: libreta o celular
M.drawPropVB = function (ctx, kind, k) {
  ctx.save();
  ctx.translate(200, 430);
  ctx.rotate(-0.08 + Math.sin(k * 3) * 0.03);
  if (kind === 'libreta') {
    ctx.fillStyle = '#FFFDF4'; ctx.strokeStyle = '#B9B2A0'; ctx.lineWidth = 3;
    rr(ctx, -70, -50, 140, 100, 8); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = '#8EB8E0'; ctx.lineWidth = 3;
    for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(-58, -30 + i * 17); ctx.lineTo(58, -30 + i * 17); ctx.stroke(); }
    ctx.strokeStyle = '#2F3B52'; ctx.lineWidth = 4;
    const n = Math.floor((k * 2) % 5);
    for (let i = 0; i < n; i++) { ctx.beginPath(); ctx.moveTo(-54, -34 + i * 17); ctx.lineTo(-54 + 70 + (i % 2) * 30, -34 + i * 17); ctx.stroke(); }
    ctx.fillStyle = '#E53935'; ctx.fillRect(-72, -52, 12, 104);
    // lápiz
    ctx.save(); ctx.translate(40 + Math.sin(k * 9) * 10, 10); ctx.rotate(-0.7);
    ctx.fillStyle = '#F6C343'; ctx.fillRect(-6, -60, 12, 60); ctx.fillStyle = '#333'; ctx.fillRect(-3, 0, 6, 8);
    ctx.restore();
  } else {
    ctx.fillStyle = '#1D1F24'; rr(ctx, -34, -60, 68, 120, 12); ctx.fill();
    ctx.fillStyle = '#7FD3FF'; rr(ctx, -27, -50, 54, 98, 6); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    for (let i = 0; i < 4; i++) ctx.fillRect(-20, -40 + i * 22 + ((k * 20) % 22), 30 + (i % 2) * 10, 8);
  }
  ctx.restore();
};

function rr(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
M.rr = rr;

// ---------------------------------------------------------------- motor (motocicleta)
M.drawMoto = function (ctx, x, y, flip, body, t = 0, running = false) {
  ctx.save();
  ctx.translate(x, y + (running ? Math.sin(t * 60) * 0.8 : 0));
  ctx.scale(flip ? -1 : 1, 1);
  // sombra
  ctx.fillStyle = 'rgba(0,0,0,0.18)';
  ctx.beginPath(); ctx.ellipse(0, 2, 230, 16, 0, 0, Math.PI * 2); ctx.fill();
  const wheel = (wx) => {
    ctx.fillStyle = '#1E1E22'; ctx.beginPath(); ctx.arc(wx, -62, 62, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#A9AFB7'; ctx.beginPath(); ctx.arc(wx, -62, 40, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#1E1E22'; ctx.beginPath(); ctx.arc(wx, -62, 32, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#A9AFB7'; ctx.lineWidth = 4;
    for (let i = 0; i < 6; i++) {
      const a = i * Math.PI / 3 + t * (running ? 12 : 0);
      ctx.beginPath(); ctx.moveTo(wx, -62); ctx.lineTo(wx + Math.cos(a) * 32, -62 + Math.sin(a) * 32); ctx.stroke();
    }
    ctx.fillStyle = '#D9DDE2'; ctx.beginPath(); ctx.arc(wx, -62, 9, 0, Math.PI * 2); ctx.fill();
  };
  wheel(-150); wheel(150);
  // escape
  ctx.fillStyle = '#C9CED6'; rr(ctx, -215, -112, 170, 22, 11); ctx.fill();
  // chasis
  ctx.strokeStyle = '#2B2B30'; ctx.lineWidth = 14; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-150, -62); ctx.lineTo(-40, -120); ctx.lineTo(60, -120); ctx.lineTo(150, -62); ctx.stroke();
  // horquilla
  ctx.strokeStyle = '#B8BEC6'; ctx.lineWidth = 12;
  ctx.beginPath(); ctx.moveTo(150, -62); ctx.lineTo(108, -230); ctx.stroke();
  // motor
  ctx.fillStyle = '#5B6068'; rr(ctx, -55, -140, 110, 70, 18); ctx.fill();
  ctx.fillStyle = '#7C828B'; rr(ctx, -35, -128, 60, 40, 10); ctx.fill();
  // tanque y carenado
  ctx.fillStyle = body;
  ctx.beginPath(); ctx.moveTo(-30, -150); ctx.quadraticCurveTo(20, -205, 105, -190); ctx.lineTo(118, -150); ctx.quadraticCurveTo(40, -135, -30, -150); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-200, -150); ctx.quadraticCurveTo(-150, -175, -40, -155); ctx.lineTo(-40, -138); ctx.quadraticCurveTo(-140, -128, -200, -150); ctx.fill();
  // guardafango
  ctx.beginPath(); ctx.moveTo(95, -95); ctx.quadraticCurveTo(150, -150, 215, -100); ctx.lineTo(205, -92); ctx.quadraticCurveTo(150, -132, 105, -88); ctx.fill();
  // asiento
  ctx.fillStyle = '#17171A'; rr(ctx, -175, -182, 170, 30, 14); ctx.fill();
  // timón y faro
  ctx.strokeStyle = '#2B2B30'; ctx.lineWidth = 9;
  ctx.beginPath(); ctx.moveTo(100, -240); ctx.lineTo(70, -262); ctx.stroke();
  ctx.fillStyle = '#F4F4F0'; ctx.beginPath(); ctx.arc(130, -215, 20, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#FFE082'; ctx.beginPath(); ctx.arc(133, -215, 12, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#E53935'; rr(ctx, -215, -165, 18, 12, 4); ctx.fill();
  ctx.restore();
};

// ---------------------------------------------------------------- escenario
// Coordenadas del mundo: suelo (acera) en y=1060; isleta al frente; grupo en y≈1610-1640.
const scene = { built: false };
function buildScene() {
  const r = rng(2015);
  // copa del árbol: manchas
  scene.canopy = [];
  const cx = 520, cy = 600, rx = 580, ry = 370;
  for (let i = 0; i < 300; i++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r());
    const x = cx + Math.cos(a) * rx * d, y = cy + Math.sin(a) * ry * d * 0.95;
    const rad = 50 + r() * 65;
    scene.canopy.push({ x, y, rad, ph: r() * 6.28 });
  }
  scene.canopy.sort((p, q) => p.y - q.y);
  scene.flowers = [];
  for (let i = 0; i < 300; i++) {
    const a = r() * Math.PI * 2, d = Math.pow(r(), 0.6);
    scene.flowers.push({ x: cx + Math.cos(a) * rx * d * 0.98, y: cy + Math.sin(a) * ry * d * 0.9 - 20, rad: 4 + r() * 6, ph: r() * 6.28, c: r() < 0.5 ? '#F4C430' : '#F9DC5C' });
  }
  scene.bgTrees = [];
  for (let i = 0; i < 70; i++) scene.bgTrees.push({ x: -700 + r() * 3200, y: 880 + r() * 150, rad: 70 + r() * 90, c: ['#2F6B34', '#3B7D3C', '#4A8F45'][Math.floor(r() * 3)] });
  scene.clouds = [];
  const cl = [[-300, -300, 1.2], [450, -420, 1.4], [1250, -250, 1.3], [1900, -380, 1.1], [150, 120, 0.9], [1050, 160, 1.0], [1750, 260, 0.8], [700, 420, 0.7]];
  for (const [x, y, s] of cl) {
    const puffs = [];
    for (let i = 0; i < 9; i++) puffs.push({ dx: (r() - 0.5) * 420 * s, dy: (r() - 0.5) * 90 * s, rad: (80 + r() * 90) * s });
    scene.clouds.push({ x, y, s, puffs, grey: y < -200 && x > 1000 });
  }
  scene.tracks = [];
  for (let i = 0; i < 26; i++) scene.tracks.push({ x: -500 + r() * 2800, y: 1120 + r() * 1700, w: 200 + r() * 600, a: (r() - 0.5) * 0.5 });
  scene.pebbles = [];
  for (let i = 0; i < 160; i++) scene.pebbles.push({ x: -700 + r() * 3200, y: 1090 + r() * 1800, rad: 2 + r() * 4 });
  scene.built = true;
}

function blob(ctx, x, y, rad) { ctx.moveTo(x + rad, y); ctx.arc(x, y, rad, 0, Math.PI * 2); }

M.drawSky = function (ctx, t) {
  if (!scene.built) buildScene();
  const g = ctx.createLinearGradient(0, -900, 0, 1060);
  g.addColorStop(0, '#5FA8DA'); g.addColorStop(0.55, '#97CBEB'); g.addColorStop(1, '#D9EEF8');
  ctx.fillStyle = g; ctx.fillRect(-1500, -1500, 5200, 2600);
  for (const c of scene.clouds) {
    const ox = c.x + t * 6 * c.s;
    ctx.fillStyle = c.grey ? '#B9C4CF' : '#FFFFFF';
    ctx.beginPath(); for (const p of c.puffs) blob(ctx, ox + p.dx, c.y + p.dy, p.rad); ctx.fill();
    ctx.fillStyle = c.grey ? '#A3AFBB' : '#E3ECF3';
    ctx.beginPath(); for (const p of c.puffs) blob(ctx, ox + p.dx, c.y + p.dy + p.rad * 0.35, p.rad * 0.75); ctx.fill();
    ctx.fillStyle = c.grey ? '#C6D0D9' : '#FFFFFF';
    ctx.beginPath(); for (const p of c.puffs) blob(ctx, ox + p.dx - p.rad * 0.1, c.y + p.dy - p.rad * 0.1, p.rad * 0.8); ctx.fill();
  }
};

M.drawBackground = function (ctx, t) {
  M.drawSky(ctx, t);
  // árboles del fondo
  for (const b of scene.bgTrees) { ctx.fillStyle = b.c; ctx.beginPath(); blob(ctx, b.x, b.y, b.rad); ctx.fill(); }
  // ---- hilera de locales verdes
  const shopColors = ['#EDEBE2', '#86CC96', '#9AD8A8', '#7DC48C', '#94D3A2', '#82C993', '#9BD9A9'];
  for (let i = 0; i < 7; i++) {
    const x = -400 + i * 200;
    ctx.fillStyle = shopColors[i]; ctx.fillRect(x, 895, 200, 165);
    ctx.fillStyle = 'rgba(0,0,0,0.08)'; ctx.fillRect(x + 192, 895, 8, 165);
    // puerta enrollable
    ctx.fillStyle = '#A3A9AE'; ctx.fillRect(x + 28, 948, 144, 112);
    ctx.fillStyle = '#8D9399';
    for (let k = 0; k < 13; k++) ctx.fillRect(x + 28, 952 + k * 8.5, 144, 2.5);
    ctx.fillStyle = '#7E848A'; ctx.fillRect(x + 28, 940, 144, 10);
  }
  // alero/parapeto crema
  ctx.fillStyle = '#E9DDAE'; ctx.fillRect(-420, 878, 1430, 24);
  ctx.fillStyle = '#D2C48F'; ctx.fillRect(-420, 900, 1430, 6);
  // ---- colmado
  ctx.fillStyle = '#6DBE7E'; ctx.fillRect(1000, 870, 260, 190);
  ctx.fillStyle = '#E9DDAE'; ctx.fillRect(990, 860, 280, 18);
  ctx.fillStyle = '#3A2A20'; ctx.fillRect(1035, 950, 190, 110);         // interior
  const shelf = ['#E53935', '#FDD835', '#1E88E5', '#43A047', '#FB8C00', '#FFFFFF'];
  for (let row = 0; row < 3; row++) {
    ctx.fillStyle = '#6D4C33'; ctx.fillRect(1035, 975 + row * 28, 190, 4);
    for (let k = 0; k < 11; k++) { ctx.fillStyle = shelf[(k + row * 2) % shelf.length]; ctx.fillRect(1042 + k * 17, 960 + row * 28, 11, 15); }
  }
  ctx.fillStyle = '#9EA4A9'; ctx.fillRect(1035, 940, 190, 12);
  // letrero COLMADO
  ctx.fillStyle = '#D7362B'; rr(ctx, 1018, 884, 224, 52, 8); ctx.fill();
  ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 3; rr(ctx, 1024, 890, 212, 40, 6); ctx.stroke();
  ctx.fillStyle = '#FFFFFF'; ctx.font = '900 32px Inter'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('COLMADO', 1130, 911);
  // nevera de hielo
  ctx.fillStyle = '#F7F7F7'; rr(ctx, 1004, 990, 52, 70, 6); ctx.fill();
  ctx.fillStyle = '#4FC3F7'; ctx.fillRect(1010, 1000, 40, 10);
  // ---- casa de dos pisos verde limón
  const hx = 1270, hw = 520;
  ctx.fillStyle = '#C8DC6C'; ctx.fillRect(hx, 640, hw, 420);
  ctx.fillStyle = '#F1EBC8'; ctx.fillRect(hx - 15, 618, hw + 30, 26);   // losa techo
  ctx.fillStyle = '#F1EBC8'; ctx.fillRect(hx - 15, 842, hw + 30, 16);   // losa balcón
  const arches = (y0, y1, n, dark) => {
    const aw = hw / n;
    for (let k = 0; k < n; k++) {
      const ax = hx + k * aw + aw * 0.16, w = aw * 0.68;
      ctx.fillStyle = dark;
      ctx.beginPath(); ctx.moveTo(ax, y1); ctx.lineTo(ax, y0 + w / 2); ctx.arc(ax + w / 2, y0 + w / 2, w / 2, Math.PI, 0); ctx.lineTo(ax + w, y1); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = '#F1EBC8'; ctx.lineWidth = 6; ctx.stroke();
    }
  };
  arches(668, 842, 4, '#4B5A3C');
  // ventanas con rejas dentro del balcón
  ctx.strokeStyle = '#26301E'; ctx.lineWidth = 3;
  for (let k = 0; k < 4; k++) {
    const ax = hx + k * 130 + 40;
    ctx.fillStyle = '#7D9A9F'; ctx.fillRect(ax, 720, 50, 70);
    for (let j = 0; j < 5; j++) { ctx.beginPath(); ctx.moveTo(ax + j * 12.5, 720); ctx.lineTo(ax + j * 12.5, 790); ctx.stroke(); }
  }
  // balaustrada blanca
  ctx.fillStyle = '#FFFFFF'; ctx.fillRect(hx, 784, hw, 10); ctx.fillRect(hx, 834, hw, 8);
  for (let k = 0; k < 34; k++) { const bx = hx + 8 + k * 15.2; rr(ctx, bx, 794, 9, 40, 4); ctx.fill(); }
  // columnas
  ctx.fillStyle = '#B6CB59';
  for (let k = 0; k <= 4; k++) ctx.fillRect(hx + k * 130 - 8, 660, 16, 400);
  arches(880, 1060, 4, '#55663F');
  // puerta
  ctx.fillStyle = '#6B4A2E'; ctx.fillRect(hx + 175, 945, 60, 115);
  // verja de hierro negra
  ctx.fillStyle = '#C8DC6C'; ctx.fillRect(hx - 10, 1030, hw + 20, 30);
  ctx.fillStyle = '#B6CB59';
  for (let k = 0; k <= 4; k++) ctx.fillRect(hx + k * 130 - 14, 975, 28, 85);
  ctx.strokeStyle = '#151515'; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(hx, 990); ctx.lineTo(hx + hw, 990); ctx.moveTo(hx, 1026); ctx.lineTo(hx + hw, 1026); ctx.stroke();
  ctx.lineWidth = 3;
  for (let bx = hx; bx < hx + hw; bx += 13) { ctx.beginPath(); ctx.moveTo(bx, 984); ctx.lineTo(bx, 1030); ctx.stroke(); }
  // ---- postes y cables
  ctx.fillStyle = '#C9C3B6';
  for (const px of [-260, 1235, 2150]) { ctx.fillRect(px - 9, 380, 18, 690); ctx.fillRect(px - 50, 400, 100, 10); }
  ctx.strokeStyle = 'rgba(40,40,45,0.85)'; ctx.lineWidth = 3;
  const cab = (y0, y1, y2, sag) => {
    ctx.beginPath(); ctx.moveTo(-1500, y0 - 120);
    ctx.quadraticCurveTo(-880, y0 + sag, -260, y0);
    ctx.quadraticCurveTo(490, y1 + sag, 1235, y1);
    ctx.quadraticCurveTo(1690, y2 + sag * 0.6, 2150, y2);
    ctx.quadraticCurveTo(2700, y2 + sag, 3200, y2 - 200);
    ctx.stroke();
  };
  cab(400, 404, 402, 110); cab(408, 412, 410, 150); cab(404, 408, 406, 190);
  ctx.beginPath(); ctx.moveTo(-900, -500); ctx.quadraticCurveTo(400, -120, 2800, -650); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(-900, -440); ctx.quadraticCurveTo(500, -40, 2800, -560); ctx.stroke();
  // ---- acera y suelo de arena
  ctx.fillStyle = '#D3CBB8'; ctx.fillRect(-1500, 1058, 5200, 30);
  ctx.fillStyle = '#BDB4A0'; ctx.fillRect(-1500, 1086, 5200, 6);
  const sg = ctx.createLinearGradient(0, 1090, 0, 2900);
  sg.addColorStop(0, '#E2CFA6'); sg.addColorStop(1, '#EBDCBB');
  ctx.fillStyle = sg; ctx.fillRect(-1500, 1090, 5200, 2400);
  ctx.strokeStyle = 'rgba(160,130,90,0.20)'; ctx.lineWidth = 10; ctx.lineCap = 'round';
  for (const k of scene.tracks) {
    ctx.save(); ctx.translate(k.x, k.y); ctx.rotate(k.a);
    ctx.beginPath(); ctx.moveTo(-k.w / 2, 0); ctx.quadraticCurveTo(0, 30, k.w / 2, 0); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-k.w / 2, 26); ctx.quadraticCurveTo(0, 56, k.w / 2, 26); ctx.stroke();
    ctx.restore();
  }
  ctx.fillStyle = 'rgba(150,120,85,0.35)';
  for (const p of scene.pebbles) { ctx.beginPath(); blob(ctx, p.x, p.y, p.rad); ctx.fill(); }
  // ---- isleta triangular de cemento
  const isle = () => {
    ctx.beginPath();
    ctx.moveTo(-260, 1712);
    ctx.quadraticCurveTo(-120, 1640, 380, 1430);
    ctx.quadraticCurveTo(600, 1320, 820, 1430);
    ctx.quadraticCurveTo(1350, 1640, 1520, 1712);
    ctx.quadraticCurveTo(1540, 1752, 1470, 1758);
    ctx.quadraticCurveTo(630, 1790, -210, 1758);
    ctx.quadraticCurveTo(-290, 1752, -260, 1712);
    ctx.closePath();
  };
  ctx.save(); ctx.translate(0, 20); ctx.fillStyle = '#A59E90'; isle(); ctx.fill(); ctx.restore();
  ctx.fillStyle = '#D6D1C6'; isle(); ctx.fill();
  ctx.strokeStyle = '#BDB7AA'; ctx.lineWidth = 8; isle(); ctx.stroke();
  // grietas y manchas
  ctx.strokeStyle = 'rgba(120,110,95,0.25)'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(300, 1560); ctx.lineTo(380, 1600); ctx.lineTo(420, 1660); ctx.moveTo(980, 1560); ctx.lineTo(1050, 1650); ctx.stroke();
  // sombra del árbol sobre la isleta
  ctx.fillStyle = 'rgba(40,50,30,0.16)';
  ctx.beginPath(); ctx.ellipse(560, 1560, 720, 130, 0, 0, Math.PI * 2); ctx.fill();
  // ---- tronco
  ctx.fillStyle = '#6E4B2F';
  ctx.beginPath();
  ctx.moveTo(470, 1580); ctx.quadraticCurveTo(505, 1300, 490, 950); ctx.lineTo(580, 950); ctx.quadraticCurveTo(575, 1300, 615, 1580); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#5A3C25';
  ctx.beginPath(); ctx.moveTo(555, 1580); ctx.quadraticCurveTo(555, 1300, 570, 950); ctx.lineTo(580, 950); ctx.quadraticCurveTo(575, 1300, 615, 1580); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = '#6E4B2F'; ctx.lineCap = 'round';
  for (const [x0, y0, x1, y1, w] of [[530, 1060, 250, 800, 34], [540, 1040, 830, 780, 34], [530, 1120, 120, 900, 22], [545, 1100, 960, 900, 22], [535, 1000, 500, 600, 30], [350, 900, 300, 660, 18], [760, 850, 820, 640, 18]]) {
    ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo((x0 + x1) / 2, y0 - 40, x1, y1); ctx.stroke();
  }
};

// copa del árbol (se dibuja después del fondo y antes de los personajes)
M.drawCanopy = function (ctx, t) {
  const sw = (p) => Math.sin(t * 0.9 + p.ph) * 4;
  const shade = (y) => (y > 820 ? '#2C5A2A' : y > 560 ? '#356B31' : '#3F7A38');
  ctx.fillStyle = '#244D24';
  ctx.beginPath(); for (const p of scene.canopy) blob(ctx, p.x + sw(p), p.y + 18, p.rad); ctx.fill();
  for (const p of scene.canopy) { ctx.fillStyle = shade(p.y); ctx.beginPath(); blob(ctx, p.x + sw(p), p.y, p.rad * 0.92); ctx.fill(); }
  ctx.fillStyle = 'rgba(120,170,80,0.35)';
  ctx.beginPath(); for (const p of scene.canopy) if (p.y < 700) blob(ctx, p.x + sw(p) - p.rad * 0.25, p.y - p.rad * 0.3, p.rad * 0.45); ctx.fill();
  for (const f of scene.flowers) {
    ctx.fillStyle = f.c; ctx.beginPath(); blob(ctx, f.x + Math.sin(t * 0.9 + f.ph) * 4, f.y, f.rad); ctx.fill();
  }
};

// ---------------------------------------------------------------- texto
M.wrap = function (ctx, text, maxW) {
  const words = text.split(' ');
  const lines = []; let cur = '';
  for (const w of words) {
    const test = cur ? cur + ' ' + w : w;
    if (ctx.measureText(test).width > maxW && cur) { lines.push(cur); cur = w; } else cur = test;
  }
  if (cur) lines.push(cur);
  return lines;
};

M.drawSubtitle = function (ctx, who, color, text, k) {
  // k: 0..1 aparición
  const a = M.smooth(k * 1.0);
  ctx.save();
  ctx.globalAlpha = a;
  ctx.font = '900 64px Inter';
  const lines = M.wrap(ctx, text, 930);
  const lh = 78;
  const boxH = lines.length * lh + 50;
  const y0 = 1560 - boxH / 2 + (1 - a) * 30;
  ctx.fillStyle = 'rgba(20,12,8,0.78)';
  rr(ctx, 50, y0, 980, boxH, 34); ctx.fill();
  // etiqueta con el nombre
  ctx.font = '900 46px Inter';
  const nw = ctx.measureText(who).width + 56;
  ctx.fillStyle = color; rr(ctx, 80, y0 - 42, nw, 70, 35); ctx.fill();
  ctx.fillStyle = '#1B120C'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(who, 108, y0 - 6);
  ctx.font = '900 64px Inter';
  ctx.textAlign = 'center';
  lines.forEach((ln, i) => {
    const y = y0 + 42 + lh / 2 + i * lh - 10;
    ctx.lineWidth = 10; ctx.strokeStyle = '#000'; ctx.lineJoin = 'round';
    ctx.strokeText(ln, 540, y);
    ctx.fillStyle = '#FFFFFF'; ctx.fillText(ln, 540, y);
  });
  ctx.restore();
};
