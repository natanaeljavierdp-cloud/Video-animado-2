# Video: el rumor del "apagón mundial" del 17 de noviembre (Capital Curioso)

Video vertical de 1080x1920 a 30 fps que dura 75,2 s, lo mismo que la narración.
Archivo final: `output/apagon_17nov_capitalcurioso.mp4`

## Cómo se genera
1. `npm install` (atlas para mapas, íconos lucide y topojson)
2. `node scripts/geo.mjs && node scripts/build-data.mjs`: mapas, íconos y transcripción en `render/data.js`
3. `node scripts/render.mjs <dir> 4`: renderiza los cuadros con Playwright (canvas en `render/app.js`)
4. `python3 scripts/audio.py assets/narracion.mp3 mix.wav`: música de suspenso y efectos sintetizados, mezclados con la voz
5. ffmpeg: concatena los segmentos y agrega el audio (loudnorm -14 LUFS)

`data/words.json` tiene los tiempos de cada palabra de la narración (transcrita con Whisper).
Todas las animaciones y los subtítulos están sincronizados con esos tiempos.
