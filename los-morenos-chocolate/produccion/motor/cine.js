// =====================================================================
//  CINE: cámara 2.5D con parallax, lentes, profundidad de campo,
//  luz (rayos de sol), gradación de color y grano de película.
//  Cámara: {x, y, z (tamaño de los personajes), f (lente: 0.8 gran angular … 3 tele),
//           rot (grados, plano holandés), focus (profundidad enfocada), dof (cuánto desenfoque)}
// =====================================================================
/* global window, document */
(function () {
  const M = window.M;
  const { clamp } = M;
  const C = (M.C = {});
  const W = 1080, H = 1920;
  const A = { x: 700, y: 1400 };   // punto de referencia del decorado
  const FREF = 1.5;                // lente de referencia del diseño

  const mk = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  let half1, half2, main, tmp, grain = [], fx;

  C.init = function () {
    half1 = mk(W / 2, H / 2); half2 = mk(W / 2, H / 2); main = mk(W, H); tmp = mk(W, H); fx = mk(W / 2, H / 2);
    for (let k = 0; k < 6; k++) {
      const g = mk(W / 2, H / 2), gx = g.getContext('2d');
      const id = gx.createImageData(W / 2, H / 2);
      for (let i = 0; i < id.data.length; i += 4) {
        const v = 128 + (Math.random() - 0.5) * 120;
        id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255;
      }
      gx.putImageData(id, 0, 0);
      grain.push(g);
    }
    C.main = main; C.mainCtx = main.getContext('2d');
  };

  // escala de una capa a profundidad dd (0 = personajes; >0 más lejos; <0 más cerca)
  C.scaleAt = (cam, dd) => cam.z / (1 + (cam.z * dd) / cam.f);

  C.apply = function (ctx, cam, dd, res = 1) {
    const s = C.scaleAt(cam, dd), g = 1 + dd / FREF;
    ctx.setTransform(res, 0, 0, res, 0, 0);
    ctx.translate(W / 2, H / 2);
    ctx.rotate(((cam.rot || 0) * Math.PI) / 180);
    ctx.scale(s, s);
    ctx.translate(-cam.x, -cam.y);
    ctx.translate(A.x, A.y); ctx.scale(g, g); ctx.translate(-A.x, -A.y);
  };

  C.blurFor = (cam, dd) => clamp((cam.dof ?? 1) * 5.2 * Math.abs(dd - (cam.focus || 0)) * Math.pow(cam.z, 0.8) * Math.sqrt(cam.f / FREF), 0, 24);

  // dibuja una capa (desenfocada si toca) sobre ctx
  C.layer = function (ctx, cam, dd, drawFn, haze) {
    const b = C.blurFor(cam, dd);
    if (b < 1.2) {
      ctx.save(); C.apply(ctx, cam, dd, 1); drawFn(ctx); ctx.restore();
    } else {
      const h = half1.getContext('2d');
      h.setTransform(1, 0, 0, 1, 0, 0); h.clearRect(0, 0, W / 2, H / 2);
      h.save(); C.apply(h, cam, dd, 0.5); drawFn(h); h.restore();
      const h2 = half2.getContext('2d');
      h2.setTransform(1, 0, 0, 1, 0, 0); h2.clearRect(0, 0, W / 2, H / 2);
      h2.filter = `blur(${(b / 2).toFixed(2)}px)`; h2.drawImage(half1, 0, 0); h2.filter = 'none';
      ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(half2, 0, 0, W, H); ctx.restore();
    }
    if (haze) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = haze; ctx.fillRect(0, 0, W, H); ctx.restore(); }
  };

  // dibujo en pantalla (primer plano) desenfocado y opcionalmente oscurecido
  C.screenFx = function (ctx, drawFn, blur, filterExtra = '') {
    const h = half1.getContext('2d');
    h.setTransform(1, 0, 0, 1, 0, 0); h.clearRect(0, 0, W / 2, H / 2);
    h.save(); h.scale(0.5, 0.5); drawFn(h); h.restore();
    const h2 = half2.getContext('2d');
    h2.setTransform(1, 0, 0, 1, 0, 0); h2.clearRect(0, 0, W / 2, H / 2);
    h2.filter = `blur(${(blur / 2).toFixed(2)}px) ${filterExtra}`; h2.drawImage(half1, 0, 0); h2.filter = 'none';
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(half2, 0, 0, W, H); ctx.restore();
  };

  // ramas con flores en primer plano (cuelgan desde arriba)
  C.fgBranches = function (ctx, cam, t, par) {
    C.screenFx(ctx, (g) => {
      g.translate(par.x, par.y);
      const r = M.rng(5);
      for (let i = 0; i < 26; i++) {
        const x = -200 + r() * 1500, y = -120 + r() * (r() < 0.7 ? 260 : 420), rad = 70 + r() * 110;
        g.fillStyle = r() < 0.5 ? '#1F3F1D' : '#2A5126';
        g.beginPath(); g.arc(x + Math.sin(t * 0.8 + i) * 10, y, rad, 0, Math.PI * 2); g.fill();
      }
      for (let i = 0; i < 40; i++) {
        const x = -200 + r() * 1500, y = -60 + r() * 380;
        g.fillStyle = r() < 0.5 ? '#E8B92C' : '#F4CF4A';
        g.beginPath(); g.arc(x + Math.sin(t * 0.8 + i) * 10, y, 14 + r() * 14, 0, Math.PI * 2); g.fill();
      }
    }, 20);
  };

  // pétalos grandes pasando muy cerca de la cámara
  C.fgPetals = function (ctx, t, amount = 1) {
    C.screenFx(ctx, (g) => {
      const r = M.rng(31);
      for (let i = 0; i < 9 * amount; i++) {
        const sp = 90 + r() * 120, off = r() * 3000, ph = r() * 6.28;
        const y = -200 + ((t * sp + off) % 2400);
        const x = r() * 1080 + Math.sin(t * 0.9 + ph) * 90;
        g.save(); g.translate(x, y); g.rotate(t + ph);
        g.fillStyle = 'rgba(250,210,70,0.9)';
        g.beginPath(); g.ellipse(0, 0, 34, 18, 0, 0, Math.PI * 2); g.fill();
        g.restore();
      }
    }, 14);
  };

  // silueta de alguien de espaldas/de lado en primer plano (plano sobre el hombro)
  C.ots = function (ctx, ch, P, side, cam) {
    const k = 1.95 * cam.z * M.S;
    C.screenFx(ctx, (g) => {
      const P2 = Object.assign({}, P, { x: 0, y: 0, lean: 0, sit: 0, prop: null });
      g.translate(side === "L" ? 60 : W - 60, H + 760 * k * 0.52);
      g.scale(k / M.S, k / M.S);
      M.drawCharacter(g, ch, P2);
    }, 22, 'brightness(0.42) saturate(0.7)');
  };

  // rayos de sol entre las hojas (pantalla)
  C.sunRays = function (ctx, t, strength) {
    if (strength <= 0.01) return;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = 'screen';
    const ox = 1250, oy = -260;
    for (let i = 0; i < 6; i++) {
      const a = 2.05 + i * 0.09 + Math.sin(t * 0.25 + i * 1.7) * 0.025;
      const w = 0.018 + (i % 3) * 0.012;
      const L = 2600;
      const g = ctx.createLinearGradient(ox, oy, ox + Math.cos(a) * L, oy + Math.sin(a) * L);
      const al = strength * (0.07 + 0.035 * Math.sin(t * 0.6 + i * 2));
      g.addColorStop(0, `rgba(255,236,190,${al})`); g.addColorStop(0.7, `rgba(255,220,160,${al * 0.5})`); g.addColorStop(1, 'rgba(255,220,160,0)');
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.moveTo(ox, oy);
      ctx.lineTo(ox + Math.cos(a - w) * L, oy + Math.sin(a - w) * L);
      ctx.lineTo(ox + Math.cos(a + w) * L, oy + Math.sin(a + w) * L);
      ctx.closePath(); ctx.fill();
    }
    // polvo flotando en la luz
    const r = M.rng(11);
    for (let i = 0; i < 28; i++) {
      const x = (r() * 1200 + t * (8 + r() * 14)) % 1180 - 50, y = (r() * 2000 + Math.sin(t * 0.5 + i) * 40 - t * 6) % 1950;
      ctx.fillStyle = `rgba(255,240,200,${strength * (0.12 + r() * 0.2)})`;
      ctx.beginPath(); ctx.arc(x, y < 0 ? y + 1950 : y, 1.5 + r() * 2.5, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  };

  // gradación de color + viñeta + grano: main -> ctx
  C.grade = function (ctx, t, opts = {}) {
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.filter = 'contrast(1.18) saturate(1.2) brightness(0.98)';
    ctx.drawImage(main, 0, 0);
    ctx.filter = 'none';
    // tono: sombras frías arriba, cálido de tarde abajo
    ctx.globalCompositeOperation = 'soft-light';
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, 'rgba(30,90,150,0.40)'); g.addColorStop(0.5, 'rgba(255,190,110,0.12)'); g.addColorStop(1, 'rgba(200,110,50,0.30)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    // brillo del sol arriba a la derecha
    ctx.globalCompositeOperation = 'screen';
    const sg = ctx.createRadialGradient(1050, 80, 0, 1050, 80, 900);
    sg.addColorStop(0, `rgba(255,214,150,${0.2 * (opts.sun ?? 1)})`); sg.addColorStop(1, 'rgba(255,214,150,0)');
    ctx.fillStyle = sg; ctx.fillRect(0, 0, W, H);
    // viñeta
    ctx.globalCompositeOperation = 'multiply';
    const vg = ctx.createRadialGradient(540, 900, 520, 540, 960, 1250);
    vg.addColorStop(0, 'rgba(255,255,255,1)'); vg.addColorStop(1, `rgba(${opts.dark ? 70 : 120},${opts.dark ? 60 : 100},${opts.dark ? 70 : 90},1)`);
    ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);
    // grano
    ctx.globalCompositeOperation = 'overlay';
    ctx.globalAlpha = 0.22;
    ctx.drawImage(grain[Math.floor(t * 24) % grain.length], 0, 0, W, H);
    ctx.restore();
  };

  // desenfoque de movimiento (barrido rápido de cámara)
  C.motionBlur = function (ctx, amount, dir) {
    if (amount < 0.02) return;
    const tc = tmp.getContext('2d');
    tc.setTransform(1, 0, 0, 1, 0, 0); tc.clearRect(0, 0, W, H); tc.drawImage(ctx.canvas, 0, 0);
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
    const n = 8, span = 140 * amount;
    ctx.globalAlpha = 1;
    ctx.drawImage(tmp, 0, 0);
    for (let i = 0; i < n; i++) {
      ctx.globalAlpha = 0.5 / (i * 0.4 + 1);
      ctx.drawImage(tmp, dir * span * ((i + 1) / n - 0.5) * 2, 0);
    }
    ctx.restore();
  };
})();
