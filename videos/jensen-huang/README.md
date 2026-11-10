# Capital Curioso · El escándalo de Jensen Huang (Nvidia)

Video vertical 9:16 (1080×1920, 30 fps) de **63.5 s**: 60 s de noticia + 3.5 s de tu cierre animado (lupa con "?").

## Archivos listos

| Archivo | Para qué |
|---|---|
| `salida/capital_curioso_jensen_huang.mp4` | Video final con música de tensión + efectos (sin voz). Súbelo a Canva. |
| `salida/musica_y_efectos.mp3` | Solo la pista de música + efectos, por si quieres manejarla aparte. |
| `salida/subtitulos.srt` | El guion cronometrado (los subtítulos ya van "quemados" en el video). |

La música y los efectos están sintetizados por código (`musica.py`): no tienen derechos de autor.

## Dónde van las fotos en Canva

Las fotos van en recuadros marcados `[FOTO: …]` con borde punteado y esquinas rojas. **No hay nada dibujado encima de esos recuadros**, así que puedes poner la foto encima sin tapar rótulos ni textos. Las coordenadas son sobre el lienzo de 1080×1920 px:

| Foto | Desde – hasta | Posición (x, y) | Tamaño (ancho × alto) |
|---|---|---|---|
| Jensen Huang con chaqueta de cuero | 0.3 s – 15.5 s | 90, 290 | 900 × 760 |
| Alice Huang | 15.5 s – 20.5 s | 90, 290 | 900 × 760 |
| Donald Trump | 35.0 s – 46.5 s | 60, 290 | 420 × 330 |
| Capitolio | 35.0 s – 46.5 s | 60, 986 | 420 × 330 |

(La bandera de China, entre las dos últimas, ya está dibujada y ondea).

En Canva: pon la foto, en **Posición** escribe X/Y y ancho/alto (si tu diseño mide 1080×1920 los valores son los mismos), recórtala para que llene el recuadro y ajusta su tiempo en la línea de tiempo.

## La narración (ElevenLabs "Jaider - Narration Spanish")

Los tiempos del video están calculados para una lectura de ~3 palabras por segundo. Cuando tengas el audio:

* **Opción rápida:** súbelo a Canva encima del video y baja el volumen del video a ~40 %.
* **Opción exacta:** guarda el audio como `audio/narracion.mp3` y ejecuta `./montar.sh audio/narracion.mp3`. Eso crea `salida/capital_curioso_jensen_huang_con_voz.mp4`: la música baja sola cuando habla la voz y todo sale a -14 LUFS (volumen estándar de TikTok/Reels).
* Si la voz no cae en su sitio, cambia los `[inicio, fin]` de cada bloque en `NARRACION` (arriba en `escena.html`) y vuelve a renderizar: subtítulos, escenas, contador, flechas, sello y efectos se re-sincronizan solos.

## Escenas

| Tiempo | Qué pasa |
|---|---|
| 0 – 8 s | Banner rojo **ÚLTIMA HORA**, foto de Jensen, titular "CEO de Nvidia admite una infidelidad" + etiqueta "SEGÚN REPORTES" |
| 8 – 15.5 s | Rótulo **JENSEN HUANG – CEO y fundador de Nvidia**, contador animado hasta **+$200,000,000,000** (fortuna estimada) |
| 15.5 – 26.5 s | Foto y rótulo de **Alice Huang – Ejecutiva de Megaspeed (Singapur)** → mapa animado EE.UU. → Singapur → China con flechas entre personas ("le compraba chips", "¿la reclutó?", "¿información?") + tarjeta de cita **The New York Times** con la etiqueta "PRESUNTO · NO CONFIRMADO" |
| 26.5 – 35 s | Correo interno tecleado, frase subrayada/resaltada, sello "Nvidia abre investigación independiente" (fuente: CNBC) y línea de tiempo animada |
| 35 – 46.5 s | Pantalla dividida en 3: Trump / China / Congreso, con calendario "18 NOV" |
| 46.5 – 53.5 s | "Por ahora no hay pruebas…" y la gran pregunta palabra por palabra: **¿Puede sobrevivir el rey de la IA?** |
| 53.5 – 60 s | Encuesta: **1 = Debe renunciar / 2 = Debe seguir** · "Comenta 1 o 2" |
| 60 – 63.5 s | Tu cierre de Capital Curioso |

Durante todo el video: subtítulos palabra por palabra (la palabra que suena se marca en rojo) y una cinta inferior "EN DESARROLLO".

## Volver a generarlo

Necesita Node 18+, Playwright (Chromium), Python 3 con `numpy` + `scipy`, y `ffmpeg`.

```bash
node render.mjs            # cuadros -> salida/_video_sin_audio.mp4 (~2 min)
./montar.sh                # música + efectos + cierre -> salida/capital_curioso_jensen_huang.mp4
```

Para ver la animación en el navegador sin renderizar: abre `escena.html` (tiene botón de reproducir y barra de tiempo).
Para revisar cuadros sueltos: `node render.mjs --stills 3,12,30`.
