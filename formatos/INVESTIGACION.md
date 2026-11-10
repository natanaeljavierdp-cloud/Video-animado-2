# Formato «INVESTIGACIÓN» — Capital Curioso (@capitalcuriosoo)

**Palabra clave:** cuando el usuario dice **"investigación"**, se trata de un tema serio, en formato
**periodístico + cinematográfico**, como un documental de investigación o el tráiler de una película.

**Proyecto de referencia (plantilla):** `videos/mezquitas-china/` (render.py, musica.py, mezclar.sh).
Video aprobado por el usuario: `videos/mezquitas-china/capital_curioso_mezquitas_china.mp4`.
Capturas: `formatos/referencias/investigacion_mezquitas*.jpg`.

## Especificaciones técnicas
- Vertical 9:16, 1080×1920, 30 fps, de unos 60 a 70 s (narración más un cierre de 3,5 s).
- MP4 H.264 a unos 5 Mbps (para que pese unos 40 MB), audio AAC estéreo a 192 kbps, **−14 LUFS**.
- Render en Python (Pillow + numpy), con fotogramas en paralelo pasados a ffmpeg (`render.py`).

## Audio
- La narración del usuario (voz **Jaider**, de ElevenLabs) va **dentro** del video.
- Se transcribe con tiempos por palabra (faster-whisper "small"; el modelo está en npm:
  `@skillninja/shortmovie-telop-model-p0..p3`, porque Hugging Face está bloqueado) y **cada escena, rótulo
  y palabra se sincroniza con la voz**.
- Música **original sintetizada** (`musica.py`) de suspenso cinematográfico: cuerdas graves en
  tonalidad menor, pulsos lentos tipo latido, impactos graves en los cortes, *risers*, destellos y sellos.
  Va a volumen bajo y **baja sola** cuando habla la voz (sidechain en `mezclar.sh`).

## Estilo visual
- **Barras negras de cine** arriba y abajo (165 px). En la barra de arriba: «CAPITAL CURIOSO» a la izquierda
  e «INVESTIGACIÓN» en rojo a la derecha.
- Grano de película suave, viñeta oscura, **colores fríos y desaturados** en las fotos.
- Colores de marca: **azul marino `#0A285A`** y **rojo `#FE4A55`** sobre fondo oscuro.
- Tipografías: **Anton** (titulares grandes), **Poppins** 500–900 (subtítulos y rótulos),
  **Playfair Display** (nombre del medio en las tarjetas de fuente), **Special Elite** (documentos).
- Transiciones de cine: fundidos a negro, destellos de luz y cortes al ritmo de la música.
- Fotos con movimiento lento de cámara (zoom suave y paneo tipo documental). **No se generan imágenes**:
  se usan las fotos del usuario. Si falta alguna, se usan gráficos animados (mapas, siluetas, iconos),
  nunca fotos inventadas.

## Elementos periodísticos
- Subtítulos **grandes, palabra por palabra**, con las **palabras clave en rojo** (Poppins 900 con contorno).
- Titulares gigantes en Anton, que entran con un golpe de escala sincronizado con la palabra.
- Rótulos con nombre y lugar (*lower third*: caja azul marino con barra roja) y pin de ubicación.
- **Tarjetas de cita con la fuente** (NYT, Financial Times…): tarjeta clara con barra roja y comillas.
- Documentos en papel con texto resaltado o tachado, franjas negras de censura y sello rojo («CONFIDENCIAL — año»).
- Mapa animado que se ilumina en rojo, contadores, comparación ANTES/DESPUÉS con línea deslizante,
  listas de pasos que se tachan con ✕, interfaz de análisis satelital.
- Una tarjeta **gris neutra** con la versión oficial o la otra parte (equilibrio periodístico).
- Cierre: una pregunta grande + encuesta «1 = … / 2 = …» + «Te leo en los comentarios», y luego
  **el intro/cierre animado de Capital Curioso** (lupa con «?», `assets/capital_curioso_intro.mp4`).

## Reglas editoriales
- Tono **neutral y serio**, como un reportaje.
- **NUNCA** poner banners de «ÚLTIMA HORA», «EN DESARROLLO» ni «EN VIVO».
- Honestidad visual: si una foto no es del lugar del que se habla, poner una nota pequeña
  («Imagen ilustrativa · lugar real»). Las ilustraciones van marcadas como «ilustración» y las recreaciones
  de documentos llevan «Recreación gráfica basada en…». No inventar cifras: si la narración dice «miles»,
  no se pone un número exacto.
