# Capital Curioso — Funcionarios que se mudaron a bases militares

Video vertical 1080×1920, 30 fps, ~66 s, para @capitalcuriosoo.

- `capital_curioso_bases_militares.mp4` — video final.
- `narracion.mp3` — voz original (Jaider). `guion.txt` — texto exacto de la narración.
- `imagenes/` — fotos usadas (incluye `fortmcnair_aerea.jpg` y `fortmcnair_mapa.jpg`, las fotos de Fort McNair enviadas por chat).

## Cómo se genera

```bash
python3 build/transcribe.py narracion.mp3 build/words_raw.json   # tiempos palabra por palabra (faster-whisper)
python3 build/align.py 65.41                                     # alinea el guion exacto → words.json + timeline.json
node build/render.mjs video                                      # dibuja los cuadros (Canvas en Chromium) → build/parts/
python3 build/audio.py                                           # música de suspenso + efectos sintetizados + voz → build/mezcla.wav
ffmpeg -f concat -i build/parts/list.txt -i build/mezcla.wav -c:v copy -c:a aac -b:a 192k -shortest capital_curioso_bases_militares.mp4
```

Vista previa de cuadros sueltos: `node build/render.mjs preview 12.5 30 55` → `build/preview/`.

Si agregas `imagenes/anacostia.jpg` o `imagenes/fortmyer.jpg`, se usan automáticamente como foto de fondo
de las escenas 5 y 6 (sin ellas se muestra un fondo de textura). Vuelve a ejecutar `render.mjs video` y el `ffmpeg` final.

La música y los efectos están sintetizados por código (sin licencias de terceros).
