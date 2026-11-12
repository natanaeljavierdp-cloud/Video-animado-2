// ============================================================
//  Escenas, mapas, subtítulos y render(t)
//  Tiempos tomados de la transcripción por palabra (words.json)
// ============================================================
const DUR = 67.0;
const SD = [-69.93, 18.49], DC = [-77.04, 38.91], MOS = [37.62, 55.75];

// ---------- Mapa plano de RD ----------
const G = window.GEO;
function drProj(x0, y0, x1, y1) { return d3.geoMercator().fitExtent([[x0, y0], [x1, y1]], G.dr); }
function drawDR(proj, { fill = RED, stroke = WHITE, sw = 4, haiti = 'rgba(255,255,255,.12)', glow = 'rgba(206,17,38,.7)', alpha = 1, drawK = 1 } = {}) {
  const path = d3.geoPath(proj, ctx);
  ctx.save(); ctx.globalAlpha *= alpha;
  if (haiti) { ctx.beginPath(); path(G.haiti); ctx.fillStyle = haiti; ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,.25)'; ctx.lineWidth = 2; ctx.stroke(); }
  if (fill) { ctx.beginPath(); path(G.dr); ctx.shadowColor = glow; ctx.shadowBlur = 50; ctx.fillStyle = fill; ctx.fill(); ctx.shadowBlur = 0; }
  if (stroke) {
    ctx.beginPath(); path(G.dr); ctx.strokeStyle = stroke; ctx.lineWidth = sw; ctx.lineJoin = 'round';
    if (drawK < 1) { ctx.setLineDash([4000 * drawK, 4000]); }
    ctx.stroke(); ctx.setLineDash([]);
  }
  ctx.restore();
}

// Luces dentro de RD (escena 1)
const S1P = drProj(90, 640, 990, 1080);
const LIGHTS = [];
(function () {
  for (let y = 600; y < 1120; y += 15) for (let x = 60; x < 1020; x += 15) {
    const jx = x + (hash(x * 7 + y) - .5) * 8, jy = y + (hash(x + y * 13) - .5) * 8;
    const ll = S1P.invert([jx, jy]);
    if (ll && d3.geoContains(G.dr, ll)) LIGHTS.push({ x: jx, y: jy, off: 3.05 + Math.pow(hash(x * 3.1 + y * 1.7), 1.3) * 1.35 + (x - 60) / 960 * .25, r: 1.6 + hash(x + y) * 2.2 });
  }
})();

// ---------- Globo ----------
const GRAT = d3.geoGraticule10();
const SPHERE = { type: 'Sphere' };
function drawGlobe(cx, cy, r, scale, rot, opts = {}) {
  const proj = d3.geoOrthographic().scale(scale).translate([cx, cy]).rotate([-rot[0], -rot[1]]).clipAngle(90).precision(.3);
  const path = d3.geoPath(proj, ctx);
  ctx.save();
  ctx.globalAlpha *= (opts.alpha ?? 1);
  // halo
  ctx.save(); ctx.shadowColor = 'rgba(60,140,255,.55)'; ctx.shadowBlur = 70;
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fillStyle = NAVY_D; ctx.fill(); ctx.restore();
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.clip();
  let g = ctx.createRadialGradient(cx - r * .35, cy - r * .4, r * .1, cx, cy, r * 1.05);
  g.addColorStop(0, '#16407F'); g.addColorStop(1, '#06132E');
  ctx.fillStyle = g; ctx.fillRect(cx - r, cy - r, 2 * r, 2 * r);
  ctx.beginPath(); path(GRAT); ctx.strokeStyle = 'rgba(160,200,255,.12)'; ctx.lineWidth = 1.5; ctx.stroke();
  ctx.beginPath(); path(G.land); ctx.fillStyle = '#2D4C7E'; ctx.fill();
  if (opts.usa) { ctx.beginPath(); path(G.usa); ctx.fillStyle = `rgba(150,190,255,${.55 * opts.usa})`; ctx.fill(); }
  if (opts.rus) { ctx.beginPath(); path(G.rus); ctx.fillStyle = `rgba(206,17,38,${.6 * opts.rus})`; ctx.fill(); }
  ctx.beginPath(); path(G.countries); ctx.strokeStyle = 'rgba(200,220,255,.28)'; ctx.lineWidth = 1.2; ctx.stroke();
  ctx.beginPath(); path(G.dr); ctx.fillStyle = RED; ctx.shadowColor = RED_L; ctx.shadowBlur = 25; ctx.fill(); ctx.shadowBlur = 0;
  // arcos
  for (const a of (opts.arcs || [])) {
    if (a.k <= 0) continue;
    const ip = d3.geoInterpolate(a.from, a.to), n = 80, pts = [];
    for (let i = 0; i <= n * a.k; i++) pts.push(ip(i / n));
    pts.push(ip(a.k));
    const line = { type: 'LineString', coordinates: pts };
    ctx.beginPath(); path(line); ctx.strokeStyle = 'rgba(255,59,78,.35)'; ctx.lineWidth = 16; ctx.lineCap = 'round'; ctx.stroke();
    ctx.beginPath(); path(line); ctx.strokeStyle = RED_L; ctx.lineWidth = 6; ctx.stroke();
    const hp = proj(ip(a.k));
    if (a.k < 1 && hp) { ctx.fillStyle = WHITE; ctx.shadowColor = WHITE; ctx.shadowBlur = 25; ctx.beginPath(); ctx.arc(hp[0], hp[1], 10, 0, 7); ctx.fill(); ctx.shadowBlur = 0; }
  }
  // brillo especular
  g = ctx.createRadialGradient(cx - r * .45, cy - r * .5, 0, cx - r * .45, cy - r * .5, r * 1.1);
  g.addColorStop(0, 'rgba(255,255,255,.16)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g; ctx.fillRect(cx - r, cy - r, 2 * r, 2 * r);
  ctx.restore();
  ctx.save(); ctx.globalAlpha *= (opts.alpha ?? 1);
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.strokeStyle = 'rgba(160,200,255,.55)'; ctx.lineWidth = 3; ctx.stroke();
  // pines
  for (const p of (opts.pins || [])) {
    if (p.k <= 0) continue;
    const center = proj.invert([cx, cy]);
    if (d3.geoDistance(p.ll, center) > Math.PI / 2 - .05) continue;
    const [x, y] = proj(p.ll);
    if (Math.hypot(x - cx, y - cy) > r - 6) continue;
    const s = eBack(p.k);
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); iconPin(0, 0, 44, p.col || WHITE); ctx.restore();
    const lw = measure(p.label, F(800, 30), 2) + 28, lx = x + (p.dx ?? 0), ly = y + (p.dy ?? -78);
    ctx.save(); ctx.globalAlpha *= p.k;
    rr(lx - lw / 2, ly - 24, lw, 48, 8); ctx.fillStyle = p.bg || NAVY; ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,.5)'; ctx.lineWidth = 2; ctx.stroke();
    text(p.label, lx, ly + 2, { font: F(800, 30), ls: 2, shadow: false });
    ctx.restore();
  }
  ctx.restore();
}
function rotLerp(a, b, k) {
  // interpolar en esfera para un giro natural
  const ip = d3.geoInterpolate(a, b); return ip(k);
}

