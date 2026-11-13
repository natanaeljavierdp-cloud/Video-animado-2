# BIBLIA DE LA SERIE — LOS MORENOS CHOCOLATE

> **Regla de oro:** antes de hacer cualquier episodio, leer este archivo completo y respetarlo.
> Las voces de abajo son **permanentes**: nunca se cambian. Si un episodio necesita una línea
> nueva, se genera con la misma voz (mismo identificador) y el mismo modelo.

---

## 1. Personajes y voces (permanentes)

Todas las voces son de **ElevenLabs**, modelo **`eleven_v4`** (permite etiquetas de actuación como
`[shouting]`, `[laughs]`, `[softly]`). Todas son masculinas, en español con acento dominicano
(o caribeño cuando no había dominicano con ese tono).

| # | Personaje | Archivo SVG | Personalidad / cómo suena | Voz ElevenLabs (nombre) | ID de voz |
|---|-----------|-------------|---------------------------|-------------------------|-----------|
| — | **Narrador** | — | Voz grave de locutor dominicano, pausada y con misterio. | Chaer – Deep Dominican Spanish Narrator | `6yJbRCDgjQDmHJ6NrRYG` |
| 1 | **Mikibiry** | `01-mikibiry.svg` | Voz media, relajada, tíguere tranquilo. | Ramses Dominican-podcast-entusiast-quiet | `RkTY0BBMA1oYqRLj7BnR` |
| 2 | **El Bolen** | `02-el-bolen.svg` | Voz grave y ronca, se altera fácil. | J . A Pereyra | `KJLY4idZ8qLfELeUA2jA` |
| 3 | **Doble P** | `03-doble-p.svg` | Voz gruesa y fuerte, mandón, el que pone orden. | Yovanny – Institutional Broadcast Baritone | `uc1bP8ode9kpUoLa3zdR` |
| 4 | **El Doblón** | `04-el-doblon.svg` | Voz suave y más aguda, más femenina que la de los demás, habla calmado. El más enfocado. | Eddy | `PnZKmmf2UYhdNFUyNPGg` |
| 5 | **Marino el EPC** | `05-marino-el-epc.svg` | Voz alegre y burlona, el chistoso, se ríe fácil. | Mario – Upbeat & Friendly Dominican | `qGPLsX3HiC7FqSnZTSCe` |
| 6 | **El Sicario** | `06-el-sicario.svg` | Voz seria y seca, habla lento, se pica rápido. | Michael | `1cbIUZoxnknSRNz8qJ6d` |
| 7 | **El NJ** | `07-el-nj.svg` | Voz clara y juvenil, habla rápido, el conciliador. | Wanaby | `CCXmXKZExbF90N5aaPWM` |

### Etiquetas de actuación que se usan por personaje (eleven_v4)
- Narrador: `[deep voice] [dramatically]`
- Mikibiry: sin etiqueta o `[shouting]` cuando discute.
- El Bolen: `[angry] [raspy]`
- Doble P: `[shouting]`, `[dramatically]`
- El Doblón: `[softly] [high voice]` (siempre, para mantener la voz suave y más aguda)
- Marino el EPC: `[laughing]`, `[laughs]`
- El Sicario: `[serious] [slowly]`, o `[angry]` cuando se pica.
- El NJ: `[excited]` o sin etiqueta.
- Risas de grupo: `[laughs harder] Jajajajaja... [laughs] jajajaja.` con la voz de cada uno
  (El Sicario normalmente no se ríe).

### Notas técnicas de voz
- Al mandar el texto a la voz, **quitar los apóstrofes** (`to'` → `to`, `e'` → `e`), porque la voz
  ya se come las "s" sola y el apóstrofe a veces la confunde. En los subtítulos el texto va
  **tal cual está en el guion**, con apóstrofes.
- Los audios se descargan de `elevenlabsusercontent.com` (permitido en la red del entorno).

---

## 2. Forma de hablar

Todos son dominicanos de barrio. Hablan informal, con jerga dominicana, comiéndose las "s" y
cortando palabras: *to', pa', tá, vamo', e', na', verdá, vaina, tíguere, pana, muchacho*.
Nada de formalidad ni de español neutro. Los diálogos se dicen **tal como están escritos** en el
guion de cada episodio.

---

## 3. El lugar (escenario fijo de la serie)

Dibujado en caricatura, con el mismo estilo plano de los personajes (colores sólidos, formas
redondeadas, sin texturas realistas). Basado en las fotos de `referencias-lugar/`.

