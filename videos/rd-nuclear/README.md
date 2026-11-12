# ¿República Dominicana nuclear? — Capital Curioso

Video vertical 1080×1920, 30 fps, 67 s, con narración, música de suspenso y efectos.

- `rd-nuclear.mp4` — video final.
- `index.html` + `src/` — motor de animación en canvas (`render(t)`), sincronizado con `words.json`
  (tiempos por palabra de la narración, transcrita con faster-whisper).
- `audio.py` — sintetiza música y efectos y mezcla con `assets/narracion.mp3` → `build/mix.wav`.
- `render.cjs` — renderiza los fotogramas con Playwright/Chromium y codifica con ffmpeg.

Regenerar: `python3 audio.py && node render.cjs 4`
Vista previa de instantes: `node preview.cjs carpeta 12.5 30`