// ---------- Subtítulos palabra por palabra ----------
const CHUNKS = [];
(function () {
  let cur = null;
  WORDS.forEach((w, i) => {
    const prev = WORDS[i - 1];
    const brk = !cur || cur.words.length >= 4 || (cur.chars + w.w.length > 20) || /[.,?!:]$/.test(prev.w) || (w.s - prev.e > .5);
    if (brk) { cur = { words: [], chars: 0 }; CHUNKS.push(cur); }
    cur.words.push(w); cur.chars += w.w.length + 1;
  });
  CHUNKS.forEach((c, i) => {
    c.s = c.words[0].s - .06;
    const last = c.words[c.words.length - 1];
    c.e = i < CHUNKS.length - 1 ? Math.min(CHUNKS[i + 1].words[0].s - .06, last.e + .7) : last.e + .5;
  });
})();
function subtitles(t) {
  const c = CHUNKS.find(c => t >= c.s && t < c.e);
  if (!c) return;
  const font = F(900, 64), ls = 1, gap = 20, y = 300;
  const items = c.words.map(w => ({ w, str: w.w.toUpperCase().replace(/[.,:]$/, ''), width: measure(w.w.toUpperCase().replace(/[.,:]$/, ''), font, ls) }));
  // layout en líneas (máx 920 px)
  const lines = [[]]; let lw = 0;
  for (const it of items) { if (lw + it.width > 920 && lines[lines.length - 1].length) { lines.push([]); lw = 0; } lines[lines.length - 1].push(it); lw += it.width + gap; }
  const lh = 86, y0 = y - (lines.length - 1) * lh / 2;
  const active = [...c.words].reverse().find(w => t >= w.s - .04);
  lines.forEach((ln, li) => {
    const tw = ln.reduce((s, it) => s + it.width, 0) + gap * (ln.length - 1);
    let x = W / 2 - tw / 2;
    for (const it of ln) {
      const k = A(t, it.w.s - .06, it.w.s + .1);
      if (k > 0) {
        const isA = it.w === active;
        const sc = .7 + .3 * eBack(k);
        ctx.save(); ctx.translate(x + it.width / 2, y0 + li * lh); ctx.scale(sc, sc); ctx.globalAlpha = k;
        if (isA) { rr(-it.width / 2 - 14, -42, it.width + 28, 84, 12); ctx.fillStyle = RED; ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 20; ctx.fill(); ctx.shadowBlur = 0; }
        text(it.str, 0, 3, { font, ls, color: WHITE, stroke: isA ? null : 'rgba(5,14,34,.95)', sw: 12, shadow: !isA });
        ctx.restore();
      }
      x += it.width + gap;
    }
  });
}

// ---------- Marca ----------
function brandChip(t, alpha) {
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha = alpha * .95;
  const x = 54, y = 128;
  rr(x, y - 30, 410, 60, 30); ctx.fillStyle = 'rgba(10,31,68,.78)'; ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 2; ctx.stroke();
  iconMag(x + 34, y + 2, 46, 1, 1, WHITE, RED_L);
  text('CAPITAL CURIOSO', x + 66, y + 2, { font: F(800, 25), align: 'left', ls: 3, shadow: false });
  flagDR(x + 358, y - 12, 34, 24);
  ctx.restore();
}

// ============================================================
//  ESCENAS
// ============================================================

// 1 · Apagón total [0 – 7.3]
function scene1(t) {
  if (t > 7.35) return;
  // "HACE UN AÑO" + fecha
  const a1 = t < 2.78 ? eOut(A(t, .1, .5)) : (t < 2.98 ? (hash(Math.floor(t * 40)) > .5 ? 1 : 0) * (1 - A(t, 2.78, 2.98)) : 0);
  if (a1 > 0) {
    pill('HACE UN AÑO', W / 2, 830, { alpha: a1, scale: .9 + .1 * eBack(A(t, .1, .5)) });
    const k = eOut(A(t, .25, .95));
    ctx.save(); ctx.globalAlpha = a1;
    ctx.beginPath(); ctx.rect(0, 880, W * k + 1, 200); ctx.clip();
    text('11 NOV 2025', W / 2, 975, { font: F(900, 136), ls: 2 });
    ctx.restore();
    ctx.save(); ctx.globalAlpha = a1; ctx.fillStyle = RED; ctx.fillRect(W / 2 - 330 * k, 1062, 660 * k, 8); ctx.restore();
  }
  // mapa apagándose
  const am = env(t, 2.85, 7.3, .3, .25);
  if (am > 0) {
    ctx.save(); ctx.globalAlpha = am;
    const off = A(t, 3.1, 4.5);
    drawDR(S1P, { fill: `rgba(${lerp(255, 25, off) | 0},${lerp(190, 30, off) | 0},${lerp(80, 50, off) | 0},${lerp(.35, .85, off)})`, glow: off < 1 ? 'rgba(255,190,80,.6)' : 'rgba(206,17,38,.6)', stroke: off > .5 ? RED_L : '#FFD9A0', sw: 5 });
    // luces
    for (const L of LIGHTS) {
      if (t > L.off + .12) continue;
      const fl = t > L.off ? (hash(L.x + Math.floor(t * 30)) > .5 ? 1 : .2) : 1;
      ctx.fillStyle = `rgba(255,214,130,${.95 * fl})`; ctx.shadowColor = 'rgba(255,190,90,.9)'; ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.arc(L.x, L.y, L.r, 0, 7); ctx.fill();
    }
    ctx.shadowBlur = 0;
    text('REPÚBLICA DOMINICANA', W / 2, 1125, { font: F(800, 34), ls: 6, color: ICE, alpha: eOut(A(t, 3.0, 3.4)) });
    ctx.restore();
  }
  // contador
  const ac = env(t, 4.0, 7.3, .3, .25);
  if (ac > 0) {
    ctx.save(); ctx.globalAlpha = ac;
    text('CASI', W / 2, 1215, { font: F(800, 44), ls: 8, color: RED_L });
    const v = 11e6 * eOut(A(t, 4.05, 5.9));
    const sc = 1 + .08 * (1 - eOut(A(t, 5.9, 6.3))) * (t > 5.9 ? 1 : 0);
    ctx.save(); ctx.translate(W / 2, 1330); ctx.scale(sc, sc);
    text(fmt(v), 0, 0, { font: F(900, 140), ls: -2 });
    ctx.restore();
    const ks = eBack(A(t, 5.95, 6.35));
    if (ks > 0) pill('SIN LUZ', W / 2, 1462, { font: F(900, 62), h: 100, padX: 40, ls: 6, scale: ks });
    ctx.restore();
  }
}

