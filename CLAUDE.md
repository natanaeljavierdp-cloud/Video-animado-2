# Instrucciones permanentes — videos de Capital Curioso (@capitalcuriosoo)

El usuario no es programador: hacer todo directamente (render, música, mezcla y entrega del MP4),
sin pedirle que ejecute nada. Responder en español.

## Formatos de video (palabras clave)
- **"investigación"** → tema serio, periodístico y cinematográfico. Leer y seguir
  `formatos/INVESTIGACION.md`. Plantilla: `videos/mezquitas-china/`.
- **"sabías?" / "¿sabías que…?"** → datos curiosos en animación vectorial colorida, como el video del
  Pico Duarte. Leer y seguir `formatos/SABIAS.md`. Plantilla: `videos/pico-duarte/video/`.

## Común a ambos formatos
- Vertical 9:16, 1080×1920, 30 fps, de unos 60 a 70 s, con sonido. Se entrega el MP4 al usuario (SendUserFile).
- La voz de la narración la manda el usuario (Jaider, de ElevenLabs): va dentro del video y todo se
  sincroniza con los tiempos por palabra.
- Música original generada con código (sin derechos de autor), a volumen bajo y con ducking bajo la voz.
- Subtítulos grandes palabra por palabra, con las palabras clave resaltadas.
- Al final, siempre el intro/cierre animado de Capital Curioso (lupa con «?»; archivo en
  `videos/mezquitas-china/assets/capital_curioso_intro.mp4`).
- Usar solo las fotos que mande el usuario; no generar ni inventar imágenes.
- Cada video nuevo va en su propia carpeta `videos/<tema>/`.
