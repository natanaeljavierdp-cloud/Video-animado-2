# Instrucciones de renderizado

## Requisitos
- Python 3.10+ con `numpy` y `Pillow` (probado con numpy 2.5 y Pillow 12.3).
- FFmpeg con `libx264` y `aac`.
- Sin otras dependencias. Tipografía Poppins incluida en `capital-curioso/assets/fuentes/` (OFL).

## Estructura
```
capital-curioso/
  assets/
    logo.png                      logotipo (extraído del cierre oficial)
    fuentes/                      Poppins (OFL)
    fotos/                        5 imágenes proporcionadas (rotuladas como ilustrativas)
    audio/narracion_combustibles.mp3   locución proporcionada
    musica/combustibles_tema_original.wav  música original generada por audio.py
    referencias/capital_curioso_cierre.mp4  cierre oficial (se usa tal cual)
  src/marca.py                    colores, fuentes y medidas de la marca
  combustibles/
    src/tiempos.py                escenas y subtítulos (tiempos de la narración)
    src/render.py                 motor de imagen (PIL → FFmpeg)
    src/audio.py                  música, efectos, mezcla y normalización
    transcripcion_palabras.json   marcas de tiempo por palabra de la locución
    salida/                       entregables
```

## Pasos (desde `capital-curioso/combustibles/`)
```bash
python3 src/audio.py salida                                 # música + efectos + mezcla (≈40 s)
python3 src/render.py video salida/_video_sin_audio.mp4     # 1,992 fotogramas (≈1.5 min con 4 núcleos)
ffmpeg -y -i salida/_video_sin_audio.mp4 -i salida/mezcla_final.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest \
  -movflags +faststart salida/capital_curioso_combustibles.mp4
python3 src/render.py portada salida/portada_combustibles.png
```
Otras opciones:
- `python3 src/render.py frame 25.0 prueba.png` — un fotograma suelto para revisar.
- `python3 src/render.py video salida/limpio.mp4 --sin-subtitulos` — versión sin subtítulos quemados (para subir `subtitulos.srt` aparte).

## Cambiar la narración
Si se graba una nueva locución:
1. Reemplazar `assets/audio/narracion_combustibles.mp3`.
2. Obtener los tiempos por palabra (se usó `faster-whisper`, modelo `medium`, idioma `es`, `word_timestamps=True`) y actualizar `ESCENAS` y `SUBTITULOS` en `src/tiempos.py`. Los tiempos de las animaciones dentro de cada escena están en `render.py` (por ejemplo, `prog(T, 14.25, …)` = aparece el "7" a los 14.25 s de la voz).
3. Volver a ejecutar los pasos anteriores.

## Especificaciones del archivo final (verificadas con ffprobe)
- 1080×1920 (9:16), 30 fps constantes, H.264 High, yuv420p, CRF 17, `faststart`.
- AAC-LC 48 kHz estéreo 256 kb/s.
- Duración 66.4 s. Sonoridad −14 LUFS integrada, pico verdadero −1.5 dBTP.

## Subtítulos
El MP4 lleva los subtítulos quemados. `subtitulos.srt` contiene los mismos bloques con los tiempos del vídeo final. Si la plataforma activa subtítulos automáticos, desactívelos o use la versión `--sin-subtitulos` para evitar duplicados.

## Antes de publicar
- Confirmar los datos en los enlaces de `fuentes.md` (el entorno de producción no pudo abrir las páginas oficiales directamente).
- Confirmar la licencia de las cinco imágenes del zip.
- La pieza **no** se ha publicado en ninguna red.