// 2 · 104 días [7.3 – 12.7]
function scene2(t) {
  if (t < 7.2 || t > 10.8) return;
  const a = env(t, 7.3, 10.75, .3, .45);
  ctx.save(); ctx.globalAlpha = a;
  const n = Math.round(104 * eOut(A(t, 7.36, 8.15)));
  const pop = t > 8.15 ? 1 + .1 * (1 - eOut(A(t, 8.15, 8.5))) : 1;
  ctx.save(); ctx.translate(W / 2, 830); ctx.scale(pop, pop);
  text(String(n), 0, 0, { font: F(900, 290), ls: -6 });
  ctx.restore();
  pill('DÍAS DESPUÉS', W / 2, 1010, { font: F(900, 50), h: 86, ls: 6, scale: eBack(A(t, 7.6, 8.0)), alpha: A(t, 7.6, 7.8) });
  // línea de tiempo
  const x0 = 150, x1 = 930, y = 1210, k = eIO(A(t, 7.7, 8.7));
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
  ctx.strokeStyle = RED_L; ctx.shadowColor = RED; ctx.shadowBlur = 18; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(lerp(x0, x1, k), y); ctx.stroke(); ctx.shadowBlur = 0;
  for (let i = 1; i < 15; i++) { const x = lerp(x0, x1, i / 15); if (x < lerp(x0, x1, k)) { ctx.fillStyle = 'rgba(255,255,255,.6)'; ctx.fillRect(x - 1.5, y - 12, 3, 24); } }
  const dot = (x, kk, lbl, sub, hot) => {
    if (kk <= 0) return; const s = eBack(kk);
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
    if (hot) { const pr = A(t, 9.26, 10.2); ctx.strokeStyle = `rgba(255,59,78,${1 - pr})`; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, 22 + pr * 70, 0, 7); ctx.stroke(); }
    ctx.fillStyle = RED; ctx.beginPath(); ctx.arc(0, 0, 22, 0, 7); ctx.fill(); ctx.strokeStyle = WHITE; ctx.lineWidth = 5; ctx.stroke();
    ctx.restore();
    text(lbl, x, y + 70, { font: F(900, 40), alpha: kk });
    text(sub, x, y + 118, { font: F(700, 28), ls: 4, color: ICE, alpha: kk });
  };
  dot(x0, A(t, 7.6, 7.9), '11 NOV 2025', 'APAGÓN', false);
  dot(x1, A(t, 8.6, 8.9), '23 FEB 2026', t > 9.26 ? 'OTRO APAGÓN' : '', t > 9.26);
  if (t > 9.26) { const kb = eBack(A(t, 9.26, 9.6)); ctx.save(); ctx.translate(x1, y - 105); ctx.scale(kb, kb); ctx.fillStyle = RED; ctx.beginPath(); ctx.arc(0, 0, 50, 0, 7); ctx.fill(); iconBolt(0, 0, 70); ctx.restore(); }
  ctx.restore();
}

