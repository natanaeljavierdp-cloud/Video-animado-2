# Capital Curioso · El escándalo de Jensen Huang (Nvidia)

Video vertical 9:16 (1080×1920, 30 fps) de **70 s**: 66.5 s de noticia narrada por **Jaider (ElevenLabs)** + 3.5 s de tu cierre animado (lupa con "?").

## Archivos listos

| Archivo | Para qué |
|---|---|
| `salida/capital_curioso_jensen_huang.mp4` | **Video final**: voz de Jaider + música de suspenso + efectos. Listo para publicar. |
| `audio/narracion.mp3` | La narración original de ElevenLabs (voz "Jaider - Narration Spanish"). |
| `salida/musica_y_efectos.mp3` | Solo la pista de música + efectos, por si quieres manejarla aparte. |
| `salida/subtitulos.srt` | El guion cronometrado (los subtítulos ya van "quemados" en el video). |

La música de suspenso (dron grave, cuerdas en trémolo, latido, piano con eco, tic-tac y subidas de tensión en cada corte) y los efectos están sintetizados por código (`musica.py`): no tienen derechos de autor.

## Fotos

Las fotos ya van dentro del video (originales en `assets/fotos/`, incrustadas en `fotos.js`), con zoom/paneo lento estilo documental:

| Foto | Tiempo | Movimiento |
|---|---|---|
| Jensen Huang con chaqueta de cuero | 0.3 s – 17.9 s | acercamiento lento a la cara |
| Alice Huang (con Jensen) | 17.9 s – 24.1 s | empieza en Alice y se abre hasta mostrar a los dos |
| Donald Trump | 42.3 s – 53.8 s | acercamiento lento |
| Capitolio | 42.3 s – 53.8 s | acercamiento lento |

Para cambiar una foto: reemplaza el JPG en `assets/fotos/`, regenera `fotos.js` (cada foto es un `data:image/jpeg;base64,...`) y vuelve a renderizar. Si falta una foto, aparece el recuadro `[FOTO: …]`.

## La narración (ElevenLabs "Jaider - Narration Spanish")

El video ya está sincronizado con `audio/narracion.mp3`: los tiempos de cada frase (medidos en las pausas del audio) están en `NARRACION`, al principio de `escena.html`. Escenas, subtítulos, contador, flechas, sello, calendario y efectos se calculan a partir de ahí.

Si cambias la narración: reemplaza `audio/narracion.mp3`, ajusta los `[inicio, fin]` de cada frase y ejecuta `rm salida/_video_sin_audio.mp4 && ./montar.sh`. La música baja sola cuando habla la voz (sidechain) y la mezcla sale a -14 LUFS (volumen estándar de TikTok/Reels).

## Escenas

| Tiempo | Qué pasa |
|---|---|
| 0 – 9.5 s | Banner rojo **ÚLTIMA HORA**, foto de Jensen, titular "CEO de Nvidia admite una infidelidad" + etiqueta "SEGÚN REPORTES" |
| 9.5 – 18 s | Rótulo **JENSEN HUANG – CEO y fundador de Nvidia**, contador animado hasta **+$200,000,000,000** (fortuna estimada) |
| 18 – 30.8 s | Foto y rótulo de **Alice Huang – Ejecutiva de Megaspeed (Singapur)** → mapa animado EE.UU. → Singapur → China con flechas entre personas + tarjeta de cita **The New York Times** ("PRESUNTO · NO CONFIRMADO") |
| 30.8 – 42.3 s | Correo interno tecleado, frase subrayada/resaltada, sello "Nvidia abre investigación independiente" (fuente: CNBC) y línea de tiempo |
| 42.3 – 53.8 s | Pantalla dividida en 3: Trump / China / Congreso, con calendario "18 NOV" |
| 53.8 – 61.1 s | "Por ahora no hay pruebas…" y la gran pregunta palabra por palabra: **¿Puede sobrevivir el rey de la IA?** |
| 61.1 – 66.5 s | Encuesta: **1 = Debe renunciar / 2 = Debe seguir** · "Comenta 1 o 2" |
| 66.5 – 70 s | Tu cierre de Capital Curioso |

Durante todo el video: subtítulos palabra por palabra (la palabra que suena se marca en rojo) y una cinta inferior "EN DESARROLLO".

## Volver a generarlo

Necesita Node 18+, Playwright (Chromium), Python 3 con `numpy` + `scipy`, y `ffmpeg`.

```bash
node render.mjs            # cuadros -> salida/_video_sin_audio.mp4 (~2 min)
./montar.sh                # música + efectos + cierre -> salida/capital_curioso_jensen_huang.mp4
```

Para ver la animación en el navegador sin renderizar: abre `escena.html` (tiene botón de reproducir y barra de tiempo).
Para revisar cuadros sueltos: `node render.mjs --stills 3,12,30`.
