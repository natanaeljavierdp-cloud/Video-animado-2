// =====================================================================
//  EPISODIO 1 — "Cómo empezaron Los Morenos Chocolate"
//  Director: posiciones, gestos, cámara, subtítulos y títulos.
//  Necesita: motor.js (window.M) y window.TL (timeline_ep1.json)
// =====================================================================
/* global window */
(function () {
  const M = window.M;
  const { lerp, clamp, smooth, ease, win } = M;

  const CAST = [
    { id: 'mik', file: '01-mikibiry.svg', name: 'MIKIBIRY', num: 1, color: '#4FC3F7', home: [150, 1610], chair: '#F4F4F4', prop: 'celular' },
    { id: 'bol', file: '02-el-bolen.svg', name: 'EL BOLEN', num: 2, color: '#FF8A65', home: [690, 1640], chair: '#E2574C', prop: 'libreta' },
    { id: 'dp', file: '03-doble-p.svg', name: 'DOBLE P', num: 3, color: '#EF5350', home: [870, 1610], chair: '#F4F4F4', prop: 'libreta' },
    { id: 'dob', file: '04-el-doblon.svg', name: 'EL DOBLÓN', num: 4, color: '#EDE7F6', home: [1050, 1640], chair: '#3F7FD6', prop: 'libreta' },
    { id: 'mar', file: '05-marino-el-epc.svg', name: 'MARINO EL EPC', num: 5, color: '#81C784', home: [510, 1610], chair: '#F4F4F4', prop: 'celular' },
    { id: 'sic', file: '06-el-sicario.svg', name: 'EL SICARIO', num: 6, color: '#B0BEC5', home: [330, 1640], chair: '#E2574C', prop: 'celular' },
    { id: 'nj', file: '07-el-nj.svg', name: 'EL NJ', num: 7, color: '#FFD54F', home: [1230, 1610], chair: '#3F7FD6', prop: 'libreta' },
  ];
  const BY = {}; CAST.forEach((c, i) => { c.idx = i; BY[c.id] = c; });
  const WHO = { 'MIKIBIRY': 'mik', 'EL BOLEN': 'bol', 'DOBLE P': 'dp', 'EL DOBLÓN': 'dob', 'MARINO EL EPC': 'mar', 'EL SICARIO': 'sic', 'EL NJ': 'nj' };
  const CLIPWHO = { '08_mikv_a': 'mik', '09_bolv_a': 'bol', '10_mard_a': 'mar', '11_dpd_a': 'dp', 'L_mar_a': 'mar', 'L_mik_a': 'mik', 'L_nj_a': 'nj', 'L_bol_a': 'bol', 'L_mar_b': 'mar', 'L_mik_b': 'mik', 'L_nj_b': 'nj', 'L_bol_b': 'bol' };
  const COLOR_WHO = { NARRADOR: '#F5C542', TODOS: '#FFFFFF' };
  CAST.forEach((c) => { COLOR_WHO[c.name] = c.color; });

  const E = { CAST };
  window.EP = E;

  let TL, T, cues;
  E.setup = function () {
    TL = window.TL; T = TL.total; cues = TL.cues;
    cues.forEach((q) => { q.char = WHO[q.who] || CLIPWHO[q.clip] || null; });
    buildActions();
    buildCamera();
  };

  // ------------------------------------------------------------ llegada
  const SPEED = 215;
  const ARR = {
    bol: { t0: 0.4, from: [1950, 1250] },
    sic: { t0: 1.4, from: [-480, 1640] },
    mar: { t0: 0.2, from: [510, 2780] },
    dp: { t0: 0.1, from: [2180, 1610] },
    dob: { t0: 0.9, from: [1560, 2780] },
    nj: { t0: 2.0, from: [2150, 1290] },
  };
  for (const k in ARR) {
    const a = ARR[k], h = BY[k].home;
    a.t1 = a.t0 + Math.hypot(h[0] - a.from[0], h[1] - a.from[1]) / SPEED;
  }
  // Mikibiry llega en motor
  const MOTO = { y: 2050, x0: -1000, x1: 300, t1: 5.3, off: 5.5, hop: 5.9 };
  const motoX = (t) => lerp(MOTO.x0, MOTO.x1, 1 - Math.pow(1 - clamp(t / MOTO.t1, 0, 1), 2.2));
  const MIK_FOOT = [MOTO.x1 + 95, MOTO.y - 4];
  const MIK_WALK = { t0: MOTO.hop, from: MIK_FOOT };
  MIK_WALK.t1 = MIK_WALK.t0 + Math.hypot(BY.mik.home[0] - MIK_FOOT[0], BY.mik.home[1] - MIK_FOOT[1]) / SPEED;

  // ------------------------------------------------------------ acciones
  const G = {}; // gestos por personaje: {t0,t1,r, armL, armR, head, lean, shake, cross, laugh, nod}
  CAST.forEach((c) => { G[c.id] = []; });
  const add = (id, o) => G[id].push(Object.assign({ r: 0.25 }, o));

  function buildActions() {
    const cs = TL.cards_start, cl = TL.card_len;
    // presentación: cada uno hace su gesto
    const cardG = {
      mik: { armR: -140, shake: 1 }, bol: { armL: 45, armR: -45, shake: 1 }, dp: { armL: 150, armR: -150 },
      dob: { nod: 1 }, mar: { laugh: 0.8 }, sic: { cross: 1 }, nj: { armL: 130, armR: -130, shake: 1 },
    };
    CAST.forEach((c, i) => add(c.id, Object.assign({ t0: cs + i * cl + 0.1, t1: cs + (i + 1) * cl - 0.05, r: 0.2 }, cardG[c.id])));

    const q = (who, n = 0) => cues.filter((x) => x.who === who)[n];
    const argEnd = TL.dp_start + 0.15;
    // discusión: todos encima de todos, señalándose
    add('mik', { t0: q('MIKIBIRY').start - 0.2, t1: argEnd, armR: -95, head: 6, lean: 3, shake: 1 });
    add('sic', { t0: q('EL SICARIO').start - 0.3, t1: argEnd, armL: 95, head: -6, lean: -3, shake: 1 });
    add('mar', { t0: q('MARINO EL EPC').start - 0.2, t1: argEnd, armL: 55, armR: -55, shake: 2, headShake: 1 });
    add('nj', { t0: q('EL NJ').start - 0.2, t1: argEnd, armL: 92, head: -7, lean: -3, shake: 1.2 });
    add('bol', { t0: q('MIKIBIRY').start + 0.5, t1: argEnd, armL: 40, armR: -60, shake: 2.2 });
    add('dp', { t0: q('MIKIBIRY').start + 0.9, t1: argEnd - 0.1, armL: 70, armR: -30, shake: 1.6 });
    add('dob', { t0: q('MIKIBIRY').start + 1.2, t1: argEnd, armL: 25, armR: -25, headShake: 0.6 });
    // Doble P: "¡Hagan silencio!" — levanta las manos, todos se callan
    add('dp', { t0: TL.dp_start, t1: TL.dp_start + 2.0, armL: 160, armR: -160, r: 0.18, shake: 0.4 });
    // "Sabemo' que fue El Bolen": Doble P lo señala y todos lo miran
    const rv = TL.bolen_reveal;
    const bolX = BY.bol.home[0];
    add('dp', { t0: rv - 0.1, t1: rv + 3.2, armL: 100, head: -8, lean: -3, r: 0.3 });
    CAST.forEach((c) => {
      if (c.id === 'bol' || c.id === 'dp') return;
      const s = Math.sign(bolX - c.home[0]);
      add(c.id, { t0: rv + 0.15 + c.idx * 0.06, t1: q('EL BOLEN').start + 0.6, head: 9 * s, lean: 3 * s, r: 0.35 });
    });
    add('bol', { t0: rv + 0.3, t1: q('EL BOLEN').start, head: 0, lean: 0, armL: 15, armR: -15, r: 0.3 });
    // El Bolen manotea
    const b = q('EL BOLEN');
    add('bol', { t0: b.start - 0.1, t1: b.end + 0.2, armL: 70, armR: -70, shake: 4.5, headShake: 1.2 });
    // El Doblón calmado, palmas abiertas
    const d1 = q('EL DOBLÓN');
    add('dob', { t0: d1.start, t1: d1.end, armL: 30, armR: -30, shake: 0.5 });
    // "Sí, e' verdá" — todos asienten / "¡Vamo' a darle!" — puños arriba
    const v = q('TODOS', 0), dl = q('TODOS', 1);
    CAST.forEach((c) => add(c.id, { t0: v.start, t1: v.end + 0.3, nod: 1 }));
    ['mar', 'dp', 'nj', 'mik', 'bol'].forEach((id, k) => add(id, { t0: dl.start - 0.05 + k * 0.05, t1: dl.end + 0.35, armR: -150, shake: 0.8, r: 0.15 }));
    // El NJ conciliador: brazos abiertos
    const n2 = q('EL NJ', 1);
    add('nj', { t0: n2.start, t1: n2.end, armL: 55, armR: -55, shake: 0.6 });
    // El Sicario serio
    const s2 = q('EL SICARIO', 1);
    add('sic', { t0: s2.start + 2.2, t1: s2.end, armR: -60, shake: 0.4 });
    // risas
    const l1 = TL.laugh1, l2 = TL.laugh2;
    CAST.forEach((c) => {
      if (c.id === 'sic') return;
      add(c.id, { t0: l1 - 0.05 + c.idx * 0.05, t1: l1 + 3.6, laugh: 0.8, r: 0.3 });
      add(c.id, { t0: l2 - 0.1 + c.idx * 0.05, t1: l2 + 5.3, laugh: 1.25, r: 0.35 });
    });
    // Marino muerto de risa señalando al Sicario
    const m2 = q('MARINO EL EPC', 1);
    add('mar', { t0: m2.start, t1: m2.end, laugh: 0.6, armL: 92, shake: 1.0 });
    // El Sicario serio con los brazos cruzados
    add('sic', { t0: l1 + 0.4, t1: l1 + 2.6, head: -4 });
    add('sic', { t0: l2 - 0.4, t1: TL.dob2_end + 0.8, cross: 1, head: -3, r: 0.4 });
    // El Doblón final
    const d2 = q('EL DOBLÓN', 1);
    add('dob', { t0: d2.start, t1: d2.end, armL: 30, armR: -35, shake: 0.6 });
    // todos asienten
    CAST.forEach((c) => add(c.id, { t0: d2.end + 0.1 + c.idx * 0.07, t1: d2.end + 1.6, nod: 1 }));
  }

  // ------------------------------------------------------------ voz -> animación
  function speech(id, t) {
    let e = 0;
    for (const q of cues) {
      if (q.char !== id || t < q.start || t >= q.end) continue;
      const k = Math.floor((t - q.start) * 30);
      e = Math.max(e, q.env[k] || 0);
    }
    return e;
  }
  function speakingNow(id, t) {
    return cues.some((q) => q.char === id && q.who !== 'RISAS' && t >= q.start && t < q.end);
  }

  // ------------------------------------------------------------ pose
  const SIT_T = () => TL.dob2_end + 1.75;

  E.pose = function (c, t) {
    const i = c.idx;
    const [hx, hy] = c.home;
    const P = { x: hx, y: hy, bob: 0, lean: 0, head: 0, headDX: 0, headDY: 0, armL: 0, armR: 0, legL: 0, legR: 0, sit: 0, cross: 0 };
    // llegada
    let walking = false, wt = 0;
    if (c.id === 'mik') {
      if (t < MOTO.off) {
        P.x = motoX(t) - 60; P.y = MOTO.y - 84; P.sit = 1; P.armR = -62; P.armL = -10; P.riding = true;
        P.bob = Math.sin(t * 40) * 1.5;
      } else if (t < MOTO.hop) {
        const k = smooth((t - MOTO.off) / (MOTO.hop - MOTO.off));
        P.x = lerp(MOTO.x1 - 60, MIK_FOOT[0], k); P.y = lerp(MOTO.y - 84, MIK_FOOT[1], k);
        P.sit = 1 - k; P.bob = -Math.sin(k * Math.PI) * 60;
      } else if (t < MIK_WALK.t1) {
        const k = (t - MIK_WALK.t0) / (MIK_WALK.t1 - MIK_WALK.t0);
        P.x = lerp(MIK_FOOT[0], hx, k); P.y = lerp(MIK_FOOT[1], hy, k); walking = true; wt = t - MIK_WALK.t0;
      }
    } else {
      const a = ARR[c.id];
      if (t < a.t1) {
        const k = clamp((t - a.t0) / (a.t1 - a.t0), 0, 1);
        P.x = lerp(a.from[0], hx, k); P.y = lerp(a.from[1], hy, k);
        walking = t > a.t0; wt = t - a.t0;
      }
    }
    if (walking) {
      const ph = wt * 8.5 + i;
      P.legL = 16 * Math.sin(ph); P.legR = 16 * Math.sin(ph);
      P.armL = 10 * Math.sin(ph); P.armR = 10 * Math.sin(ph);
      P.bob = -Math.abs(Math.cos(ph)) * 14; P.head = Math.sin(ph) * 2;
    }
    // respiración y vida
    if (!P.riding) {
      P.bob += Math.sin(t * 2.1 + i * 1.3) * 3;
      P.head += Math.sin(t * 0.8 + i * 1.7) * 1.6;
      P.armL += Math.sin(t * 1.1 + i) * 2; P.armR -= Math.sin(t * 1.3 + i * 2) * 2;
    }
    // gestos
    for (const g of G[c.id]) {
      const w = win(t, g.t0, g.t1, g.r);
      if (w <= 0) continue;
      const sh = (g.shake || 0) * 7;
      if (g.armL !== undefined) P.armL = lerp(P.armL, g.armL + Math.sin(t * 13 + i) * sh, w);
      if (g.armR !== undefined) P.armR = lerp(P.armR, g.armR + Math.sin(t * 11.5 + i * 2) * sh, w);
      if (g.armL === undefined && g.armR === undefined && sh) { P.armL += Math.sin(t * 9) * sh * w; P.armR -= Math.sin(t * 8) * sh * w; }
      if (g.head !== undefined) P.head = lerp(P.head, g.head, w);
      if (g.lean !== undefined) P.lean = lerp(P.lean, g.lean, w);
      if (g.headShake) P.head += Math.sin(t * 15) * 6 * g.headShake * w;
      if (g.cross) P.cross = Math.max(P.cross, g.cross * w);
      if (g.nod) P.headDY += Math.max(0, Math.sin((t - g.t0) * 10)) * 12 * w;
      if (g.laugh) {
        const L = g.laugh * w;
        P.bob -= Math.abs(Math.sin(t * 17 + i)) * 12 * L;
        P.head += Math.sin(t * 8.5 + i) * 7 * L;
        P.headDY -= Math.abs(Math.sin(t * 17 + i)) * 6 * L;
        P.lean += Math.sin(t * 4 + i) * 3 * L;
        if (g.armL === undefined) P.armL = lerp(P.armL, -22 + Math.sin(t * 17) * 6, Math.min(1, L));
        if (g.armR === undefined) P.armR = lerp(P.armR, 22 - Math.sin(t * 17) * 6, Math.min(1, L));
      }
    }
    // hablar: la cabeza y los brazos siguen la voz
    const e = speech(c.id, t);
    if (e > 0.02) {
      const tw = speakingNow(c.id, t) ? 1 : 0.4;
      P.head += Math.sin(t * 7.3 + i) * 5 * e * tw;
      P.headDY -= e * 7 * tw;
      P.bob -= e * 4 * tw;
      P.armL += e * (12 * Math.sin(t * 4.3 + i) + 8) * tw;
      P.armR -= e * (12 * Math.sin(t * 3.7 + i * 2) + 8) * tw;
    }
    // sentarse y escribir
    const st = SIT_T() + i * 0.12;
    if (t > st) {
      const k = smooth((t - st) / 0.9);
      P.sit = k;
      P.cross *= 1 - k;
      P.armL = lerp(P.armL, -24 + Math.sin(t * 2 + i) * 2, k);
      P.armR = lerp(P.armR, 24 - Math.sin(t * 2.3 + i) * 2, k);
      P.head = lerp(P.head, 4 * Math.sin(t * 1.2 + i), k);
      P.headDY += 6 * k;
      if (k > 0.6) { P.prop = c.prop; P.propT = t + i; }
    }
    return P;
  };

  // ------------------------------------------------------------ cámara
  let SHOTS = [];
  function buildCamera() {
    const q = (who, n = 0) => cues.filter((x) => x.who === who)[n];
    const C = (id, z, dy = -300, dx = 0) => ({ x: BY[id].home[0] + dx, y: BY[id].home[1] + dy, z });
    const GROUP = (z = 0.95) => ({ x: 690, y: 1420, z });
    const S = [];
    const shot = (t0, from, to, shake = 0, easing = 'ease') => S.push({ t0, from, to, shake, easing });
    shot(0, { x: 860, y: 1260, z: 0.56 }, { x: 700, y: 1400, z: 0.8 }, 0, 'ease');
    const cs = TL.cards_start, cl = TL.card_len;
    CAST.forEach((c, i) => shot(cs + i * cl, C(c.id, 2.55, -315), C(c.id, 2.75, -320), 0, 'linear'));
    const mik = q('MIKIBIRY'), mar = q('MARINO EL EPC'), nj = q('EL NJ');
    shot(cs + 7 * cl, { x: 245, y: 1420, z: 1.45 }, { x: 245, y: 1410, z: 1.6 }, 1.2, 'linear');
    shot(mar.start, C('mar', 1.9, -270), C('mar', 2.05, -275), 1.4, 'linear');
    shot(nj.start, GROUP(1.0), GROUP(1.06), 1.4, 'linear');
    shot(TL.dp_start, { x: 870, y: 1400, z: 1.2 }, C('dp', 2.4, -290), 0, 'ease');
    shot(TL.dp_start + 2.2, C('dp', 2.4, -290), C('dp', 2.6, -300), 0, 'linear');
    shot(TL.bolen_reveal, GROUP(0.98), { x: 690, y: 1400, z: 1.35 }, 0, 'ease');
    const b = q('EL BOLEN');
    shot(b.start - 0.15, C('bol', 2.5, -300), C('bol', 2.9, -310), 2.2, 'linear');
    const d1 = q('EL DOBLÓN');
    shot(d1.start - 0.2, C('dob', 2.0, -280), C('dob', 2.5, -300), 0, 'ease');
    const v = q('TODOS', 0);
    shot(v.start - 0.1, GROUP(0.98), GROUP(1.08), 0.6, 'linear');
    const n2 = q('EL NJ', 1);
    shot(n2.start - 0.2, C('nj', 2.1, -290, -30), C('nj', 2.5, -300, -30), 0, 'ease');
    const s2 = q('EL SICARIO', 1);
    shot(s2.start - 0.2, C('sic', 2.2, -290), C('sic', 2.95, -310), 0, 'ease');
    shot(TL.laugh1, GROUP(0.98), GROUP(1.04), 1.6, 'linear');
    const m2 = q('MARINO EL EPC', 1);
    shot(m2.start - 0.1, C('mar', 2.1, -290, -40), C('mar', 2.4, -300, -60), 0.6, 'ease');
    shot(TL.laugh2, GROUP(1.0), { x: 600, y: 1410, z: 1.12 }, 1.6, 'linear');
    shot(TL.laugh2 + 2.3, C('sic', 2.3, -280), C('sic', 2.5, -290), 0, 'linear');
    const d2 = q('EL DOBLÓN', 1);
    shot(d2.start, C('dob', 2.1, -285), C('dob', 2.45, -300), 0, 'ease');
    shot(d2.end + 0.05, GROUP(0.98), GROUP(1.0), 0, 'linear');
    shot(SIT_T() + 0.2, GROUP(1.0), { x: 690, y: 1470, z: 1.25 }, 0, 'ease');
    shot(SIT_T() + 2.6, { x: 690, y: 1470, z: 1.25 }, { x: 800, y: 1290, z: 0.62 }, 0, 'ease');
    S.forEach((s, k) => { s.t1 = k + 1 < S.length ? S[k + 1].t0 : T; });
    SHOTS = S;
  }

  E.camera = function (t) {
    let s = SHOTS[0];
    for (const x of SHOTS) if (t >= x.t0) s = x;
    const k0 = (t - s.t0) / (s.t1 - s.t0);
    const k = s.easing === 'ease' ? ease(Math.min(1, k0 * 1.15)) : clamp(k0, 0, 1);
    const cam = { x: lerp(s.from.x, s.to.x, k), y: lerp(s.from.y, s.to.y, k), z: lerp(s.from.z, s.to.z, k) };
    // cámara en mano muy suave + sacudida
    const hs = 1.5 + s.shake * 5;
    cam.x += (Math.sin(t * 0.9) * 0.6 + Math.sin(t * 2.3) * 0.4) * hs / cam.z;
    cam.y += (Math.sin(t * 1.1 + 1) * 0.6 + Math.sin(t * 2.9) * 0.4) * hs / cam.z;
    return cam;
  };

  // ------------------------------------------------------------ cuadro
  E.render = function (ctx, t) {
    const cam = E.camera(t);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#9CCBEA'; ctx.fillRect(0, 0, M.W, M.H);
    ctx.setTransform(cam.z, 0, 0, cam.z, M.W / 2 - cam.x * cam.z, M.H / 2 - cam.y * cam.z);
    M.drawBackground(ctx, t);
    M.drawCanopy(ctx, t);
    // objetos con profundidad: personajes, motores parqueados
    const items = [];
    items.push({ y: 1575, f: () => M.drawMoto(ctx, -330, 1575, false, '#1E5AA8') });
    items.push({ y: 1590, f: () => M.drawMoto(ctx, 1560, 1590, true, '#C62828') });
    items.push({ y: 1505, f: () => M.drawMoto(ctx, 1380, 1505, true, '#2E7D32') });
    const mx = motoX(t);
    items.push({ y: MOTO.y, f: () => M.drawMoto(ctx, mx, MOTO.y, false, '#F9A825', t, t < MOTO.t1 + 0.2) });
    for (const c of CAST) {
      // silla plástica detrás de cada uno, en su puesto bajo el árbol
      items.push({ y: c.home[1] - 0.5, f: () => { ctx.save(); ctx.translate(c.home[0], c.home[1]); ctx.scale(M.S, M.S); ctx.translate(-200, -760); M.drawChairVB(ctx, c.chair); ctx.restore(); } });
      const P = E.pose(c, t);
      items.push({ y: P.riding ? MOTO.y - 1 : P.y, f: () => M.drawCharacter(ctx, c.ch, P) });
    }
    items.sort((a, b) => a.y - b.y).forEach((it) => it.f());
    // ---- capa de pantalla
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const vg = ctx.createRadialGradient(540, 900, 600, 540, 960, 1250);
    vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(10,5,0,0.35)');
    ctx.fillStyle = vg; ctx.fillRect(0, 0, M.W, M.H);
    drawCards(ctx, t);
    drawSubs(ctx, t);
    drawTitle(ctx, t);
    // fundido de entrada
    if (t < 0.8) { ctx.fillStyle = `rgba(0,0,0,${1 - t / 0.8})`; ctx.fillRect(0, 0, M.W, M.H); }
  };

  function drawSubs(ctx, t) {
    let best = null;
    for (const q of cues) if (q.sub && t >= q.start - 0.05 && t <= q.end + 0.3) if (!best || q.start > best.start) best = q;
    if (!best) return;
    const k = clamp((t - best.start + 0.05) / 0.18, 0, 1) * clamp((best.end + 0.3 - t) / 0.15, 0, 1);
    M.drawSubtitle(ctx, best.who, COLOR_WHO[best.who] || '#fff', best.text, k);
  }

  function drawCards(ctx, t) {
    const cs = TL.cards_start, cl = TL.card_len;
    const i = Math.floor((t - cs) / cl);
    if (t < cs || i > 6) return;
    const c = CAST[i];
    const k = (t - cs - i * cl) / cl;
    const a = smooth(k / 0.15) * smooth((1 - k) / 0.12);
    const slide = (1 - ease(Math.min(1, k / 0.25))) * -700;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.translate(slide, 0);
    ctx.fillStyle = 'rgba(40,22,12,0.85)';
    M.rr(ctx, -40, 1380, 960, 300, 40); ctx.fill();
    ctx.fillStyle = c.color; ctx.fillRect(-40, 1380, 28 + 40, 300);
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.font = '900 70px Inter'; ctx.fillStyle = '#F5C542';
    ctx.fillText('#' + c.num, 70, 1450);
    ctx.font = c.name.length > 10 ? '900 100px Inter' : '900 124px Inter';
    ctx.lineWidth = 12; ctx.strokeStyle = '#000'; ctx.lineJoin = 'round';
    ctx.strokeText(c.name, 70, 1570); ctx.fillStyle = '#FFFFFF'; ctx.fillText(c.name, 70, 1570);
    ctx.restore();
  }

  function drawTitle(ctx, t) {
    const t0 = T - 3.9;
    if (t < t0) return;
    const k = smooth((t - t0) / 1.0);
    ctx.save();
    ctx.fillStyle = `rgba(30,16,8,${0.72 * k})`; ctx.fillRect(0, 0, M.W, M.H);
    const s = 0.85 + 0.15 * ease(Math.min(1, (t - t0) / 1.2));
    ctx.translate(540, 900); ctx.scale(s, s);
    ctx.globalAlpha = k;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    ctx.font = '900 150px Inter';
    const fit = Math.min(1, 960 / ctx.measureText('LOS MORENOS').width);
    ctx.font = `900 ${Math.floor(150 * fit)}px Inter`;
    for (const [txt, y] of [['LOS MORENOS', -110], ['CHOCOLATE', 45]]) {
      ctx.lineWidth = 22; ctx.strokeStyle = '#3B2414'; ctx.strokeText(txt, 0, y);
      ctx.fillStyle = '#F5C542'; ctx.fillText(txt, 0, y);
    }
    ctx.font = '800 76px Inter';
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText('– Episodio 1 –', 0, 210);
    ctx.restore();
    if (t > T - 0.9) { ctx.fillStyle = `rgba(0,0,0,${(t - (T - 0.9)) / 0.9})`; ctx.fillRect(0, 0, M.W, M.H); }
  }
})();
