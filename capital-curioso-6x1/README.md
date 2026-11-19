# Capital Curioso — Fin de la escala 6x1 en Brasil

Video vertical **1080×1920, 30 fps, H.264 + AAC**, de unos 71 s: 66,6 s de narración más el cierre animado.
Archivo final: `capital_curioso_6x1.mp4`.

## Cómo se genera

```bash
pip install numpy pillow scipy faster-whisper   # faster-whisper solo para volver a transcribir
python3 audio.py      # música + efectos + mezcla con la voz  -> build/mix.wav
python3 render.py     # fotogramas + subtítulos + mux final   -> capital_curioso_6x1.mp4
python3 render.py --frames 8.1 30.5   # (opcional) fotogramas sueltos en build/preview/
```

- `timeline.py`: tiempos de cada escena, sacados de la transcripción palabra por palabra
  (`assets/data/words.json`, generada con faster-whisper "small").
- `render.py`: las 8 escenas, los subtítulos palabra por palabra (arriba, con la palabra actual en rojo),
  las transiciones de cortinilla, el Ken Burns, el grano y la viñeta.
- `audio.py`: la música de suspenso y todos los efectos (whoosh, impacto, cristales, tic-tac, pops, ding)
  están **sintetizados en el script**, así que no tienen derechos de terceros. La música va a −20 dB
  respecto a la voz y la mezcla queda normalizada a −14 LUFS.

## Recursos

- Fotos en `assets/img/`. Además de las 8 pedidas hay tres extra que no se usan
  (`calendario2.jpg`, `saopaulo2.jpg`, `trabajadores2.jpg`). `calendario.jpg` es el fondo de la encuesta.
- Mapa: Natural Earth 110m (dominio público).
- Fuentes: Anton, Poppins y Bebas Neue (Google Fonts, licencia OFL).
- El cierre usa el clip `assets/capital_curioso_cierre.mp4`, con el texto "Síguenos para más historias de Latinoamérica" encima.
