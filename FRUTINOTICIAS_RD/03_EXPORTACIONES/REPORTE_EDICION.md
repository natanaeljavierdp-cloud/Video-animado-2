# REPORTE DE EDICIÓN — FRUTINOTICIASRD · Lanzamiento cinematográfico

## 1. Entregables

| Archivo | Contenido |
|---|---|
| `FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.mp4` | Video final |
| `FRUTINOTICIASRD_LANZAMIENTO_CINEMATOGRAFICO.srt` | Subtítulos en español (archivo aparte, sin marcas de color) |
| `proyecto/` | Proyecto reproducible: `edl.json` (decisiones editables), `scripts/`, `assets/`, `construir_todo.sh` |
| `revision/` | Hojas de contacto, fotogramas de control, verificación de diálogos |

**Especificaciones verificadas con ffprobe:** 1080 × 1920 (9:16), 24 fps (igual que la fuente), H.264 High 4.1, yuv420p, BT.709, CRF 16 (~8,3 Mb/s), AAC-LC 256 kb/s estéreo a 48 kHz, `faststart`. **Duración: 63,67 s (1528 fotogramas).** Sin marcas de agua. La decodificación completa con ffmpeg no da errores.

Los 8 originales no se modificaron: siguen en `01_ESCENAS_EN_ORDEN/` en modo de solo lectura y sus SHA-256 coinciden con `manifest.json`.

## 2. Verificación del orden por el audio real

Transcribí los 8 clips con **faster-whisper large-v3** (con marcas de tiempo por palabra) y los contrasté con el modelo **medium**. Los dos coinciden. **El orden 01→08 es correcto narrativamente y no hubo que reordenar.**

| # | Clip | Diálogo verificado |
|---|---|---|
| 1 | 01_Gancho_de_Apertura | "Señores, atención. Llegó el noticiero que no promete arreglar el país y por eso empezamos bien." |
| 2 | 02_Presentacion_Dania_Frutoles | "Yo soy Dania Frutoles, su presentadora. Soy una fresa, sí, pero aquí no nos tragamos cualquier cuento." |
| 3 | 03_Concepto_FrutinoticiasRD | "Bienvenidos a FrutinoticiasRD, noticias dominicanas, hechos verificados y comentarios con más picante que un ají caribe." |
| 4 | 04_Apagones_y_Tapones | "Tapones, apagones y paciencia. Tres cosas dominicanas. Bueno, la paciencia se nos acaba primero." |
| 5 | 05_Promesas_Politicas | "También hablaremos de promesas políticas. Algunas tienen tanta experiencia hoy que ya deberían estar cobrando pensión." |
| 6 | 06_Frutas_Podridas | "Y si una historia huele raro, investigamos primero. Que frutas podridas ya tiene el colmado." |
| 7 | 07_Humor_Oscuro | "El humor viene oscuro, pero las fuentes bien claras. Porque inventar noticias, eso sí da vergüenza." |
| 8 | 08_Despedida_Final | "Soy Dania Frutoles, esto es FrutinoticiasRD, exprimimos las noticias, no la verdad. Nos vemos." |

## 3. Montaje (línea de tiempo final)

| Bloque | Clip | Entrada → salida (fotogramas fuente) | En el montaje | Recorte |
|---|---|---|---|---|
| Intriga | 01 | 0 → 190 | 0,00 – 7,92 s | ninguno: el gancho suena desde el fotograma 0 |
| Presentación | 02 | 2 → 188 | 7,92 – 15,67 s | silencio inicial y final |
| Identidad | 03 | 2 → 186 | 15,67 – 23,33 s | se quita el **fotograma 189**, un destello de otro plano (defecto del original) |
| Humor | 04 | 3 → 183 | 23,33 – 30,83 s | silencios |
| Humor | 05 | 3 → 190 | 30,83 – 38,63 s | se conserva el sonido final tras "pensión" |
| Credibilidad | 06 | 5 → 190 | 38,63 – 46,33 s | silencio inicial |
| Humor/credibilidad | 07 | 2 → 179 | 46,33 – 53,71 s | silencio final |
| Gran cierre | 08 | 3 → 180 | 53,71 – 61,08 s | se evita el fundido a gris del original |
| Firma de marca | end card | — | 61,08 – 63,67 s | — |

