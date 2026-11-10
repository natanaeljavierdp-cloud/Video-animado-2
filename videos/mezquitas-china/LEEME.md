# Capital Curioso — Mezquitas en China (vertical 9:16, 70 s)

Video final: `capital_curioso_mezquitas_china.mp4` (1080x1920, 30 fps, AAC estéreo, −14 LUFS).

Regenerar (requiere Python 3 con Pillow + numpy, y ffmpeg):

```
python3 musica.py      # música de suspenso + efectos -> build/musica.wav
mkdir -p build/intro && ffmpeg -i assets/capital_curioso_intro.mp4 build/intro/%04d.png
python3 render.py      # imagen -> build/video_sin_audio.mp4
./mezclar.sh           # voz + música con ducking -> mp4 final
```

- `assets/palabras.json`: transcripción de la narración con tiempos por palabra (sincroniza escenas y subtítulos).
- `assets/fotos/`: fotos aportadas. Para cambiar una foto basta con reemplazar el archivo con el mismo nombre.
