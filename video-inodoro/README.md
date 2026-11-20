# ¿Qué pasa cuando jalas la cadena del inodoro? — video explicativo animado

Video vertical 1080x1920, 30 fps, 100 % gráficos animados generados por código (Python + Cairo).

## Archivos

| Archivo | Qué hace |
|---|---|
| `words.json` | Transcripción de la narración con tiempos por palabra (faster-whisper `medium`, español). |
| `common.py` | Paleta, easing, cámara con spline (movimiento continuo), polilíneas y adornos de cómic. |
| `world_city.py` | Barrio isométrico tipo dron, alcantarillado en rayos X y planta de tratamiento. |
| `world_bath.py` | Corte de la casa y del inodoro (tanque, flotador, válvula, tapón, sifón, desagüe). |
| `world_plant.py` | Planta de tratamiento en corte: rejillas, bacterias, clarificador y río. |
| `captions.py` | Subtítulos de 1-4 palabras, arriba al centro, clave en rojo, relleno en gris. |
| `render.py` | Línea de tiempo, transiciones con zoom + fundido, textura de papel y render MP4. |
| `audio.py` | Música de fondo y efectos sintetizados (propios, libres de derechos) + mezcla con la voz. |

## Cómo regenerar

```bash
pip install pycairo numpy pillow scipy faster-whisper
python3 audio.py ruta/a/narracion.mp3        # -> out/mezcla.wav
python3 render.py video 4                     # -> out/video_sin_audio.mp4
ffmpeg -i out/video_sin_audio.mp4 -i out/mezcla.wav -c:v copy -c:a aac -b:a 192k -shortest inodoro_por_dentro.mp4
python3 render.py frames 12.7 26 68.6         # fotogramas de prueba
```

Fuente de subtítulos: Inter Display Black (SIL Open Font License).
