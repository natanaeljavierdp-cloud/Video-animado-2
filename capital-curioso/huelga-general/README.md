# Capital Curioso — Huelga general (11 de noviembre)

`capital_curioso_huelga_general.mp4`: 1080×1920, 30 fps, 69,7 s (66,2 s de narración + 3,5 s de cierre).

## Imágenes
| Hueco | Imagen | Momento |
|---|---|---|
| [IMAGEN 1] edificio de Madrid | `img/02.jpg` | 0–7,5 s |
| [IMAGEN 2] protesta por la vivienda | `img/08.jpg` | 8,8–16,1 s |
| [IMAGEN 3] Madrid bajo la lluvia | `img/10.jpg` | 50,3–56,7 s |
| Apoyo: fuego | `img/03.jpg` | 16,1–19,5 s ("encendió") |
| Apoyo: bandera | `img/01.jpg` | fondo del gráfico y de la encuesta |
| Apoyo: contenedor, Mossos | `img/04.jpg`, `img/05.jpg` | fondo del mapa |
| Apoyo: lanzador, línea policial | `img/07.jpg`, `img/09.jpg` | "¿Fue un éxito?" |
| Apoyo: bengalas | `img/06.jpg` | mitad izquierda de la pantalla dividida |
| Apoyo: Congreso | `img/11.jpg` | calendario electoral |

Para cambiar una foto, reemplaza el archivo en `proyecto/img/` con el mismo nombre y vuelve a renderizar.

## Música (atribución obligatoria)
"Darkling" — Kevin MacLeod (incompetech.com). Licencia CC BY 4.0.
Pon en la descripción: `Música: "Darkling" de Kevin MacLeod (incompetech.com), CC BY 4.0`.
Los efectos de sonido se sintetizaron (sin licencia de terceros).

## Volver a renderizar
1. `proyecto/transcribe.py` → tiempos por palabra (faster-whisper) → `subs.py` → `subs.json`.
2. `node map.js` → contorno de España (world-atlas) → `data.js` = `SUBS` + `SPAIN`.
3. `OUT=frames node render.js 0 1985` (fotogramas), `mix.py narración.mp3 Darkling.mp3` (audio).
4. ffmpeg: fotogramas + `capital_curioso_cierre.mp4` + audio.
Las fuentes (Poppins, Playfair Display) se descargan de google/fonts.
