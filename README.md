# Granja Integrada: Tres Producciones, Un Solo Negocio

Video animado 3D (~64 s, 1920 × 1080, 30 fps, MP4/H.264) para presentar a posibles
inversionistas un proyecto agropecuario en República Dominicana que integra
**gallinas ponedoras**, **cerdas reproductoras** y **cerdos de engorde**, con una
inversión proyectada de **RD$5,000,000** e instalaciones existentes.

El video se genera 100 % por código con [Remotion](https://www.remotion.dev) +
[Three.js](https://threejs.org) (escenas 3D en tiempo real, personajes y animales
modelados y animados proceduralmente), y la banda sonora se sintetiza con Python.

## Escenas

| # | Escena | Contenido |
|---|--------|-----------|
| 1 | El nacimiento de una idea | Sobrevuelo de la granja, título, Miguel camina por el camino y señala las instalaciones. |
| 2 | Las gallinas ponedoras | Interior del gallinero: gallinas que caminan, comen y ponen huevos; trabajadores recogen huevos en bandejas; camión "Huevos frescos" sale hacia el mercado. |
| 3 | Las cerdas reproductoras | Maternidad con lámparas de calor; cerdas echadas amamantando lechones; Miguel entra y observa; un trabajador las alimenta. |
| 4 | El engorde de cerdos | Corral de engorde; trabajador reparte alimento; *time‑lapse* de crecimiento con indicador hasta la meta de ≈100 kg. |
| 5 | El modelo financiero | Vista aérea orbital; tres tarjetas conectadas (Huevos / Reproducción / Engorde) y "INVERSIÓN PROYECTADA: RD$5,000,000". |
| 6 | La visión de futuro | Miguel sonríe satisfecho, la cámara se eleva sobre toda la propiedad y cierra con el logotipo y el lema. |

Personajes y escenario son los mismos en todas las escenas (vestuario fijo en
`src/scenes/common.tsx`, granja exterior única en `src/three/World.tsx`).

> **Nota sobre cifras:** el video no muestra ganancias ni afirma que los huevos
> cubran todos los gastos. Los gráficos son cualitativos y se incluye la leyenda
> "Cifras de ingresos y rentabilidad sujetas a un análisis financiero detallado".

## Estructura

```
scripts/narracion.json   Guion de la narración (una entrada por escena)
scripts/build_audio.py   Voz + música + ambiente + efectos -> public/audio/mix.wav y src/timings.json
src/timings.json         Tiempos de escenas y subtítulos (generado)
src/GranjaVideo.tsx      Composición principal: escenas, fundidos, subtítulos, audio
src/scenes/Scene1..6     Cada escena (cámara, acciones, gráficos)
src/three/Characters.tsx Miguel/trabajadores, gallinas, cerdos, huevos, bandejas
src/three/World.tsx      Cielo, luz, granja, galpones, árboles, camión, letrero
src/ui/                  Subtítulos e íconos/emblema SVG
```

## Cómo regenerar el video

Requisitos: Node 18+, Python 3 con `numpy` y `scipy`, `ffmpeg`, `sox`, `espeak-ng`,
`mbrola` y la voz `mbrola-mx2` (Debian/Ubuntu:
`sudo apt-get install espeak-ng mbrola mbrola-mx2 sox ffmpeg`).

```bash
npm install
npm run audio      # genera public/audio/mix.wav y src/timings.json
npm run studio     # vista previa interactiva (opcional)
npm run render     # -> out/granja-integrada.mp4
```

El render usa WebGL por software (`swangle`), por lo que funciona en servidores sin
GPU. Si Remotion no puede descargar su navegador, indique uno local con
`REMOTION_BROWSER=/ruta/a/chrome-headless-shell npm run render`.

## Versión con audio mejorado

`video/Granja_Integrada_Audio_Mejorado.mp4` usa **el mismo video** (imagen idéntica
bit a bit al original) con una banda sonora nueva:

- Narración **neural** masculina en español (Kokoro‑82M, voz `em_alex`, licencia
  Apache‑2.0, gratuita y generada localmente), con cadena de locutor (filtro de graves,
  EQ de presencia, compresión suave, de‑esser) y nivel igualado entre escenas (±0,3 dB).
- Cada frase se corta en sus pausas naturales y se coloca en el instante exacto en que
  aparece su subtítulo (verificado con Whisper: 15/15 bloques sincronizados).
- Música instrumental estéreo con reverberación; baja 11 dB cuando habla el narrador
  (relación voz/fondo ≈ 17–22 dB).
- Ambiente de granja suave (viento, aves, gallinas, cerdos, camión) atenuado 6 dB bajo la voz.
- Sonoridad normalizada a **−16 LUFS**, pico real ≤ −1,4 dBFS, sin saturación.
  Audio AAC estéreo 48 kHz a 256 kbps.

Regenerar (sin volver a renderizar el video):

```bash
pip install kokoro-onnx soundfile scipy numpy
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd ..
python3 scripts/build_audio_pro.py            # -> public/audio/mix_pro.wav
ffmpeg -i video/granja-integrada.mp4 -i public/audio/mix_pro.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart video/Granja_Integrada_Audio_Mejorado.mp4
python3 scripts/verify_audio.py video/Granja_Integrada_Audio_Mejorado.mp4 <carpeta-whisper>  # opcional
```

## Usar una voz de estudio (opcional)

Si prefiere una locución humana o de un servicio comercial:

1. Genere o grabe un archivo WAV por escena con el texto de `scripts/narracion.json`
   (por ejemplo con **ElevenLabs**, **Azure Speech** — voces `es-MX-JorgeNeural` o
   `es-US-AlonsoNeural` — o **Google Cloud TTS**, o un locutor humano).
2. Guárdelos como `public/audio/voz/escena1.wav` … `escena6.wav`.
3. Ejecute `python3 scripts/build_audio_pro.py` y el comando `ffmpeg` de arriba.

El script detecta esos archivos automáticamente y los procesa, nivela y mezcla igual.
