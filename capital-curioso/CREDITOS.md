# RD al Mundial Sub-17 — Capital Curioso

Video final: `rd-mundial-sub17.mp4` (1080×1920, 30 fps, 66 s, AAC estéreo, -14 LUFS).

## Créditos de audio
- Narración: voz de Jaider (archivo del autor).
- Música: compuesta por síntesis en `fuente/scripts/audio.py` (sin derechos de terceros).
- Silbato: "218318 splicesound referee-whistle-blow-gymnasium.wav" — SpliceSound, CC0 (Wikimedia Commons).
- Público de estadio: "Arrowhead Stadium crowd noise.wav" — Kj1595, CC BY-SA 4.0 (Wikimedia Commons).
  → Esta licencia pide atribución: incluye "Sonido de público: Kj1595, CC BY-SA 4.0 (Wikimedia Commons)" en la descripción del post.
- Whooshes, golpes, clics y pitidos: sintetizados.

## Otros
- Mapas: Natural Earth (dominio público). Fuentes: Anton, Oswald, Inter (SIL OFL).
- Fotos: proporcionadas por el autor.

## Cómo regenerarlo
`fuente/build/index.html` contiene toda la animación (`render(t)`); `scripts/render.js` la captura con Playwright
y `scripts/audio.py` crea la mezcla. Ver los comentarios de cada script.
