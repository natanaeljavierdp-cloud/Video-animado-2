# Voyager 1 — video vertical 3D (1080x1920, 30 fps)

Video educativo sobre cómo nos comunicamos con la Voyager 1, renderizado 100 % en 3D
con **Three.js** dentro de Chromium sin pantalla (SwiftShader), estilo cómic/toon:

- `MeshToonMaterial` con rampa de 4 tonos, sombras suaves reales (PCF soft).
- Contorno negro fino por "casco invertido" con grosor constante en pantalla (`src/lib.js`).
- Bloom para energía/señales (puntitos dorados y anillos de radio que se expanden en 3D).
- Postproceso: textura de papel + grano + viñeta suave + colores algo apagados.
- Subtítulos 2D encima del render: Nunito Black, arriba al centro, 1–4 palabras,
  claves en rojo, relleno en gris; blanco con halo oscuro en el espacio y negro con
  halo blanco en tierra (`src/subs.js`).
- Tiempos sincronizados con la transcripción por palabra (`words.json`, faster-whisper).
- Música de fondo sintetizada en `music.py` (sin derechos de terceros), a ~-20 dB.

## Archivos

```
src/lib.js      materiales toon, contorno, easing, cámara (Hermite), partículas, anillos, etiquetas
src/models.js   modelos procedurales: Tierra (continentes reales simplificados), Luna, planetas,
                Sol, Voyager 1, reloj, bombillo, módem, monitor, antena de espacio profundo...
src/scenes.js   coreografía de las 8 escenas (todo es función del tiempo t)
src/subs.js     subtítulos
src/main.js     renderer + postproceso + mezcla entre escenas
render.mjs      servidor local + Chromium: `node render.mjs a=0 b=2810 out=out/part.mp4`
                o `node render.mjs stills=1,12.5,40` para fotogramas sueltos
music.py        música de fondo
data/land.json  polígonos de continentes para la textura de la Tierra
```

## Render

```bash
npm install
node render.mjs a=0 b=937 out=out/part0.mp4      # (se puede repartir en varios procesos)
python3 music.py 93.65
# concatenar partes y mezclar voz + música (ver comandos en el historial del commit)
```