Todos los puntos de corte caen en silencios medidos (RMS por ventanas de 50 ms y transcripción por palabra). **Ningún corte toca una palabra, una sílaba ni un remate.**

## 4. Paquete gráfico

Todo se diseñó por código (Python + Pillow) con la paleta del set: azul eléctrico y azul oscuro, rojo intenso, blanco, plateado metálico y negro. La tipografía es Inter Display.

- **Apertura (0–4,6 s):** destello de revelado de 3 fotogramas, líneas digitales rojas y azules que enmarcan la zona inferior, marca **FRUTINOTICIASRD** metálica con "RD" en rojo, barrido de luz y chips **ESTRENO OFICIAL** y **SÁTIRA Y HUMOR**. No hay intro previa: la primera frase de Dania suena desde 0,2 s.
- **Mapa de República Dominicana (panel superior izquierdo, clips 01 y 03):** la silueta real sale de **Natural Earth 1:10m** (paquete `world-atlas@2.0.2`, ISC; datos de dominio público) e incluye la isla Saona y la isla Beata. El contorno se dibuja de forma animada con brillo, lleva línea de escaneo y franja con los colores de la bandera. Los puntos de ciudad (Santo Domingo y Santiago en el clip 01; además Puerto Plata y Punta Cana en el clip 03) usan coordenadas públicas y se unen con líneas de datos.
- **Rótulo de la presentadora (clip 02, al decir su nombre):** **DANIA FRUTOLES / PRESENTADORA | FRUTINOTICIASRD**. Letras blancas sobre azul oscuro, acento rojo y filo plateado. Entra y sale con barrido suave.
- **Titulares en placa 3D** (bisel, canto extruido y destello): NOTICIAS CON SABOR / DOMINICANO · APAGONES Y TAPONES (el texto parpadea como un apagón cuando Dania dice "apagones") · PROMESAS POLÍTICAS · INVESTIGAMOS PRIMERO (placa más sobria, chip VERIFICACIÓN) · HUMOR SIN FILTROS (placa oscura, el barrido de luz coincide con "bien claras") · ESTRENO OFICIAL.
- **Recursos irónicos discretos:** una batería de **PACIENCIA** que se vacía al decir "la paciencia se nos acaba primero", y una barra de **PROMESA EN PROCESO** que se atasca en **SIGUE CARGANDO...** al decir "cobrando pensión". No muestran cifras, personas reales ni acusaciones.
- **Credibilidad (clip 06):** líneas informativas con pulsos de datos y checks **FUENTES · CONTEXTO · DATOS**. La pantalla queda limpia para el remate "frutas podridas ya tiene el colmado".
- **Barra informativa:** etiqueta roja **SÁTIRA Y HUMOR** y texto en desplazamiento "FRUTINOTICIASRD | NOTICIAS CON SABOR DOMINICANO • SÁTIRA, ACTUALIDAD Y HUMOR • REPÚBLICA DOMINICANA". Aparece solo en los clips 03–05 y 08.
- **Identificador de sátira:** está en los chips de apertura, en la barra, en cada titular y en el end card.
- **Transiciones (7 cortes y la entrada al end card):** barrido luminoso diagonal de **0,33 s**, con núcleo blanco, halo azul y filos rojo y azul, centrado en el corte. Se suman un destello de 2 fotogramas, líneas rojas y azules veloces y un leve *punch-in* del 3,5 % en los 7 fotogramas siguientes. El video se corta en seco para no solapar diálogos.
- **End card (2,6 s):** el último plano desenfocado y oscurecido, el mapa grande dibujándose con las 4 ciudades, la marca, la franja de la bandera, el lema "EXPRIMIMOS LAS NOTICIAS, NO LA VERDAD" (es frase de Dania) y "SÁTIRA Y HUMOR · REPÚBLICA DOMINICANA". Termina con un fundido a negro.

No añadí estadísticas, cifras, titulares reales, personas reales ni micrófonos.

