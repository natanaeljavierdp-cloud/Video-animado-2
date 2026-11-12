---
name: sandoval-legal-video
description: Formato fijo de los videos de Sandoval Legal (@sandoval_legal, República Dominicana). Úsalo SIEMPRE que el usuario mencione "Sandoval Legal" o pida un video, reel o portada para la oficina: vertical 9:16, estilo periodístico-cinematográfico, marco azul marino/dorado, subtítulos palabra por palabra, música de suspenso y cierre animado.
---

# Formato de video Sandoval Legal

Cada vez que el usuario diga "Sandoval Legal", aplica este formato completo, aunque no lo repita en el prompt. El usuario no es programador: hazlo todo tú y al final dile solo lo que tiene que hacer. Escribe siempre en español.

Referencia aprobada: `videos/revision-vehiculos/` (video final, portada, `ENTREGA.md` y `fuente/` con el código). **Parte de ese código como plantilla**: copia `fuente/` y cambia solo las escenas, las fotos y los datos.

## 1. Especificaciones técnicas
- MP4 vertical 1080x1920, 30 fps, H.264 (crf 20, maxrate 12M), AAC 192k, `+faststart`. Duración máxima la que pida el usuario (normalmente 1:15).
- Audio final normalizado a **-14 LUFS**, pico ≤ -1 dBFS.

## 2. Insumos del usuario (úsalos tal cual)
- Narración ya grabada (voz de Eddy). **Nunca generes otra voz, ni la cortes ni la aceleres.** La narración manda los tiempos.
- Fotos enviadas por el usuario. **No busques ni descargues imágenes.** Si falta una, usa un fondo azul marino con un ícono ilustrado. Descarta las fotos con marca de agua y avísale.
- Cierre animado (`sandoval_legal_cierre.mp4`, unos 4 s, 478x850): va pegado **completo** al final, escalado a 1080x1920 y con un fundido de 0,3 s. Ahí no van ni marco ni subtítulos. Normalmente coincide con la frase "Sandoval Legal: donde la ley se entiende".
- Logo: si no llega el archivo, usa `recursos/logo.png` (el logo circular recortado del cierre).

## 3. Identidad visual (siempre igual)
- Colores: azul marino `#0B1526` / `#111F3A`, dorado `#D6B270`, plateado `#B9B9B9`, crema `#F0E8D6` (texto) y rojo apagado `#C4524A` solo para sellos o lo "injustificado".
- Tipografía: **Playfair Display** 900/700 para los títulos, **Cinzel** 700 para etiquetas y marca, **Montserrat** 600-800 para datos y subtítulos (`recursos/fonts/`).
- Marco: línea plateada fina a 22 px del borde, con esquinas doradas en forma de L.
- Etiqueta fija arriba a la izquierda, en dorado y con el tema del video (por ejemplo "CÓDIGO PENAL · LEY 74-25").
- Barra inferior azul marino: logo circular a la izquierda, "SANDOVAL LEGAL" en Cinzel dorado y "@sandoval_legal" en plateado a la derecha.
- Tarjetas de dato: fondo azul marino, borde dorado fino, ícono de la balanza, cita en itálica y "Fuente: …" en plateado.

## 4. Estilo
- Documental de investigación: fotos con zoom y paneo lentos (Ken Burns), oscurecidas y algo desaturadas, viñeta oscura, grano sutil, transiciones limpias con un destello suave y temblor leve en los golpes.
- **Sin** banners de "última hora" ni "noticia en desarrollo".
- Tono informativo y neutral: contenido legal educativo, nunca acusatorio.
- Recursos animados habituales: textos grandes que entran con desenfoque, golpe ("slam") en la palabra clave, contadores numéricos, líneas de tiempo, íconos SVG dorados que aparecen uno a uno, sellos, barras comparativas, pantalla dividida (legal ✔ / injustificada ✖), mapa de RD dorado y encuesta final con barras "en suspenso".

## 5. Subtítulos
- Palabra por palabra, arriba (debajo de la etiqueta), Montserrat 800 a 54 px, en crema; **la palabra que se está diciendo va en dorado**.
- Tiempos sacados de la narración con faster-whisper (`fuente/scripts/transcribe.py`, modelo `medium`, idioma `es`, desde PCM crudo). Revisa a mano: palabras que falten, números ("74-25") y mayúsculas ("Código Penal").
- Frases cortas que cortan en el punto o el signo de interrogación, de una o dos líneas equilibradas.

## 6. Audio
- Música: **de suspenso**. La aprobada es **"Interloper", de Kevin MacLeod** (incompetech.com, CC BY 4.0). El usuario rechazó "Investigations" (muy baja) y "Darkest Child" (no le gustó). Emparéjala con compresor y loudnorm a -13 LUFS antes de mezclar.
- Nivel de la música: unos -25 LUFS en total. Baja sola cuando hay voz y sube un poco en el gancho y en los momentos clave. Fundido de salida al final del cierre.
- Efectos suaves en cada tarjeta y cifra: whoosh en las transiciones, mazo en la palabra clave y sello en los sellos. Están en `recursos/` y se generan con `fuente/scripts/sfx.py`.
- Si la música no es de Kevin MacLeod, debe ser libre de derechos y con su licencia documentada.

## 7. Entrega (siempre)
1. El MP4 final.
2. Portada 1080x1920 con la pregunta gancho y el dato clave en dorado, con el mismo marco y la misma barra.
3. `ENTREGA.md`: archivos, tiempos de cada escena, **texto para publicar** (con aviso de "contenido informativo" y el crédito de la música), **5 hashtags** (incluir #SandovalLegal) y la lista de música y efectos con enlaces y licencias.
4. Guarda todo en `videos/<tema>/`, haz commit y push a la rama de trabajo, y envía los archivos al usuario.
5. Resumen final corto: qué se entregó, qué decisiones tomaste y **qué tiene que hacer el usuario**.

## 8. Notas técnicas del entorno
- Render: página HTML + `timeline.js` con `renderFrame(t)` determinista, capturada con Playwright a 30 fps (4 procesos en paralelo), y de ahí a ffmpeg.
- Red: incompetech.com, raw.githubusercontent.com, npm y pypi suelen funcionar; pixabay, freesound, mixkit y Google Fonts suelen estar bloqueados. Las fuentes se bajan con `npm pack @fontsource/...`.
- Los archivos subidos tienen nombres con prefijo (por ejemplo `cd0a30d6-VID-...mp4`). Identifica cada foto por lo que se ve en ella.
