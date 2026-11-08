# Su tierra es su historia — Sandoval Legal

Video vertical (1080×1920, 30 fps) para TikTok / Reels, generado por código a partir de
`video_spec.json`, las imágenes de `assets/` y la voz `assets/voz.mp3`.

**Voz:** Eddy M (ElevenLabs, modelo eleven_v4), toma 1 del flow
`DNgxnLvGOTuQ8lL0DgXp`. Descárguela de ElevenLabs y guárdela como `assets/voz.mp3`.
Los tiempos de esa toma ya están en `assets/voz_alineacion.json` (transcripción de ElevenLabs).

## Generar el video

```bash
pip install pillow          # ffmpeg también debe estar instalado
python3 sync_voice.py       # sincroniza escenas y subtítulos con la voz
python3 render.py           # -> out/su-tierra-es-su-historia.mp4  (~1–2 min)
python3 render.py --stills  # una imagen por escena en out/stills/ (revisión rápida)
```

## Archivos

| Archivo | Qué es |
|---|---|
| `video_spec.json` | Escenas, textos, movimientos y tiempos (ya ajustados a la voz: 51,9 s) |
| `assets/voz_alineacion.json` | Momento exacto de cada frase de la voz. **Si un subtítulo sale adelantado o atrasado, se corrige aquí** y se vuelve a correr `sync_voice.py` + `render.py` |
| `assets/subtitles_timed.json` | Subtítulos generados (no editar a mano) |
| `docs/storyboard.md`, `docs/guion_locutor.md` | Storyboard y guion originales |
| `docs/muestra_voz/` | Muestra de voz enviada como referencia (no se usa en el video) |
| `docs/video_spec_original_55s.json` | Spec original de 55 s, antes de ajustarla a la voz |

## Pendiente

- `assets/voz.mp3` (toma 1 de Eddy M). Sin ella el video sale mudo.
- Imagen `04_casa_mecedora.png` (hoy sale como “FALTA LA IMAGEN”).
- Confirmar el usuario de Instagram del cierre (`@sanfoval-legal`).
- Música `assets/musica.mp3` y golpe `assets/golpe.mp3` (opcionales: si faltan, se omiten).

Las imágenes son 16:9; el video las muestra en una franja central con movimiento
(Ken Burns) sobre una copia desenfocada. Si se generan en 9:16 se verán a pantalla completa
con más calidad.

Fuentes: Playfair Display y Montserrat (Google Fonts, licencia OFL).
