# Capital Curioso — "1 de cada 5" (video vertical 9:16)

`capital_curioso_latinos.mp4` · 1080x1920 · 30 fps · 63 s · voz + música + efectos mezclados (−14 LUFS).

| Tiempo | Frase de la narración | Escena |
|---|---|---|
| 0–5,0 s | "Uno de cada cinco…" | 5 siluetas, una en rojo · "1 DE CADA 5" · golpe grave |
| 5,0–9,45 s | "Hoy, los latinos son el 20 %…" | Mapa de EE. UU. que se llena de rojo · contador 0→20 % |
| 9,45–16,25 s | "Y aquí está lo sorprendente…" | Ícono hospital/bebé · gráfico de línea · fuente Hispanic Federation |
| 16,25–27,05 s | "Ese poder también se siente en las urnas…" | Foto familia (Ken Burns) · urna · dona 50 % · fuente UnidosUS |
| 27,05–37,2 s | "Y llega hasta el Capitolio…" | Capitolio con barras de cine y luz cálida · contador 50+ · rótulo |
| 37,2–47,25 s | "Pero hay un contraste…" | Tono oscuro · tarjeta de encuesta con barra al 65 % · fuente Axios / Noticias Telemundo (Ipsos) |
| 47,25–50,15 s | "Más poder… pero más preocupación." | Pantalla dividida con flechas que suben a la vez |
| 50,15–58,5 s | "¿Tú qué crees?…" | Encuesta final con botones 👍/👎 · ícono de comentario |
| 58,5–63 s | — | Cierre de marca (`assets/cierre.mp4`) + sonido de cierre |

## Regenerar
Requiere Node + Playwright (Chromium), Python 3 con numpy/scipy y ffmpeg.
```bash
./make.sh
```
- `scene.html` — todas las animaciones (canvas), `renderFrame(t)` determinista.
- `render.mjs` — renderiza los fotogramas (`node render.mjs stills 7 24` para fotos de prueba).
- `audio.py` — música de suspenso y efectos sintetizados (sin derechos de autor).
- `assets/words.json` — tiempos por palabra de la narración (subtítulos).
- `assets/us-states.json` — contornos de estados (paquete npm `us-atlas`).