## 5. Protección de Dania y del logotipo

- `02_analizar_zonas.py` detecta en **cada fotograma** de cada clip la caja de la cabeza: rostro de fresa, hojas y cabello. Usa máscaras de color con apertura morfológica y suavizado con mediana. Esto hace falta porque la cámara se acerca dentro de varios clips.
- Al dibujar, cada gráfico decorativo comprueba esa caja (más 26 px de margen) y se desvanece si fuera a invadirla.
- **Resultado medido (`build/qa_overlay.json`):** la capa de gráficos cubre **0,0 %** de la cabeza en los 1466 fotogramas de escena y **0,0 %** de la banda del logotipo del set (y = 360–1000 px).
- La primera versión del panel del mapa rozaba esa banda (0,9 %). La detecté en esta revisión y reduje el panel antes de la exportación final.
- Única excepción deliberada: el barrido de las transiciones cruza el cuadro durante ~0,3 s, atenuado al 35 % sobre la cabeza. Así se ve en las tiras de `revision/transiciones.jpg`.
- No se tocaron la boca, la expresión, la sincronización labial, el color ni el set.

## 6. Subtítulos

Salen de la transcripción verificada. Cada línea toma sus tiempos de las palabras de Whisper. Usan Inter Display ExtraBold de 58 px, blanco con contorno azul noche, y nunca pasan de 2 líneas. Algunas palabras clave van resaltadas en rojo o en azul de marca.

Están centrados en y ≈ 1248 px, debajo del mentón en todos los planos (el punto más bajo de la cabeza es ~1110 px). Todo el texto queda por encima de y ≈ 1566 px: fuera de la franja inferior y del lateral derecho, donde Instagram, Facebook y TikTok ponen su interfaz. La única corrección sobre Whisper fue escribir la marca como **FrutinoticiasRD**.

## 7. Sonido

- **Voz:** es el audio original de cada clip, sin doblaje ni voces nuevas. Lleva un paso-altos de 70 Hz y una reducción de ruido muy suave (`afftdn nr=6`). Cada clip se igualó a −17 LUFS (ajustes de −1,0 a +2,6 dB; el 07 era el más bajo) con microfundidos de 8 ms en los cortes.
- **Música:** es una **composición original sintetizada por el propio script** (`04_audio.py`), sin muestras ni pistas de terceros, así que se puede usar comercialmente. Está en re menor a 100 BPM: pad cinematográfico, bajo pulsante, "reloj" de noticiero, percusión grave y arpegio. Evoluciona por bloques: intriga → presentación con percusión → humor con arpegio → credibilidad con cuerdas graves → subida → cierre. Termina con una **firma sonora** en re mayor con impacto y brillo.
- **SFX (sintetizados):** impacto de apertura, whoosh e impacto suave en cada corte, blips digitales al entrar los gráficos, destellos sobre la marca, checks de verificación y firma final. La lista con tiempos está en `build/sfx_log.json`.
- **Prioridad de la voz:** el ducking automático baja la música ~11 dB mientras Dania habla. La música queda ~15 dB por debajo de la voz. Antes de los remates de los clips 04, 05, 06 y 07 hay **pausas dramáticas** en las que la música calla un instante.
- **Máster:** −14,0 LUFS integrados, pico −1,5 dBFS, sin saturación.
- Los stems `voz.wav`, `musica.wav` y `sfx.wav` se regeneran en `proyecto/build/`. Para usar otra música basta con sustituir la parte de música de `04_audio.py` o mezclar sobre `voz.wav`.

## 8. Revisión final

