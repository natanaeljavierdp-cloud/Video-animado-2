# Cómo regenerar el video (técnico)

1. Copiar en `assets/` las fotos (nombres en `timeline.js`, lista `BGS`) y `logo.png`; en `fonts/` los .woff2 de Playfair Display, Cinzel y Montserrat (paquetes npm `@fontsource/*`).
2. `node render.js preview 6.9 27.3` → fotogramas de prueba. `node render.js frames 0 1905 main.mp4` → video sin audio (63,5 s).
3. `python3 scripts/sfx.py sfx_track.wav` (efectos) y `python3 scripts/mix.py` (narración + música + efectos).
4. Unir con ffmpeg: `main.mp4` + cierre (xfade 0,3 s en 63,2 s) + audio normalizado a -14 LUFS.

Los subtítulos (`subs.json`) salen de `scripts/transcribe.py` (faster-whisper) con correcciones manuales.
