# Motion graphic — Sandoval Legal (15 s)

Secuencia cinematográfica de 15 segundos (1920×1080, 30 fps) con tipografía cinética,
transiciones de formas, elementos 3D y cámara en movimiento continuo. Hecha con Three.js
y renderizada fotograma a fotograma, así que cada render sale idéntico.

**Video listo:** `output/sandoval-legal-motion-web.mp4`

## Guion

| Tiempo | Escena | 3D | Tipografía / transición |
|---|---|---|---|
| 0–3 s | Origen | El polvo dorado se reúne en un rombo de oro (el monograma) | «CADA CASO»: las letras suben desenfocadas mientras el espaciado se cierra |
| 3–6.5 s | Historia | Las partículas se convierten en templo; las columnas acanaladas suben escalonadas | Un rombo cubre y abre la pantalla · «TIENE UNA / *historia.*» con giro 3D de las letras |
| 6.5–10 s | Valores | La balanza sube, oscila y se equilibra dentro de un halo de partículas | Barras redondeadas barren la pantalla · «JUSTICIA → CLARIDAD → COMPROMISO» |
| 10–12.5 s | Portal | La cámara vuela a través de un anillo de oro | Frase de cierre palabra por palabra, que pasa de largo junto a la cámara |
| 12.5–15 s | Logo | Las partículas dibujan el rombo doble | Un círculo se transforma en rombo · «S» + «SANDOVAL LEGAL» + «SOLUCIÓN JURÍDICA» |

La cámara sigue una spline de Hermite (velocidad continua entre claves), con un leve
movimiento de cámara en mano, cambios de distancia focal y un giro durante el vuelo.
Acabado: bloom, viñeta, grano de película y bandas cinemascope.

## Uso

```bash
cd video
npm install
npm run preview          # http://localhost:4800 (reproducción + barra de tiempo)
npm run render           # output/sandoval-legal-motion.mp4 (requiere Playwright + ffmpeg)
node render.mjs --stills # solo fotogramas clave en output/stills/
```

Para renderizar en tu equipo: `npm i -D playwright && npx playwright install chromium`
y tener `ffmpeg` instalado. El master sale con CRF 17 (~31 MB); la versión web del repo
se recodificó con `ffmpeg -i master.mp4 -c:v libx264 -crf 23 -movflags +faststart web.mp4`.

Textos, tiempos y colores están en `main.js` (`updateType`, `camKeys`, `morphs`).

## Audio

- `output/audio/voz-jaider.mp3`: narración (voz «Jaider – Narration Spanish», ElevenLabs).
- `audio/score.py`: banda sonora dramática original, sintetizada (drones, cuerdas, braams,
  tambores, risers y campanas en los cortes del video). `python3 audio/score.py output/audio/musica.wav`
  (requiere `numpy` y `scipy`).
- `audio/mix.sh`: coloca cada frase de la voz en su escena, baja la música bajo la voz
  (sidechain), normaliza a −14 LUFS y une todo al video → `output/sandoval-legal-motion-con-audio.mp4`.
