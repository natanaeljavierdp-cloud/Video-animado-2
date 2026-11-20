// Subtítulos 2D (1–4 palabras), arriba al centro, con resaltado de palabras clave.
import { clamp, lin, eback, eout } from './lib.js';

const FILLER = new Set(['a', 'al', 'con', 'de', 'del', 'e', 'el', 'en', 'es', 'esa', 'ese', 'esta', 'la', 'las', 'le', 'lo', 'los', 'nos', 'o', 'para', 'por', 'que', 'se', 'si', 'su', 'un', 'una', 'unos', 'y', 'así', 'como', 'hay', 'han', 'ir', 'va', 'sí']);
// frases clave (en minúsculas, sin puntuación) -> se pintan en rojo
const KEYS = ['día entero', 'otro día', 'voyager 1', '1977', 'día luz', '26 mil millones', 'kilómetros', 'luz', 'más rápido', 'luna', 'un segundo', '24 horas',
  'paneles', 'pila nuclear', 'calor', 'electricidad', 'apagando instrumentos', 'antena', 'bombillo pequeño', 'radio', 'débil', 'antenas gigantes',
  'estados unidos', 'españa', 'australia', 'tierra gira', 'muy despacio', 'despacio', 'lento', 'internet', 'sistema solar', 'disco de oro', 'sonidos', 'imágenes', 'humanidad', 'mensajero'];
// grupos que no se deben partir
const KEEP = ['voyager 1', 'día luz', 'pila nuclear', 'antenas gigantes', 'estados unidos', 'disco de oro', 'bombillo pequeño', '24 horas', 'un segundo', 'sistema solar', '26 mil millones', 'día entero'];

const norm = (s) => s.toLowerCase().replace(/[.,¿?¡!:;]/g, '').trim();

export function buildChunks(words) {
  // reemplazos de visualización
  const W = [];
  for (let i = 0; i < words.length; i++) {
    let [a, b, raw] = words[i];
    let txt = raw.trim();
    const n = norm(txt);
    if (n === 'veinticuatro') txt = '24';
    if (n === 'veintiséis') {
      // "veintiséis mil millones" -> "26 mil millones"
      txt = '26';
    }
    if (n === '1' && i > 0 && norm(words[i - 1][2]) === 'voyager') txt = txt.replace('1.', '1.');
    W.push({ a, b, txt, n: norm(txt), punct: /[.,]$/.test(raw.trim()) });
  }
  // marcar grupos indivisibles
  const glue = new Array(W.length).fill(false); // glue[i] = la palabra i va pegada a la i+1
  for (const k of KEEP) {
    const parts = k.split(' ');
    for (let i = 0; i + parts.length <= W.length; i++) {
      if (parts.every((p, j) => W[i + j].n === p)) for (let j = 0; j < parts.length - 1; j++) glue[i + j] = true;
    }
  }
  const chunks = [];
  let cur = [];
  const flush = () => { if (cur.length) chunks.push(cur); cur = []; };
  for (let i = 0; i < W.length; i++) {
    cur.push(i);
    const w = W[i], nx = W[i + 1];
    if (!nx) { flush(); break; }
    if (glue[i]) continue;
    const gap = nx.a - w.b;
    const len = cur.reduce((s, j) => s + W[j].txt.length + 1, 0);
    // longitud del grupo pegado que viene
    let k = i + 1, glen = 0, gn = 0; while (k < W.length) { glen += W[k].txt.length + 1; gn++; if (!glue[k]) break; k++; }
    if (w.punct || gap > 0.28 || cur.length + gn > 4 || len + glen > 22 || (cur.length >= 3 && len > 10)) flush();
  }
  // texto + colores
  return chunks.map((idx) => {
    const ws = idx.map((j) => W[j]);
    const n = ws.map((w) => w.n);
    const col = ws.map(() => 0); // 0 normal, 1 clave, 2 relleno
    ws.forEach((w, j) => { if (FILLER.has(w.n)) col[j] = 2; });
    for (const k of KEYS) {
      const parts = k.split(' ');
      for (let i = 0; i + parts.length <= n.length; i++) if (parts.every((p, j) => n[i + j] === p)) for (let j = 0; j < parts.length; j++) col[i + j] = 1;
    }
    return { a: ws[0].a, b: ws[ws.length - 1].b, words: ws.map((w, j) => ({ t: w.txt.replace(/[.,]$/, ''), c: col[j], a: w.a })) };
  });
}

export function drawSubs(ctx, chunks, t, mode, FONT) {
  let ci = -1;
  for (let i = 0; i < chunks.length; i++) {
    const c = chunks[i];
    const end = i + 1 < chunks.length ? Math.min(chunks[i + 1].a, c.b + 0.9) : c.b + 0.8;
    if (t >= c.a - 0.05 && t < end) { ci = i; break; }
  }
  if (ci < 0) return;
  const c = chunks[ci];
  const k = eback(lin(t, c.a - 0.05, c.a + 0.17));
  const al = clamp(lin(t, c.a - 0.05, c.a + 0.07));
  const dark = mode === 'space';
  const size = 92;
  ctx.save();
  ctx.font = `900 ${size}px ${FONT}`;
  ctx.textBaseline = 'middle';
  const space = size * 0.26;
  const ws = c.words.map((w) => ({ ...w, wd: ctx.measureText(w.t).width }));
  let total = ws.reduce((s, w) => s + w.wd, 0) + space * (ws.length - 1);
  const maxW = 960;
  const sc = Math.min(1, maxW / total);
  const cx = 540, cy = 222;
  ctx.translate(cx, cy); ctx.scale(sc * (0.82 + 0.18 * k), sc * (0.82 + 0.18 * k)); ctx.translate(-cx, -cy);
  ctx.globalAlpha = al;
  let x = cx - total / 2;
  const fill = dark ? ['#FFFFFF', '#FF4D4D', '#B9C2D6'] : ['#141414', '#E5262B', '#7A7F8A'];
  const halo = dark ? 'rgba(8,14,34,0.92)' : 'rgba(255,255,255,0.97)';
  ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  for (const w of ws) {
    // halo suave: trazo grueso difuminado + trazo nítido
    ctx.shadowColor = halo; ctx.shadowBlur = 26;
    ctx.strokeStyle = halo; ctx.lineWidth = 20; ctx.strokeText(w.t, x, cy);
    ctx.shadowBlur = 0; ctx.lineWidth = 12; ctx.strokeText(w.t, x, cy);
    ctx.fillStyle = fill[w.c]; ctx.fillText(w.t, x, cy);
    x += w.wd + space;
  }
  ctx.restore();
}
