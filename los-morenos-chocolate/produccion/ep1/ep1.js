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
    M.C.init();
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

  // ------------------------------------------------------------ cámara (lenguaje de cine)
  let SHOTS = [];
  const V = (x, y, z, o = {}) => Object.assign({ x, y, z, f: 1.5, rot: 0, focus: 0 }, o);
  function buildCamera() {
    const q = (who, n = 0) => cues.filter((x) => x.who === who)[n];
    const H = (id) => BY[id].home;
    const S = [];
    const shot = (t0, from, to, o = {}) => S.push(Object.assign({ t0, from, to, easing: 'ease', shake: 0, dof: 1, fg: [], rays: 0.5, whip: false, dark: false }, o));
    // 1. grúa bajando desde las flores del árbol hasta el cruce
    shot(0, V(520, 380, 1.25, { f: 0.9 }), V(720, 1330, 0.66, { f: 0.9 }), { dof: 0.25, fg: [{ type: 'branches' }, { type: 'petals' }], rays: 1 });
    // 2. travelling lateral mientras van llegando
    shot(4.4, V(640, 1380, 0.68, { f: 1.0 }), V(820, 1420, 0.8, { f: 1.0 }), { easing: 'linear', dof: 0.35, rays: 0.8, fg: [{ type: 'petals' }] });
    // 3. presentación: primeros planos con tele y travelling lateral (barrido entre cada uno)
    const cs = TL.cards_start, cl = TL.card_len;
    CAST.forEach((c, i) => {
      const d = i % 2 ? 1 : -1, [hx, hy] = c.home;
      shot(cs + i * cl, V(hx + 35 * d, hy - 312, 2.5, { f: 2.6, rot: d * 1.5 }), V(hx - 35 * d, hy - 318, 2.7, { f: 2.6, rot: -d * 0.5 }),
        { easing: 'linear', whip: i > 0, dof: 1.1, rays: 0.4 });
    });
    // 4. la pelea: cámara en mano, planos holandeses, sobre el hombro, barridos
    const mik = q('MIKIBIRY'), sic = q('EL SICARIO'), mar = q('MARINO EL EPC'), nj = q('EL NJ');
    shot(cs + 7 * cl, V(150, 1330, 2.3, { f: 2.2, rot: -3 }), V(165, 1320, 2.5, { f: 2.2, rot: -4.5 }), { easing: 'linear', shake: 1.6, whip: true, fg: [{ type: 'ots', id: 'sic', side: 'R' }] });
    shot(sic.start, V(330, 1330, 2.3, { f: 2.2, rot: 3 }), V(320, 1320, 2.5, { f: 2.2, rot: 4.5 }), { easing: 'linear', shake: 1.6, whip: true, fg: [{ type: 'ots', id: 'mik', side: 'L' }] });
    shot(mar.start, V(510, 1360, 1.9, { f: 1.2, rot: -5 }), V(510, 1340, 2.4, { f: 1.2, rot: -3 }), { easing: 'linear', shake: 2.2, whip: true });
    shot(nj.start, V(700, 1430, 1.0, { f: 1.0, rot: 2.5 }), V(700, 1420, 1.1, { f: 1.0, rot: -2 }), { easing: 'linear', shake: 2.2, whip: true, dof: 0.6 });
    // 5. Doble P: zoom brusco "¡Hagan silencio!" y empuje lento
    shot(TL.dp_start, V(870, 1430, 1.25, { f: 1.4 }), V(870, 1305, 2.6, { f: 1.9 }), { easing: 'snap', rays: 0.3 });
    shot(TL.dp_start + 2.2, V(870, 1300, 2.6, { f: 2.2 }), V(870, 1288, 3.05, { f: 2.4 }), { easing: 'linear', dof: 1.2, rays: 0.3 });
    // 6. "Sabemo' que fue El Bolen": efecto vértigo (dolly zoom) sobre El Bolen
    shot(TL.bolen_reveal, V(690, 1350, 1.45, { f: 0.75 }), V(690, 1325, 1.7, { f: 3.4 }), { easing: 'ease', dof: 0.9, rays: 0.2 });
    // 7. El Bolen: zoom brusco cómico
    const b = q('EL BOLEN');
    shot(b.start - 0.15, V(690, 1330, 1.8, { f: 2.0 }), V(690, 1298, 3.1, { f: 2.4, rot: -2 }), { easing: 'snap', shake: 2.6 });
    // 8. El Doblón, calmado: sobre el hombro de Doble P
    const d1 = q('EL DOBLÓN');
    shot(d1.start - 0.2, V(1040, 1325, 2.2, { f: 2.6 }), V(1035, 1310, 2.6, { f: 2.6 }), { dof: 1.2, rays: 0.7, fg: [{ type: 'ots', id: 'dp', side: 'L' }, { type: 'petals' }] });
    // 9. "Sí, e' verdá" / "¡Vamo' a darle!": grupo, pequeña grúa
    const v = q('TODOS', 0);
    shot(v.start - 0.1, V(690, 1500, 1.0, { f: 1.0 }), V(690, 1430, 1.1, { f: 1.0 }), { dof: 0.6, rays: 0.8, whip: true });
    // 10. El NJ conciliador: sobre el hombro de El Doblón
    const n2 = q('EL NJ', 1);
    shot(n2.start - 0.2, V(1225, 1325, 2.2, { f: 2.4 }), V(1215, 1310, 2.5, { f: 2.4 }), { dof: 1.2, rays: 0.5, fg: [{ type: 'ots', id: 'dob', side: 'L' }] });
    // 11. El Sicario: empuje lento, tele, oscuro
    const s2 = q('EL SICARIO', 1);
    shot(s2.start - 0.2, V(330, 1325, 2.2, { f: 3.0 }), V(330, 1292, 3.25, { f: 3.0 }), { dof: 1.4, rays: 0, dark: true });
    // 12. risas: barrido al grupo
    shot(TL.laugh1, V(690, 1430, 1.0, { f: 1.1, rot: 1.5 }), V(690, 1425, 1.07, { f: 1.1, rot: -1.5 }), { easing: 'linear', shake: 2.2, whip: true, dof: 0.6, rays: 0.8 });
    // 13. Marino burlándose del Sicario
    const m2 = q('MARINO EL EPC', 1);
    shot(m2.start - 0.1, V(450, 1345, 2.0, { f: 1.8 }), V(430, 1330, 2.25, { f: 1.8 }), { dof: 1.0, rays: 0.5, whip: true, fg: [{ type: 'petals' }] });
    // 14. risas más duras, y el Sicario serio (golpe cómico)
    shot(TL.laugh2, V(690, 1440, 1.0, { f: 1.0, rot: -2 }), V(640, 1430, 1.15, { f: 1.0, rot: 2 }), { easing: 'linear', shake: 2.2, dof: 0.6, rays: 0.8 });
    shot(TL.laugh2 + 2.3, V(330, 1312, 2.4, { f: 2.6 }), V(330, 1300, 2.9, { f: 2.6 }), { easing: 'linear', dof: 1.3, dark: true, rays: 0 });
    // 15. El Doblón cierra: sobre el hombro de El NJ
    const d2 = q('EL DOBLÓN', 1);
    shot(d2.start, V(1050, 1325, 2.25, { f: 2.5 }), V(1045, 1310, 2.6, { f: 2.5 }), { dof: 1.2, rays: 0.6, whip: true, fg: [{ type: 'ots', id: 'nj', side: 'R' }] });
    shot(d2.end + 0.05, V(690, 1450, 1.05, { f: 1.3 }), V(690, 1445, 1.12, { f: 1.3 }), { easing: 'linear', dof: 0.7, rays: 0.7 });
    // 16. travelling por el grupo sentado escribiendo
    shot(SIT_T() + 0.6, V(260, 1480, 1.65, { f: 1.6 }), V(1120, 1480, 1.65, { f: 1.6 }), { easing: 'linear', dof: 1.0, rays: 0.6, fg: [{ type: 'petals' }] });
    // 17. grúa subiendo y alejándose entre las ramas: título
    shot(SIT_T() + 3.4, V(800, 1440, 1.1, { f: 1.0 }), V(740, 820, 0.56, { f: 0.9 }), { dof: 0.35, rays: 1, fg: [{ type: 'branches' }, { type: 'petals' }] });
    S.forEach((s, k) => { s.t1 = k + 1 < S.length ? S[k + 1].t0 : T; s.prev = S[k - 1]; });
    SHOTS = S;
    // motores que pasan por la calle de atrás (coinciden con el sonido)
    M.backMotos = [
      { t0: 1.0, len: 7, dir: 1, color: '#C62828', shirt: '#1565C0' }, { t0: 17.5, len: 6.5, dir: -1, color: '#263238', shirt: '#F9A825' },
      { t0: 38.5, len: 7, dir: 1, color: '#1E5AA8', shirt: '#EF6C00' }, { t0: 55.5, len: 6, dir: -1, color: '#2E7D32', shirt: '#ECEFF1' },
      { t0: 66.5, len: 7, dir: 1, color: '#6A1B9A', shirt: '#8D6E63' }, { t0: T - 10.5, len: 7, dir: -1, color: '#C62828', shirt: '#26A69A' },
    ];
  }

  function shotAt(t) { let s = SHOTS[0]; for (const x of SHOTS) if (t >= x.t0) s = x; return s; }

  E.camera = function (t) {
    const s = shotAt(t);
    const k0 = clamp((t - s.t0) / (s.t1 - s.t0), 0, 1);
    const k = s.easing === 'ease' ? ease(Math.min(1, k0 * 1.1))
      : s.easing === 'snap' ? 1 - Math.pow(1 - clamp((t - s.t0) / 0.5, 0, 1), 3) : k0;
    const cam = {};
    for (const key of ['x', 'y', 'z', 'f', 'rot', 'focus']) cam[key] = lerp(s.from[key], s.to[key], k);
    // cámara en mano: respiración suave + sacudida en momentos de tensión
    const hs = 1.6 + s.shake * 6;
    cam.x += (Math.sin(t * 0.9) * 0.6 + Math.sin(t * 2.3 + 1) * 0.3 + Math.sin(t * 5.1) * 0.1 * s.shake) * hs / cam.z;
    cam.y += (Math.sin(t * 1.1 + 1) * 0.6 + Math.sin(t * 2.9) * 0.3 + Math.sin(t * 6.3) * 0.1 * s.shake) * hs / cam.z;
    cam.rot += Math.sin(t * 0.7) * 0.25 + Math.sin(t * 3.1) * 0.12 * s.shake;
    // el plano holandés recorta las esquinas: un poquito más de zoom
    cam.z *= 1 + Math.abs(cam.rot) * 0.012;
    cam.dof = s.dof;
    return cam;
  };

  // ------------------------------------------------------------ cuadro
  function drawMid(g, t) {
    M.drawGround(g, t);
    const items = [];
    items.push({ y: 1575, f: () => M.drawMoto(g, -330, 1575, false, '#1E5AA8') });
    items.push({ y: 1590, f: () => M.drawMoto(g, 1560, 1590, true, '#C62828') });
    items.push({ y: 1505, f: () => M.drawMoto(g, 1380, 1505, true, '#2E7D32') });
    const mx = motoX(t);
    items.push({ y: MOTO.y, f: () => M.drawMoto(g, mx, MOTO.y, false, '#F9A825', t, t < MOTO.t1 + 0.2) });
    const poses = CAST.map((c) => E.pose(c, t));
    for (const c of CAST) {
      items.push({ y: c.home[1] - 0.5, f: () => { g.save(); g.translate(c.home[0], c.home[1]); g.scale(M.S, M.S); g.translate(-200, -760); M.drawChairVB(g, c.chair); g.restore(); } });
    }
    // sombras de contacto primero
    CAST.forEach((c, i) => { const P = poses[i]; if (!P.riding) M.drawContactShadow(g, P.x, P.y, 1 - 0.4 * P.sit); });
    CAST.forEach((c, i) => { const P = poses[i]; items.push({ y: P.riding ? MOTO.y - 1 : P.y, f: () => M.drawCharacter(g, c.ch, P) }); });
    items.sort((a, b) => a.y - b.y).forEach((it) => it.f());
    M.drawDapple(g, t);
    M.drawCanopy(g, t);
    M.drawPetals(g, t);
  }

  E.render = function (ctx, t) {
    const C = M.C;
    const s = shotAt(t);
    const cam = E.camera(t);
    const m = C.mainCtx;
    m.setTransform(1, 0, 0, 1, 0, 0);
    m.fillStyle = '#9CCBEA'; m.fillRect(0, 0, M.W, M.H);
    C.layer(m, cam, 9, (g) => M.drawSky(g, t));
    C.layer(m, cam, 2.4, (g) => M.drawFar(g, t), 'rgba(205,228,240,0.30)');
    C.layer(m, cam, 0.9, (g) => M.drawBuild(g, t), 'rgba(215,232,240,0.10)');
    C.layer(m, cam, 0.4, (g) => M.drawStreet(g, t), 'rgba(215,232,240,0.04)');
    C.layer(m, cam, 0, (g) => drawMid(g, t));
    // primer plano
    for (const fg of s.fg) {
      if (fg.type === 'branches') {
        const par = { x: -(cam.x - s.from.x) * cam.z * 1.8, y: -(cam.y - s.from.y) * cam.z * 1.8 };
        C.fgBranches(m, cam, t, par);
      } else if (fg.type === 'petals') C.fgPetals(m, t);
      else if (fg.type === 'ots') C.ots(m, BY[fg.id].ch, E.pose(BY[fg.id], t), fg.side, cam);
    }
    C.sunRays(m, t, s.rays * clamp(1.4 - cam.z * 0.35, 0.25, 1));
    C.grade(ctx, t, { dark: s.dark, sun: s.rays });
    // barrido rápido entre planos
    if (s.whip && s.prev) {
      const a = 1 - clamp((t - s.t0) / 0.16, 0, 1);
      C.motionBlur(ctx, a, Math.sign(s.from.x - (s.prev.to.x)) || 1);
    }
    // ---- capa de pantalla (textos nítidos)
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    drawCards(ctx, t);
    drawSubs(ctx, t);
    drawTitle(ctx, t);
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
