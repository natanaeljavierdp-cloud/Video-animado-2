# Formato «¿SABÍAS?» — Capital Curioso (@capitalcuriosoo)

**Palabra clave:** cuando el usuario dice **"sabías?"** (o «¿sabías que…?»), se refiere al formato
del video del **Pico Duarte y el Lago Enriquillo**: datos curiosos, educativo, alegre y en animación vectorial.

**Proyecto de referencia (plantilla):** `videos/pico-duarte/video/` (app.js, index.html, render.mjs, music.py).
Video aprobado: `videos/pico-duarte/out/pico_duarte_lago_enriquillo.mp4`.
Capturas: `formatos/referencias/sabias_pico_duarte.jpg`.

## Especificaciones técnicas
- Vertical 9:16, 1080×1920, 30 fps, unos 60 s más el cierre de Capital Curioso.
- **Animación 100 % vectorial dibujada en canvas** (HTML + JS, `app.js`), con `render(t)` por fotograma,
  renderizada con Playwright/Chromium + ffmpeg (`render.mjs`).
- Todos los tiempos salen de la voz real (`words.json`, tiempos por palabra), con la voz entrando a los 0,25 s.

## Audio
- Voz **Jaider** (ElevenLabs) dentro del video, sincronizada palabra por palabra.
- **Música original alegre/caribeña generada con código** (`music.py`): marimba, clave, bajo, shaker y pad
  a 98 BPM. Baja sola cuando habla la voz.

## Estilo visual
- **Brillante y colorido**, tipo infografía animada o caricatura plana (sin fotos): fondo azul marino `#0B2A5B`
  con nubes, rojo `#FF4B55`, amarillo `#FFD23F`, crema `#F6F3EC`, verde `#2BB673`, turquesa `#17909C`.
- Tipografías: **Archivo Black** (titulares) + **Poppins** 400–800.
- Ilustraciones dibujadas: montañas, agua animada, animales (cocodrilo, flamenco, iguanas), excursionista,
  **bandera dominicana** ondeando, medallas, iconos.
- **Elemento guía permanente:** un indicador lateral que acompaña el tema (en el Pico Duarte fue un
  **altímetro** que sube y baja, con la «cámara» viajando con la altitud). En cada tema se busca un
  equivalente (termómetro, reloj, contador, mapa…).
- Arriba a la derecha, la etiqueta «@capitalcuriosoo» con la lupa.
- Transiciones con una franja de la bandera.

## Estructura (gancho → datos → interacción)
1. **Gancho** con una comparación o pregunta llamativa («Lo más alto / Lo más bajo»).
2. Datos curiosos con números grandes y animados (+3,095 m, −45 m, «Nº 1 del Caribe»).
3. **Trivia**: tarjeta «TRIVIA DOMINICANA» con opciones A/B/C y cuenta regresiva («Ahora adivina…»).
4. Más datos con ilustraciones (por qué es salado, quién vive ahí, etc.).
5. Mapa resumen («DEL TECHO AL FONDO»).
6. **Encuesta** con barras de porcentaje («¿A cuál irías primero?»), «¡VOTA EN LOS COMENTARIOS!»,
   tarjeta de perfil @capitalcuriosoo con botón **SEGUIR** y cursor que lo pulsa, y luego el cierre animado.

## Subtítulos
- Palabra por palabra, en una píldora oscura con texto blanco grueso y **palabras clave en rojo/amarillo**.

## Tono
- Curioso, positivo y orgulloso de lo dominicano. Fácil de entender, para todo público.