- Cruce de calles de **tierra y arena clara** en un pueblo dominicano.
- En el centro, una **isleta de cemento en forma de triángulo** con un **árbol enorme y frondoso
  de flores amarillas** que da sombra. Debajo: **sillas plásticas** y **motores** parqueados.
- Al otro lado de la calle: una hilera de **locales bajitos pintados de verde** con **puertas de
  metal enrollables**, y un **colmado** con un letrero que dice solo **"COLMADO"**.
- Al lado, una **casa de dos pisos color verde limón** con **balcones de arcos**, **balaustres
  blancos** y **verja de hierro negra**.
- **Cables de luz** cruzando el cielo, **nubes grandes** con pedazos de cielo azul, **árboles**
  al fondo.
- **No** se copian letreros ni nombres reales de las fotos.

---

## 4. Formato fijo de los episodios

- Video vertical **1080×1920**, **30 fps**, MP4 con audio (H.264 + AAC).
- Duración entre 60 y 90 segundos (la que pida el diálogo).
- Nombre: `morenos-chocolate-epN.mp4`.
- Personajes: se usan los SVG **tal como están**, sin cambiarles la cara. Se animan con sus
  piezas (`cabeza`, `cuerpo`, `brazo-izq`, `brazo-der`, `piernas`; las piernas se dividen en
  izquierda/derecha para caminar).
- El que habla se resalta: la cámara se acerca, mueve cabeza y brazos, y sale un **subtítulo
  grande** con su **nombre** y lo que dice.
- Estilo cinematográfico: planos abiertos, acercamientos, movimientos de cámara suaves.
- Sonido de ambiente bajito (brisa, motores, gente a lo lejos). **Sin música con derechos.**
- Cierre con el título **"LOS MORENOS CHOCOLATE – Episodio N"**.

---

## 5. Registro de episodios

| Ep. | Título / tema | Archivo |
|-----|---------------|---------|
| 1 | Cómo empezaron Los Morenos Chocolate (la discusión por "la Babe" y Checa) | `episodios/morenos-chocolate-ep1.mp4` |

---

## 6. Cómo se produce un episodio (para reutilizar)

- `produccion/motor/motor.js` — escenario fijo, personajes por piezas, motores, sillas,
  libretas/celulares y subtítulos. **No cambiar el escenario entre episodios.**
- `produccion/motor/cine.js` — **estilo cinematográfico obligatorio** (desde el Ep. 1 v2):
  cámara 2.5D con capas a distintas profundidades (cielo, árboles lejanos, edificios, plano
  intermedio con vida del pueblo, isleta/personajes, primer plano) y parallax real; lentes
  (gran angular en planos abiertos, tele en primeros planos); profundidad de campo (fondo
  desenfocado); sombras moteadas de las hojas; rayos de sol y polvo; pétalos cayendo;
  gradación de color de cine, viñeta y grano de película.
- Lenguaje de cámara de la serie: grúa al abrir y al cerrar, travelling lateral, primeros
  planos con tele, planos sobre el hombro (silueta desenfocada del que escucha), planos
  holandeses y cámara en mano en las peleas, zoom brusco cómico, barridos con desenfoque de
  movimiento entre personajes, efecto vértigo (dolly zoom) en las revelaciones.
- `produccion/motor/render.mjs` — dibuja cada cuadro en Chromium y lo codifica con ffmpeg.
- `produccion/epN/` — por episodio: `audio/` (voces descargadas de ElevenLabs),
  `audio_epN.py` (línea de tiempo + mezcla + ambiente sintetizado sin derechos) y `epN.js`
  (gestos, cámara y textos).
- Pasos: generar voces (sección 1) → `python3 audio_epN.py <build>` →
  `node render.mjs ../epN/epN.js <build>/timeline_epN.json <build>/mezcla_epN.wav salida.mp4`.
- Colores de las etiquetas de nombre: Mikibiry `#4FC3F7`, El Bolen `#FF8A65`, Doble P `#EF5350`,
  El Doblón `#EDE7F6`, Marino el EPC `#81C784`, El Sicario `#B0BEC5`, El NJ `#FFD54F`,
  Narrador `#F5C542`.
- Puestos fijos bajo el árbol (de izquierda a derecha): Mikibiry, El Sicario, Marino el EPC,
  El Bolen, Doble P, El Doblón, El NJ. Mikibiry tiene motor amarillo.
- Entrega: recodificar el MP4 final a ~7.8 Mbps en dos pasadas (`-b:v 7800k -pass 1/2`), porque el
  grano de película lo hace pesar >100 MB y GitHub no acepta archivos tan grandes.