| Punto | Resultado |
|---|---|
| 1. Orden de las 8 escenas | ✔ Lo confirmé por transcripción y por las hojas de contacto. |
| 2. Diálogos completos | ✔ Volví a transcribir el MP4 exportado: **126/126 palabras presentes y en orden**, con un desfase medio de 0,02 s respecto a lo previsto. La repetición de "Frutinoticias RD" que mostró la transcripción global era un artefacto de Whisper; transcrito aparte, el tramo 53,5–61,5 s la contiene una sola vez (`revision/verificacion_dialogos.json`). |
| 3. La música no tapa la voz | ✔ Lo verifiqué por medición: ducking de ~11 dB y música unos 15 dB por debajo de la voz. No hice una escucha humana (ver limitaciones). |
| 4. Rostro visible | ✔ 0 % de cobertura medida en todos los fotogramas. |
| 5. Logotipo sin cubrir | ✔ 0 % en la banda del logotipo. |
| 6. Gráficos dominicanos correctos | ✔ Silueta de Natural Earth y ciudades con coordenadas reales. |
| 7. Ortografía | ✔ Revisé todos los textos: SÁTIRA, POLÍTICAS, VERIFICACIÓN, REPÚBLICA DOMINICANA, etc. |
| 8. Transiciones fluidas | ✔ Revisé fotograma a fotograma los cortes 02→03 y 08→end card. |
| 9. Estilo uniforme | ✔ Un solo paquete gráfico, una paleta y una tipografía. |
| 10. Sincronía y reproducción | ✔ Video y audio empiezan en 0, 1528 fotogramas, sin errores de decodificación; el desfase máximo medido en una palabra es de 0,43 s y se debe a la imprecisión de tiempos de Whisper, no al montaje. |

## 9. Defectos de los videos originales (no introducidos en la edición)

1. **Clip 08: el logotipo del set está mal escrito** ("Frutinot**ias**RD" y "Frutinot**c**iasRD" en la pantalla trasera). Lo dejé sin tocar porque la instrucción prohíbe alterar el logo y el set. La grafía correcta aparece en los gráficos y en el end card. **Recomiendo regenerar ese clip.**
2. **Clip 08: texto incrustado "Dania Frut:16"** en la superficie del escritorio, abajo a la derecha. Lo **retiré** con un relleno localizado por interpolación horizontal, solo sobre los píxeles del texto y lejos de Dania y del logo. El método está en `limpiar_texto()` de `05_render.py` y las coordenadas en `edl.json`. Si se mira muy de cerca puede quedar una leve suavidad en esa zona.
3. **Clip 08:** los últimos fotogramas hacen un fundido a gris. Quedaron fuera del corte.
4. **Clip 03, fotograma 189:** destello de un plano distinto (pared blanca). Recortado.
5. En el clip 03 aparece un rótulo secundario "Frutinoticias" cortado en el borde del set, y en varios clips hay acercamientos de cámara. Ambos son originales y se conservaron.
6. El clip 05 termina con un breve sonido no verbal después de "pensión" (−9 dBFS, en ~7,6 s). Lo conservé porque forma parte de la actuación original.

## 10. Herramientas

- FFmpeg/FFprobe 6.1.1 (decodificación, escalado lanczos 720×1280 → 1080×1920 sin deformar, codificación x264/AAC, loudnorm en dos pasadas).
- Python 3.13 con NumPy, SciPy, Pillow, OpenCV y faster-whisper (large-v3 y medium).
- `world-atlas@2.0.2` (Natural Earth) para la silueta.
- Fuentes Inter e Inter Display (SIL OFL).

Para reconstruir todo: `proyecto/construir_todo.sh`. Para modificar la edición (recortes, textos de titulares, tiempos de los gráficos, subtítulos, pausas dramáticas, niveles) se edita `proyecto/edl.json` y se vuelve a ejecutar.

## 11. Limitaciones

- **No hice escucha humana.** La revisión de audio es instrumental: transcripción automática del exportado, medidas de sonoridad y picos, envolventes y ducking. Conviene que alguien escuche la pieza completa antes de publicarla, sobre todo para valorar el gusto de la música sintetizada.
- La música es original y sintética. Si se quiere una banda sonora de estudio, hay que sustituirla por una pista con licencia comercial, mezclada sobre `voz.wav`.
- Las zonas seguras de las apps cambian según la versión y el dispositivo. El diseño mantiene todo el texto por encima de la franja inferior habitual, pero conviene hacer una prueba de vista previa en cada plataforma.
- El MP4 pesa 68 MB. Es apto para subir a las tres plataformas, que recomprimen de todas formas.