// 3 · Palacio: el acuerdo [12.7 – 18.0]
function scene3(t) {
  if (t < 12.6 || t > 18.1) return;
  const a = env(t, 12.7, 18.05, .3, .3);
  ctx.save(); ctx.globalAlpha = a;
  // rótulo de lugar
  const al = env(t, 12.95, 15.4, .4, .3);
  if (al > 0) {
    ctx.save(); ctx.globalAlpha *= al; const x = 60 - 40 * (1 - eOut(A(t, 12.95, 13.4)));
    ctx.fillStyle = RED; ctx.fillRect(x, 1500, 8, 96);
    text('PALACIO NACIONAL', x + 30, 1527, { font: F(900, 40), align: 'left', ls: 3 });
    text('Santo Domingo, República Dominicana', x + 30, 1574, { font: F(600, 30), align: 'left', color: ICE });
    ctx.restore();
  }
  // documento
  const up = eOut(A(t, 12.8, 13.35));
  const shrink = eIO(A(t, 15.4, 16.0));
  const dx = W / 2, dy = lerp(lerp(1300, 1000, up), 880, shrink), ds = lerp(1, .78, shrink);
  ctx.save(); ctx.translate(dx, dy); ctx.rotate((-3 + 1.5 * shrink) * Math.PI / 180); ctx.scale(ds, ds); ctx.globalAlpha *= up;
  const w = 520, h = 660;
  ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 20;
  rr(-w / 2, -h / 2, w, h, 10); ctx.fillStyle = '#F7F4EC'; ctx.fill(); ctx.shadowColor = 'transparent';
  rr(-w / 2, -h / 2, w, 86, [10, 10, 0, 0]); ctx.fillStyle = NAVY; ctx.fill();
  text('ACUERDO', 0, -h / 2 + 46, { font: F(900, 38), ls: 10, shadow: false });
  const lk = A(t, 13.0, 13.8);
  ctx.fillStyle = 'rgba(10,31,68,.28)';
  for (let i = 0; i < 9; i++) { const ww = (i % 3 === 2 ? 260 : 400) * clamp(lk * 9 - i); if (ww > 0) { rr(-200, -h / 2 + 130 + i * 38, ww, 14, 7); ctx.fill(); } }
  // firma
  const sk = A(t, 13.25, 14.7);
  ctx.strokeStyle = 'rgba(10,31,68,.5)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-200, 230); ctx.lineTo(60, 230); ctx.stroke();
  text('FIRMA', -200, 255, { font: F(700, 18), align: 'left', ls: 3, color: 'rgba(10,31,68,.6)', shadow: false });
  if (sk > 0) {
    ctx.strokeStyle = '#0B2A6B'; ctx.lineWidth = 5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath(); const N = 120, m = Math.floor(N * eIO(sk));
    for (let i = 0; i <= m; i++) {
      const u = i / N, x = -190 + u * 250;
      const y = 205 + Math.sin(u * 22) * 22 * (1 - u * .4) - Math.sin(u * 5) * 12 + (u > .8 ? (u - .8) * 80 : 0);
      i ? ctx.lineTo(x + Math.cos(u * 22) * 10, y) : ctx.moveTo(x, y);
    }
    ctx.stroke();
    // pluma
    if (sk < 1) { const u = m / N, px = -190 + u * 250 + Math.cos(u * 22) * 10, py = 205 + Math.sin(u * 22) * 22 * (1 - u * .4) - Math.sin(u * 5) * 12; ctx.save(); ctx.translate(px, py); ctx.rotate(-.7); ctx.fillStyle = '#111'; rr(-6, -110, 14, 110, 4); ctx.fill(); ctx.fillStyle = '#C9A44C'; ctx.beginPath(); ctx.moveTo(-6, 0); ctx.lineTo(8, 0); ctx.lineTo(1, 16); ctx.fill(); ctx.restore(); }
  }
  // sello
  const st = A(t, 14.6, 14.85);
  if (st > 0) {
    const s = lerp(2, 1, eOut(st)); ctx.save(); ctx.translate(160, 220); ctx.rotate(-.25); ctx.scale(s, s); ctx.globalAlpha *= st;
    ctx.strokeStyle = RED; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, 46, 0, 7); ctx.lineWidth = 2; ctx.stroke();
    text('RD', 0, -6, { font: F(900, 34), color: RED, shadow: false }); text('EE. UU.', 0, 24, { font: F(800, 16), color: RED, shadow: false });
    ctx.restore();
  }
  ctx.restore();
  // átomo + título
  const at = A(t, 15.5, 15.95);
  if (at > 0) {
    const s = eBack(at);
    ctx.save(); ctx.translate(800, 640); ctx.scale(s, s);
    ctx.fillStyle = 'rgba(10,31,68,.92)'; ctx.beginPath(); ctx.arc(0, 0, 105, 0, 7); ctx.fill(); ctx.strokeStyle = RED_L; ctx.lineWidth = 5; ctx.stroke();
    iconAtom(0, 0, 165, t); ctx.restore();
    const tk = eOut(A(t, 15.7, 16.2));
    text('ACUERDO NUCLEAR', W / 2, 1330 + 30 * (1 - tk), { font: F(900, 92), alpha: tk, ls: 1 });
    const fk = eOut(A(t, 16.0, 16.5));
    ctx.save(); ctx.globalAlpha *= fk;
    const y = 1440, tw = measure('RD – EE. UU.', F(900, 64), 2);
    flagDR(W / 2 - tw / 2 - 120, y - 33, 96, 66);
    text('RD – EE. UU.', W / 2, y + 3, { font: F(900, 64), ls: 2, color: WHITE });
    flagUS(W / 2 + tw / 2 + 24, y - 33, 96, 66);
    ctx.restore();
  }
  ctx.restore();
}

