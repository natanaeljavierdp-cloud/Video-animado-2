# Video: "Trump, Xi y Putin: la cumbre inédita"

Video vertical 1080×1920 a 30 fps, de 77 s, sincronizado con `audio/narracion.mp3`.

- **Resultado:** `out/cumbre-final.mp4`
- **Escenas:** `escenas.html`. Las 10 escenas están animadas con `render(t)`. Para ver un instante concreto, abre el archivo en el navegador y ejecuta `render(12)` en la consola.
- **Subtítulos:** se generan a partir de `audio/transcripcion.json`, que es la transcripción automática con tiempos por palabra.
- **Renderizar de nuevo:** `node render.mjs` (hace falta Playwright y ffmpeg). Con `node render.mjs --preview 5 20 40` se guardan fotogramas sueltos en `out/preview/`.

## Imágenes y derechos
| Archivo | Origen | Licencia |
|---|---|---|
| trump.jpg | Daniel Torok, Wikimedia Commons | Dominio público |
| xi.jpg | Dati Bendo, Wikimedia Commons | CC BY 4.0 (crédito en pantalla) |
| yalta.jpg | Conferencia de Yalta, 1945 | Dominio público |
| banderas, mapas | Wikimedia Commons / Natural Earth | Dominio público |
| putin.jpg, moscu.jpg, shenzhen.jpg | Recortes de capturas propias (fotos/) | **Sin verificar**: conviene cambiarlas por 20-putin-2023 (CC BY 4.0), 16-kremlin y 17/18-shenzhen de CREDITOS-originales.txt |

La Casa Blanca está dibujada como vector plano. No se usaron los "renders" 10 y 11, que muestran otro edificio, ni los mapas de Shutterstock, iStock y Vecteezy.

## Música de suspenso
`musica.py` genera `audio/musica-suspenso.wav`, una pista original sin derechos de terceros. Tiene un dron grave en Re menor, cuerdas, un latido a 70 bpm, tic-tac de reloj y golpes que coinciden con los sellos y los cambios de escena. Para obtener `out/cumbre-final-musica.mp4`, la música se mezcla bajo la voz con *ducking* y el resultado se normaliza a −14 LUFS:

```bash
python3 musica.py
ffmpeg -y -i out/cumbre-final.mp4 -i audio/musica-suspenso.wav -filter_complex \
"[0:a]aformat=channel_layouts=stereo,asplit=2[v][sc];[1:a]volume=0.32[m];[m][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];[v][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart out/cumbre-final-musica.mp4
```
Para subir o bajar la música, cambia `volume=0.32`.
