# Capital Curioso — "Ningún avión despega"

Video vertical 1080x1920 · 30 fps · 76 s · H.264 + AAC (-14 LUFS), listo para TikTok, Instagram y Facebook.

- `capital-curioso-ningun-avion-despega.mp4` — video final.
- `render.py` — dibuja los cuadros (Pillow) sincronizados con `data/words.json` (tiempos por palabra de la narración).
- `audio.py` — música de suspenso y efectos sintetizados, con la música bajada bajo la voz.
- `imagenes/`, `audio/narracion.mp3` — material entregado.
- `data/` — mapas (us-atlas, world-atlas; Natural Earth) y transcripción.

Regenerar:
```
python3 render.py build/video_mudo.mp4 && python3 audio.py
ffmpeg -i build/video_mudo.mp4 -i build/mezcla.wav -map 0:v -map 1:a -c:v copy \
  -af loudnorm=I=-14:TP=-1.5:LRA=7 -c:a aac -b:a 192k -movflags +faststart capital-curioso-ningun-avion-despega.mp4
```
