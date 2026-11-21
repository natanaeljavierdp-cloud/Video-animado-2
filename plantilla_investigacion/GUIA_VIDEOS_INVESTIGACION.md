# Guía: videos de INVESTIGACIÓN de Capital Curioso

Referencia aprobada: `video_cpi/capital_curioso_cpi_noche.mp4` (versión final).
Scripts reutilizables: `video_cpi/render/` (`tr.py`, `plan.py`, `audio.py`, `video.py`).
Todo video de investigación de Capital Curioso (@capitalcuriosoo) se hace igual que ese.

## Formato
- Vertical 1080x1920, 30 fps, MP4 H.264 (preset veryfast), audio AAC 192k, -14 LUFS.
- Duración = narración + cierre animado de Capital Curioso al final (sin overlays encima del cierre).
- Si el archivo pasa de 100 MB, re-codificar a ~8,5 Mbps para poder subirlo a GitHub.

## Estilo visual: thriller geopolítico
- Paleta: azul marino muy oscuro, negro y rojo #D62828.
- Fotos: gradación oscura y fría (sombras navy, medios azul acero) conservando los rojos originales;
  grano de película, viñeta fuerte, brillo rojo suave en una esquina que cambia por escena.
- Movimiento lento y constante en TODAS las fotos (zoom o paneo, Ken Burns). Nunca imágenes quietas.
- Fotos horizontales: dentro de un marco con esquinas rojas sobre la misma foto desenfocada de fondo
  (no estirarlas a pantalla completa).
- Gancho: pantalla negra con estática; los protagonistas aparecen uno por uno en blanco y negro,
  en franjas horizontales separadas por líneas rojas, con impacto en cada uno.
- Recursos gráficos: sellos rojos con textura ("FIRMADO", "NO ANULA NADA", "ORDEN DE ARRESTO VIGENTE"...),
  X rojas, retícula de objetivo, tarjeta de ubicación en tipografía mono con escritura progresiva,
  listas de datos sobre cuadrícula, pantalla dividida para la pregunta final ("LA LEY" vs "LOS MÁS PODEROSOS").
- Transiciones: glitch visual (RGB separado, franjas desplazadas), destello rojo + sacudida en cada impacto, cortes secos.
- SIN banners de "última hora" ni "noticia en desarrollo".
- Usar SOLO las imágenes que entregue el usuario; no buscar ni descargar imágenes.

## Subtítulos
- Arriba, palabra por palabra, en mayúsculas (Anton), blancos con contorno negro; palabras clave en rojo #D62828.
- Sincronizados con transcripción Whisper con tiempos por palabra (faster-whisper "medium").
- Grupos de hasta 4 palabras que se van completando mientras se dicen.

## Audio
- La voz manda el ritmo de todo.
- Música de fondo: la que entregue el usuario (referencia: "Creeping Unease"), ~11 dB por debajo de la voz,
  subiendo de intensidad hasta la pregunta final; elegir el tramo para que el final natural de la pista
  caiga sobre el cierre animado.
- Medio segundo de silencio en la VOZ antes de las frases clave (pantalla negra), pero la MÚSICA NO SE DETIENE.
- Efectos con sonido de tráiler de cine, NUNCA de videojuego:
  impacto grave profundo con cola de sala en cada revelación, whoosh de aire suave en las transiciones,
  oleaje que crece antes de las revelaciones, golpe seco de sello, golpe de madera de mazo, tic de reloj mecánico.
  Prohibido: glitch de 8 bits, pitidos/tonos puros, tecleo, estática fuerte.
- Los efectos van por debajo de la voz (~8 dB) y se callan durante las pausas.

## Colaboraciones
- Si hay marca colaboradora: abajo a la izquierda, pequeño, "En colaboración con" + su logo (opacidad ~70 %)
  durante todo el video (menos en el cierre). Al final, ambos logos con sus @.
- Con Sandoval Legal (@sandoval_legal): no poner nombres de personas relacionadas ni la palabra "asesoría".
