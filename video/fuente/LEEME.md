# Video "Art. 211 — ¿No es delito?" (Sandoval Legal)

- `index.html` + `anim.js`: animación por fotograma (`window.render(t)`), 1080x1920.
- `words.js`: tiempos palabra por palabra de la narración (transcripción automática).
- `audio.py`: genera la música de fondo y los efectos (whoosh, mazo, sello, glitch).
- `render.js`: captura los fotogramas con Playwright.

Renderizar:
```
node render.js index.html frames 30 0 1
python audio.py <carpeta_audio>
ffmpeg -framerate 30 -i frames/f_%05d.jpg -i mix.wav -c:v libx264 -crf 19 -pix_fmt yuv420p -c:a aac out.mp4
```
