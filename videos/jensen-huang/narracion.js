/* Capital Curioso · Jensen Huang — datos compartidos por todos los formatos
   (noticiero: escena.html · investigación: investigacion.html).
   NARRACION tiene los tiempos reales de cada frase de audio/narracion.mp3. */
const W = 1080, H = 1920, FPS = 30;

const C = {
  navy: '#0A285A', navyD: '#061A3D', navyDD: '#04122B', navyL: '#15407F', navyM: '#0E3170',
  red: '#FE4A55', redD: '#D8303C', white: '#FFFFFF', ink: '#0A1F44',
  gray: '#A9B8D3', grayD: '#5E7299', paper: '#F6F7FB', marker: '#FFE36E', gold: '#FFC83D'
};

// Bloques de narración = escenas. Cada frase lleva [inicio, fin] en segundos,
// medidos sobre audio/narracion.mp3 (voz de Jaider, ElevenLabs). Dentro de cada
// frase las palabras se reparten según su longitud.
const NARRACION = [
  { id: 's1', frases: [[0.05, 4.54, 'El hombre detrás de los chips de la inteligencia artificial acaba de admitir una infidelidad...'],
    [5.17, 7.31, 'y la otra mujer, según Estados Unidos,'], [7.62, 8.99, 'sería una espía china.']] },
  { id: 's2', frases: [[9.78, 11.23, 'Él es Jensen Huang,'], [11.47, 12.53, 'fundador de Nvidia,'],
    [12.77, 15.26, 'una de las empresas más valiosas del planeta,'], [15.53, 17.73, 'y una de las personas más ricas del mundo.']] },
  { id: 's3', frases: [[18.26, 19.68, 'Ella es Alice Huang,'], [19.99, 21.31, 'ejecutiva de Megaspeed,'],
    [21.58, 24.11, 'una empresa de Singapur que le compraba a Nvidia.'],
    [24.58, 30.54, 'Según The New York Times, la inteligencia estadounidense cree que China la reclutó para obtener información sobre él.']] },
  { id: 's4', frases: [[31.07, 33.48, 'Este domingo, Huang escribió a sus empleados:'], [33.91, 35.23, '«Le fui infiel a mi esposa.'],
    [35.62, 36.36, 'No hay excusa.'], [36.83, 38.20, 'Lo siento profundamente.»'], [38.79, 39.64, 'Ese mismo día,'],
    [39.80, 41.99, 'Nvidia abrió una investigación independiente.']] },
  { id: 's5', frases: [[42.52, 43.46, 'Trump lo defendió:'], [43.85, 46.65, 'dice que Huang le aseguró que no sabía que era espía.'],
    [47.13, 49.32, 'China lo niega y habla de difamaciones.'],
    [49.65, 53.57, 'Y el Congreso lo citó a una reunión a puerta cerrada el 18 de noviembre.']] },
  { id: 's6', frases: [[54.02, 56.58, 'Por ahora no hay pruebas de que se filtraran secretos.'], [56.94, 57.97, 'Pero la pregunta es:'],
    [58.32, 60.88, '¿seguirá siendo el rey de la inteligencia artificial?']] },
  { id: 's7', frases: [[61.37, 62.79, 'Comenta 1 o 2.']] },
];
NARRACION.forEach(n => { n.txt = n.frases.map(f => f[2]).join(' '); n.t = [n.frases[0][0], n.frases[n.frases.length - 1][1]]; });
// Límites visuales de escena (la escena 7, la encuesta, dura hasta el final).
const SCENES = { s1: [0, 9.5], s2: [9.5, 17.95], s3: [17.95, 30.8], s4: [30.8, 42.25], s5: [42.25, 53.8], s6: [53.8, 61.1], s7: [61.1, 66.5] };
const DURATION = SCENES.s7[1];
// Opcional: tiempos reales por palabra [[inicio,fin], ...] por bloque (de una transcripción).
const WORD_TIMES = window.WORD_TIMES || null;

// ---------------------------------------------------------------- utilidades
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, k) => a + (b - a) * k;
const prog = (t, a, b) => clamp((t - a) / (b - a));
const eOut = k => 1 - Math.pow(1 - k, 3);
const eIn = k => k * k * k;
const eInOut = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const eBack = k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const eExpo = k => k >= 1 ? 1 : 1 - Math.pow(2, -10 * k);
const inS = (t, id) => t >= SCENES[id][0] && t < SCENES[id][1];
const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9ñ]/g, '');

// ---------------------------------------------------------------- tiempos por palabra
function spread(text, a, b) {
  const toks = text.split(/\s+/);
  const wt = toks.map((w, i) => {
    let k = w.replace(/[^\p{L}\p{N}]/gu, '').length + 2.2;
    if (w === '18') k += 6; // se pronuncia "dieciocho"
    if (/,$/.test(w) && i < toks.length - 1) k += 3;
    return Math.max(k, 2.5);
  });
  const tot = wt.reduce((x, y) => x + y, 0);
  let acc = a;
  return toks.map((w, i) => { const s = acc; acc += (b - a) * wt[i] / tot; return { w, s, e: acc }; });
}
const WORDS = NARRACION.map((seg, si) => {
  const toks = seg.txt.split(/\s+/);
  if (WORD_TIMES && WORD_TIMES[si] && WORD_TIMES[si].length === toks.length)
    return toks.map((w, i) => ({ w, s: WORD_TIMES[si][i][0], e: WORD_TIMES[si][i][1] }));
  return seg.frases.flatMap(([a, b, t]) => spread(t, a, b));
});
// cue('s2','planeta') -> segundo en que se dice esa palabra
function cue(id, word, nth = 0) {
  const si = NARRACION.findIndex(s => s.id === id), nw = norm(word);
  let n = 0;
  for (const x of WORDS[si]) if (norm(x.w) === nw) { if (n++ === nth) return x.s; }
  console.warn('cue no encontrado', id, word); return SCENES[id][0];
}
function cueEnd(id, word, nth = 0) {
  const si = NARRACION.findIndex(s => s.id === id), nw = norm(word);
  let n = 0;
  for (const x of WORDS[si]) if (norm(x.w) === nw) { if (n++ === nth) return x.e; }
  return SCENES[id][1];
}

// Cues clave (todo deriva de la narración)
const K = {
  s1Headline: cue('s1', 'admitir'), s1Sub: cue('s1', 'según'),
  s2Count: cue('s2', 'una', 0), s2Rich: cue('s2', 'personas'),
  s3Map: cueEnd('s3', 'Nvidia.') + 0.05, s3NYT: cue('s3', 'según'), s3China: cue('s3', 'China'), s3Info: cue('s3', 'información'),
  s4Quote: cue('s4', '«Le'), s4QuoteEnd: cueEnd('s4', 'profundamente.»'), s4Same: cue('s4', 'Ese'), s4Inv: cue('s4', 'investigación'),
  s5China: cue('s5', 'China'), s5Cong: cue('s5', 'Congreso'), s5Date: cue('s5', '18'),
  s6Q: cue('s6', 'pregunta'),
};