// 4 · Washington + objetivos [18.0 – 28.1]
const ROT_SD = [-70.5, 19], ROT_SDDC = [-73.6, 29.2], ROT_SDMOS = d3.geoInterpolate(SD, MOS)(.5);
function scene4(t) {
  if (t < 17.9 || t > 28.2) return;
  // Globo SD → Washington
  const ag = env(t, 18.05, 24.2, .4, .35);
  if (ag > 0) {
    const zk = eIO(A(t, 18.0, 19.2));
    const rot = rotLerp(ROT_SD, ROT_SDDC, zk), sc = lerp(340, 1050, zk);
    drawGlobe(W / 2, 900, 340, sc, rot, {
      alpha: ag, usa: eOut(A(t, 18.4, 19)),
      arcs: [{ from: SD, to: DC, k: eIO(A(t, 18.45, 19.6)) }],
      pins: [{ ll: SD, label: 'SANTO DOMINGO', k: A(t, 18.3, 18.6), col: RED, dy: 50, bg: RED },
             { ll: DC, label: 'WASHINGTON', k: A(t, 19.4, 19.7), col: WHITE, dy: -82 }]
    });
    // rótulo JUNIO 2026
    const jk = A(t, 19.5, 19.85);
    if (jk > 0) {
      ctx.save(); ctx.globalAlpha = ag;
      const s = eBack(jk); ctx.translate(W / 2, 1335); ctx.scale(s, s);
      rr(-280, -50, 560, 100, 14); ctx.fillStyle = RED; ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; ctx.fill(); ctx.shadowBlur = 0;
      iconCalendar(-218, 0, 62);
      text('JUNIO 2026', 42, 3, { font: F(900, 58), ls: 3, shadow: false });
      ctx.restore();
    }
    // tarjeta de fuente
    const fk = env(t, 20.85, 24.1, .45, .3);
    if (fk > 0) {
      ctx.save(); ctx.globalAlpha = ag * fk; const oy = 40 * (1 - eOut(A(t, 20.85, 21.35)));
      ctx.translate(0, oy);
      rr(70, 1430, 940, 200, 18); ctx.fillStyle = 'rgba(247,244,236,.97)'; ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 40; ctx.fill(); ctx.shadowBlur = 0;
      ctx.fillStyle = NAVY; ctx.fillRect(70, 1430, 14, 200);
      text('OBJETIVO', 120, 1474, { font: F(900, 26), align: 'left', ls: 5, color: RED, shadow: false });
      text('Cooperar en energía nuclear civil', 120, 1528, { font: F(800, 44), align: 'left', color: NAVY, shadow: false });
      ctx.fillStyle = 'rgba(10,31,68,.15)'; ctx.fillRect(120, 1562, 840, 2);
      text('FUENTE: Departamento de Estado de EE. UU.', 120, 1598, { font: F(700, 28), align: 'left', color: '#3A4A66', shadow: false });
      ctx.restore();
    }
  }
  // Medicina ↔ Electricidad
  const am = env(t, 24.1, 28.15, .3, .3);
  if (am > 0) {
    ctx.save(); ctx.globalAlpha = am;
    const hk = eOut(A(t, 24.15, 24.6));
    text('ENERGÍA NUCLEAR CIVIL', W / 2, 820, { font: F(900, 54), ls: 4, alpha: hk });
    ctx.fillStyle = RED; ctx.fillRect(W / 2 - 200 * hk, 868, 400 * hk, 7);
    const node = (x, k, icon, l1, l2) => {
      if (k <= 0) return; const s = eBack(k);
      ctx.save(); ctx.translate(x, 1130); ctx.scale(s, s);
      ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 40;
      ctx.fillStyle = 'rgba(10,31,68,.95)'; ctx.beginPath(); ctx.arc(0, 0, 135, 0, 7); ctx.fill(); ctx.shadowBlur = 0;
      ctx.strokeStyle = RED_L; ctx.lineWidth = 8; ctx.beginPath(); ctx.arc(0, 0, 135, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * eOut(k)); ctx.stroke();
      icon(); ctx.restore();
      text(l1, x, 1325, { font: F(900, 50), ls: 2, alpha: k });
      text(l2, x, 1380, { font: F(600, 32), color: ICE, alpha: k });
    };
    node(290, A(t, 24.36, 24.75), () => iconCross(0, 0, 130), 'MEDICINA', 'contra el cáncer');
    // conector "desde... hasta"
    const ck = eIO(A(t, 26.3, 27.0));
    if (ck > 0) {
      ctx.strokeStyle = WHITE; ctx.lineWidth = 6; ctx.setLineDash([16, 14]); ctx.lineDashOffset = -t * 40;
      ctx.beginPath(); ctx.moveTo(440, 1130); ctx.lineTo(lerp(440, 640, ck), 1130); ctx.stroke(); ctx.setLineDash([]);
      if (ck > .9) { ctx.fillStyle = WHITE; ctx.beginPath(); ctx.moveTo(660, 1130); ctx.lineTo(630, 1112); ctx.lineTo(630, 1148); ctx.fill(); }
    }
    node(790, A(t, 27.0, 27.4), () => iconBolt(0, 0, 150, '#FFD23F'), 'ELECTRICIDAD', 'producir energía');
    ctx.restore();
  }
}

// 5 · Moscú / Rosatom [28.1 – 37.6]
function scene5(t) {
  if (t < 28.05 || t > 37.75) return;
  // "Pero hay un detalle"
  const ad = env(t, 28.15, 29.25, .25, .3);
  if (ad > 0) {
    ctx.save(); ctx.globalAlpha = ad;
    const s = eBack(A(t, 28.15, 28.5));
    ctx.save(); ctx.translate(W / 2, 830); ctx.scale(s, s); iconMag(0, 0, 230, 1, 1, WHITE, RED_L); ctx.restore();
    text('UN DETALLE…', W / 2, 1060, { font: F(900, 90), ls: 3 });
    ctx.restore();
  }
  const ag = env(t, 28.95, 37.7, .4, .3);
  if (ag > 0) {
    const rk = eIO(A(t, 28.95, 31.0));
    const rot = rotLerp(ROT_SDDC, ROT_SDMOS, rk), sc = lerp(1050, 345, eIO(A(t, 28.95, 30.6)));
    drawGlobe(W / 2, 900, 345, sc, rot, {
      alpha: ag, rus: eOut(A(t, 33.9, 34.4)), usa: .35 * (1 - rk),
      arcs: [{ from: SD, to: MOS, k: eIO(A(t, 31.2, 33.9)) }],
      pins: [{ ll: SD, label: 'SANTO DOMINGO', k: A(t, 29.2, 29.5), col: RED, dy: 50, bg: RED },
             { ll: MOS, label: 'MOSCÚ', k: A(t, 34.95, 35.3), col: WHITE, dy: -82, dx: -20 }]
    });
    // 2019
    const yk = A(t, 29.8, 30.15);
    if (yk > 0) {
      ctx.save(); ctx.globalAlpha = ag; const s = eBack(yk);
      ctx.translate(W / 2, 1335); ctx.scale(s, s);
      rr(-160, -58, 320, 116, 14); ctx.fillStyle = RED; ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30; ctx.fill(); ctx.shadowBlur = 0;
      text('2019', 0, 4, { font: F(900, 88), ls: 4, shadow: false });
      ctx.restore();
    }
    // rótulo Rosatom
    const rk2 = A(t, 35.75, 36.3);
    if (rk2 > 0) {
      ctx.save(); ctx.globalAlpha = ag;
      const wk = eOut(rk2);
      ctx.beginPath(); ctx.rect(70, 1420, 940 * wk, 220); ctx.clip();
      rr(70, 1430, 940, 110, [14, 14, 0, 0]); ctx.fillStyle = WHITE; ctx.fill();
      ctx.fillStyle = RED; ctx.fillRect(70, 1430, 16, 200);
      text('ROSATOM', 116, 1488, { font: F(900, 70), align: 'left', ls: 4, color: NAVY, shadow: false });
      flagRU(860, 1458, 100, 66);
      rr(70, 1540, 940, 90, [0, 0, 14, 14]); ctx.fillStyle = NAVY; ctx.fill();
      text('Empresa estatal rusa · Acuerdo 2019', 116, 1587, { font: F(700, 38), align: 'left', color: WHITE, shadow: false });
      ctx.restore();
    }
  }
}

// 6 · Pantalla dividida EE. UU. / Rusia [37.6 – 41.2]
function scene6(t) {
  if (t < 37.5 || t > 41.45) return;
  const a = env(t, 37.6, 41.4, .2, .3);
  ctx.save(); ctx.globalAlpha = a;
  ctx.fillStyle = NAVY_D; ctx.fillRect(0, 0, W, H);
  const sl = eOut(A(t, 37.6, 38.05));
  const gap = 8;
  // izquierda: EE. UU.
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W / 2 - gap, H); ctx.clip();
  ctx.translate(-(1 - sl) * W / 2, 0);
  ctx.save(); ctx.translate(-260, -40); ctx.scale(1, 1); wavingFlag('us', 0, 0, 1900, 2000, t, 22); ctx.restore();
  ctx.fillStyle = 'rgba(5,14,34,.5)'; ctx.fillRect(0, 0, W, H);
  ctx.restore();
  // derecha: Rusia
  ctx.save(); ctx.beginPath(); ctx.rect(W / 2 + gap, 0, W / 2 - gap, H); ctx.clip();
  ctx.translate((1 - sl) * W / 2, 0);
  wavingFlag('ru', W / 2 - 40, -40, 640, 2000, t + 1, 22);
  ctx.fillStyle = 'rgba(5,14,34,.5)'; ctx.fillRect(0, 0, W, H);
  ctx.restore();
  // línea divisoria
  ctx.fillStyle = WHITE; ctx.fillRect(W / 2 - 3, 0, 6, H * sl);
  // etiquetas
  text('EE. UU.', W / 4, 610, { font: F(900, 74), ls: 4, alpha: sl });
  text('RUSIA', W * 3 / 4, 610, { font: F(900, 74), ls: 4, alpha: sl });
  const vk = A(t, 37.9, 38.2);
  if (vk > 0) {
    const s = eBack(vk); ctx.save(); ctx.translate(W / 2, 760); ctx.scale(s, s);
    ctx.fillStyle = RED; ctx.beginPath(); ctx.arc(0, 0, 70, 0, 7); ctx.fill(); ctx.strokeStyle = WHITE; ctx.lineWidth = 6; ctx.stroke();
    text('VS', 0, 4, { font: F(900, 60), shadow: false }); ctx.restore();
  }
  // RD en el medio
  const mk = A(t, 38.9, 39.35);
  if (mk > 0) {
    const pulse = 1 + .03 * Math.sin(t * 8);
    ctx.save(); ctx.translate(W / 2, 1120); ctx.scale(eBack(mk) * pulse, eBack(mk) * pulse); ctx.translate(-W / 2, -1120);
    ctx.fillStyle = 'rgba(5,14,34,.75)'; ctx.beginPath(); ctx.ellipse(W / 2, 1120, 470, 270, 0, 0, 7); ctx.fill();
    drawDR(drProj(200, 950, 880, 1290), { fill: RED, stroke: WHITE, sw: 5, haiti: 'rgba(255,255,255,.18)', glow: 'rgba(255,40,60,.95)' });
    ctx.restore();
    text('UN MISMO PAÍS EN EL MEDIO', W / 2, 1470, { font: F(900, 56), ls: 1, alpha: eOut(A(t, 39.2, 39.6)) });
  }
  ctx.restore();
}

// 7 · Aclaración del Gobierno [41.2 – 54.9]
function scene7(t) {
  if (t < 41.1 || t > 55.0) return;
  // "Ojo"
  const ao = env(t, 41.3, 43.15, .25, .3);
  if (ao > 0) {
    ctx.save(); ctx.globalAlpha = ao; const s = eBack(A(t, 41.3, 41.65));
    ctx.save(); ctx.translate(W / 2, 880); ctx.scale(s, s);
    ctx.fillStyle = RED; ctx.beginPath(); ctx.arc(0, 0, 120, 0, 7); ctx.fill(); ctx.strokeStyle = WHITE; ctx.lineWidth = 7; ctx.stroke();
    iconEye(0, 0, 150); ctx.restore();
    text('OJO', W / 2, 1080, { font: F(900, 110), ls: 10 });
    ctx.restore();
  }
  // Tarjeta de cita
  const aq = env(t, 43.2, 49.25, .45, .3);
  if (aq > 0) {
    ctx.save(); ctx.globalAlpha = aq; ctx.translate(0, 50 * (1 - eOut(A(t, 43.2, 43.7))));
    const y0 = 700, h = 470;
    rr(70, y0, 940, h, 22); ctx.fillStyle = 'rgba(247,244,236,.97)'; ctx.shadowColor = 'rgba(0,0,0,.55)'; ctx.shadowBlur = 50; ctx.fill(); ctx.shadowBlur = 0;
    text('“', 118, y0 + 120, { font: 'bold 230px "Liberation Serif", serif', color: RED, align: 'left', shadow: false });
    const lines = ['El acuerdo no implica', 'construir una planta', 'nuclear'];
    lines.forEach((l, i) => { const k = eOut(A(t, 43.45 + i * .25, 43.85 + i * .25)); text(l, 130, y0 + 175 + i * 70, { font: SERIF(62), align: 'left', color: NAVY, shadow: false, alpha: k }); });
    ctx.fillStyle = 'rgba(10,31,68,.15)'; ctx.fillRect(130, y0 + 370, 820, 2);
    ctx.fillStyle = RED; ctx.fillRect(130, y0 + 397, 40, 6);
    text('Ministerio de Energía y Minas', 186, y0 + 400, { font: F(800, 36), align: 'left', color: NAVY, shadow: false });
    text('Gobierno dominicano', 186, y0 + 440, { font: F(600, 26), align: 'left', color: '#55627A', shadow: false });
    ctx.restore();
  }
  // Sello NO HAY PROYECTO APROBADO
  const sk = A(t, 47.42, 47.62);
  if (sk > 0 && t < 49.4) {
    const s = lerp(2.6, 1, eOut(sk)), fo = 1 - A(t, 49.0, 49.3);
    ctx.save(); ctx.globalAlpha = Math.min(1, sk * 2) * fo; ctx.translate(W / 2, 1360); ctx.rotate(-7 * Math.PI / 180); ctx.scale(s, s);
    ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 30;
    rr(-430, -120, 860, 240, 18); ctx.fillStyle = 'rgba(206,17,38,.92)'; ctx.fill(); ctx.shadowBlur = 0;
    ctx.strokeStyle = WHITE; ctx.lineWidth = 7; rr(-410, -100, 820, 200, 12); ctx.stroke();
    text('NO HAY PROYECTO', 0, -32, { font: F(900, 80), ls: 3, shadow: false });
    text('APROBADO', 0, 52, { font: F(900, 80), ls: 14, shadow: false });
    // textura de sello
    ctx.globalCompositeOperation = 'destination-out';
    for (let i = 0; i < 260; i++) { ctx.fillStyle = `rgba(0,0,0,${.25 + hash(i) * .5})`; ctx.beginPath(); ctx.arc((hash(i * 3) - .5) * 860, (hash(i * 7) - .5) * 240, 1 + hash(i * 11) * 5, 0, 7); ctx.fill(); }
    ctx.restore();
  }
  // Borrador de ley: LISTO
  const ab = env(t, 49.3, 54.95, .35, .3);
  if (ab > 0) {
    ctx.save(); ctx.globalAlpha = ab;
    // rótulo nombre / cargo
    const nk = eOut(A(t, 49.6, 50.1));
    ctx.save(); ctx.beginPath(); ctx.rect(60, 560, 960 * nk, 140); ctx.clip();
    rr(60, 570, 840, 74, [12, 12, 0, 0]); ctx.fillStyle = WHITE; ctx.fill();
    text('MINISTERIO DE ENERGÍA Y MINAS', 90, 609, { font: F(900, 40), align: 'left', color: NAVY, ls: 1, shadow: false });
    rr(60, 644, 620, 52, [0, 0, 12, 12]); ctx.fillStyle = RED; ctx.fill();
    text('República Dominicana', 90, 671, { font: F(700, 30), align: 'left', shadow: false });
    ctx.restore();
    // documento
    const dk = A(t, 51.0, 51.4);
    if (dk > 0) {
      const s = eBack(dk); ctx.save(); ctx.translate(W / 2, 1000); ctx.scale(s, s);
      ctx.fillStyle = 'rgba(10,31,68,.92)'; ctx.beginPath(); ctx.arc(0, 0, 175, 0, 7); ctx.fill(); ctx.strokeStyle = 'rgba(255,255,255,.4)'; ctx.lineWidth = 4; ctx.stroke();
      iconDoc(0, 0, 210, A(t, 51.2, 52.4));
      const ck = A(t, 51.56, 51.9);
      if (ck > 0) { ctx.save(); ctx.translate(105, 105); ctx.scale(eBack(ck), eBack(ck)); iconCheck(0, 0, 110, A(t, 51.6, 52.0)); ctx.restore(); }
      ctx.restore();
      const tk = eOut(A(t, 51.95, 52.4));
      ctx.save(); ctx.globalAlpha *= tk;
      const t1 = 'BORRADOR DE LEY:', t2 = 'LISTO';
      text(t1, W / 2, 1270, { font: F(900, 70), ls: 2 });
      const lw = measure(t2, F(900, 96), 10) + 80;
      ctx.save(); ctx.translate(W / 2, 1380); const ps = eBack(A(t, 52.1, 52.5)); ctx.scale(ps, ps);
      rr(-lw / 2, -62, lw, 124, 16); ctx.fillStyle = '#18A34A'; ctx.fill();
      text(t2, 0, 4, { font: F(900, 96), ls: 10, shadow: false }); ctx.restore();
      text('para regular esta tecnología', W / 2, 1500, { font: F(600, 40), color: ICE, alpha: eOut(A(t, 52.9, 53.4)) });
      ctx.restore();
    }
    ctx.restore();
  }
}

// 8 · Pregunta + encuesta [54.9 – 62.9]
function scene8(t) {
  if (t < 54.8 || t > 63.1) return;
  const a = env(t, 54.95, 63.05, .4, .35);
  ctx.save(); ctx.globalAlpha = a;
  ctx.fillStyle = 'rgba(10,31,68,.45)'; ctx.fillRect(0, 0, W, H);
  // mapa de RD tenue con átomo
  ctx.save(); ctx.globalAlpha *= .22 + .05 * Math.sin(t * 2);
  drawDR(drProj(90, 1080, 990, 1500), { fill: RED, stroke: WHITE, sw: 3, haiti: 'rgba(255,255,255,.1)' });
  ctx.restore();
  pill('LA PREGUNTA', W / 2, 640, { alpha: eOut(A(t, 56.05, 56.4)), scale: eBack(A(t, 56.05, 56.4)), font: F(900, 40), ls: 6 });
  const lines = [['¿ACEPTARÍAS', 57.3], ['UNA PLANTA', 57.9], ['NUCLEAR', 58.5], ['EN RD?', 58.78]];
  lines.forEach(([l, s], i) => {
    const k = A(t, s - .05, s + .3);
    if (k <= 0) return;
    const sc = .6 + .4 * eBack(k);
    ctx.save(); ctx.translate(W / 2, 780 + i * 120); ctx.scale(sc, sc);
    text(l, 0, 0, { font: F(900, i === 2 ? 128 : 112), color: i === 2 ? RED_L : WHITE, ls: 2, alpha: k, stroke: 'rgba(5,14,34,.8)', sw: 10 });
    ctx.restore();
  });
  // encuesta
  const ck = A(t, 60.6, 60.95);
  if (ck > 0) {
    ctx.save(); ctx.globalAlpha *= ck; ctx.translate(0, 20 * (1 - eOut(ck)));
    iconBubble(W / 2 - 190, 1305, 64);
    text('COMENTA', W / 2 + 30, 1305, { font: F(900, 54), ls: 6 });
    ctx.restore();
  }
  const btn = (x, k, num, lbl, bg) => {
    if (k <= 0) return; const s = eElastic(k);
    ctx.save(); ctx.translate(x, 1480); ctx.scale(s, s);
    ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 40; rr(-205, -95, 410, 190, 28); ctx.fillStyle = bg; ctx.fill(); ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(255,255,255,.85)'; ctx.lineWidth = 5; ctx.stroke();
    text(num, -110, 4, { font: F(900, 120), shadow: false });
    text('=', -30, 0, { font: F(900, 70), shadow: false, color: 'rgba(255,255,255,.7)' });
    text(lbl, 80, 4, { font: F(900, 96), shadow: false });
    ctx.restore();
  };
  btn(290, A(t, 60.95, 61.6), '1', 'SÍ', NAVY_L);
  btn(790, A(t, 61.95, 62.6), '2', 'NO', RED);
  ctx.restore();
}

// Cierre · Capital Curioso
function outro(t) {
  if (t < 62.85) return;
  const a = A(t, 62.9, 63.25), fo = 1 - A(t, 66.45, 67.0);
  ctx.save(); ctx.globalAlpha = a;
  let g = ctx.createRadialGradient(W / 2, H * .45, 50, W / 2, H * .45, H * .8);
  g.addColorStop(0, '#163A73'); g.addColorStop(1, NAVY_D);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  // franjas bandera
  const fk = eOut(A(t, 63.0, 63.6));
  ctx.fillStyle = RED; ctx.fillRect(0, 0, W * fk, 14); ctx.fillRect(W * (1 - fk), H - 14, W * fk, 14);
  ctx.fillStyle = '#002D62'; ctx.fillRect(W * (1 - fk), 14, W * fk, 10); ctx.fillRect(0, H - 24, W * fk, 10);
  // rayos de luz giratorios
  ctx.save(); ctx.translate(W / 2, 820); ctx.rotate(t * .25); ctx.globalAlpha *= .08 * A(t, 63.4, 64);
  ctx.fillStyle = WHITE; for (let i = 0; i < 12; i++) { ctx.rotate(Math.PI / 6); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(900, -70); ctx.lineTo(900, 70); ctx.fill(); }
  ctx.restore();
  // lupa
  const k = A(t, 63.0, 63.9), q = A(t, 63.75, 64.15);
  const bob = Math.sin((t - 64) * 2.2) * 8 * A(t, 64.2, 64.6);
  ctx.save(); ctx.shadowColor = 'rgba(80,150,255,.6)'; ctx.shadowBlur = 40;
  ctx.translate(W / 2 + 25, 820 + bob); ctx.rotate(-.12 * (1 - eOut(A(t, 63, 64))));
  // lente
  if (q > 0) { ctx.save(); ctx.globalAlpha *= q; ctx.fillStyle = 'rgba(160,200,255,.12)'; ctx.beginPath(); ctx.arc(-34, -34, 145, 0, 7); ctx.fill(); ctx.restore(); }
  iconMag(0, 0, 430, k, q, WHITE, RED_L);
  // destello
  const sh = A(t, 64.2, 64.7);
  if (sh > 0 && sh < 1) { ctx.save(); ctx.beginPath(); ctx.arc(-34, -34, 140, 0, 7); ctx.clip(); ctx.rotate(.6); ctx.fillStyle = 'rgba(255,255,255,.35)'; ctx.fillRect(-300 + sh * 600, -300, 50, 600); ctx.restore(); }
  ctx.restore();
  // textos
  const tk = eOut(A(t, 64.0, 64.45));
  ctx.save(); ctx.beginPath(); ctx.rect(0, 1080, W, 140); ctx.clip();
  text('CAPITAL CURIOSO', W / 2, 1150 + 120 * (1 - tk), { font: F(900, 100), ls: 3 });
  ctx.restore();
  const hk = eOut(A(t, 64.35, 64.8));
  ctx.fillStyle = RED; ctx.fillRect(W / 2 - 260 * hk, 1222, 520 * hk, 8);
  text('@capitalcuriosoo', W / 2, 1300, { font: F(800, 54), color: ICE, alpha: hk, ls: 1 });
  const fl = A(t, 64.8, 65.2);
  if (fl > 0) { flagDR(W / 2 - 60, 1385, 120, 80); ctx.globalAlpha *= fl; }
  text('SÍGUENOS PARA MÁS', W / 2, 1540, { font: F(800, 40), ls: 8, alpha: eOut(A(t, 65.0, 65.4)), color: WHITE });
  ctx.restore();
  if (fo < 1) { ctx.fillStyle = `rgba(0,0,0,${1 - fo})`; ctx.fillRect(0, 0, W, H); }
}

// ============================================================
//  Destellos/oscurecimientos de apagón
// ============================================================
function blackouts(t) {
  let d = 0;
  if (t > 2.78 && t < 3.15) d = Math.max(d, 1 - A(t, 2.86, 3.15));
  if (t > 9.3 && t < 9.7) d = Math.max(d, (1 - A(t, 9.45, 9.7)) * .9);
  if (d > 0) { ctx.fillStyle = `rgba(0,0,0,${d})`; ctx.fillRect(0, 0, W, H); }
  // destello blanco en transiciones clave
  for (const tt of [7.3, 18.0, 28.15, 37.6, 41.2]) {
    const k = A(t, tt - .02, tt + .25); if (k > 0 && k < 1) { ctx.fillStyle = `rgba(255,255,255,${.35 * (1 - k)})`; ctx.fillRect(0, 0, W, H); }
  }
}

// sacudida de cámara (impactos)
function shake(t) {
  let a = 0;
  for (const [tt, amp] of [[2.78, 16], [5.95, 8], [8.15, 8], [37.6, 10], [47.5, 22], [9.26, 12]]) { const k = A(t, tt, tt + .4); if (k > 0 && k < 1) a = Math.max(a, amp * (1 - k)); }
  if (!a) return [0, 0];
  return [(hash(t * 91) - .5) * 2 * a, (hash(t * 57) - .5) * 2 * a];
}

// ============================================================
function render(t) {
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
  const [sx, sy] = shake(t);
  ctx.save(); ctx.translate(sx, sy);
  ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(1.02, 1.02); ctx.translate(-W / 2, -H / 2);
  drawBackground(t);
  ctx.restore();
  grade(t);
  scene1(t); scene2(t); scene3(t); scene4(t); scene5(t); scene6(t); scene7(t); scene8(t);
  ctx.restore();
  blackouts(t);
  outro(t);
  if (t < 62.9) { subtitles(t); brandChip(t, A(t, .3, .8) * (1 - A(t, 62.6, 62.9))); }
  grain(t);
}

window.READY = (async () => {
  await document.fonts.load(F(900, 40)); await document.fonts.load(F(800, 40)); await document.fonts.load(F(700, 40)); await document.fonts.load(F(600, 40)); await document.fonts.load(SERIF(40));
  await loadAll(); makeGrain(); render(0); return true;
})();
window.render = render; window.DUR = DUR;
