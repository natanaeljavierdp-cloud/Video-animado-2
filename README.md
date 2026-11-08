# Su tierra es su historia — Sandoval Legal

Video vertical (1080×1920, 30 fps) para TikTok / Reels, generado por código a partir de
`video_spec.json`, las imágenes de `assets/` y la voz `assets/voz.mp3`.

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
| `video_spec.json` | Escenas, textos, movimientos y tiempos (ya ajustados a la voz: 68,6 s) |
| `assets/voz_alineacion.json` | Momento exacto de cada frase de la voz. **Si un subtítulo sale adelantado o atrasado, se corrige aquí** y se vuelve a correr `sync_voice.py` + `render.py` |
| `assets/subtitles_timed.json` | Subtítulos generados (no editar a mano) |
| `docs/storyboard.md`, `docs/guion_locutor.md` | Storyboard y guion originales |
| `docs/video_spec_original_55s.json` | Spec original de 55 s, antes de ajustarla a la voz |

## Pendiente

- Imágenes `04_casa_mecedora.png` y `07_familia_feliz.png` (hoy salen como “FALTA LA IMAGEN”).
- Logo `08_logo.png` (PNG transparente). Si no existe, el cierre sale solo con texto.
- WhatsApp y @usuario del cierre (en `video_spec.json`, escena 8).
- Música `assets/musica.mp3` y golpe `assets/golpe.mp3` (opcionales: si faltan, se omiten).

Las imágenes son 16:9; el video las muestra en una franja central con movimiento
(Ken Burns) sobre una copia desenfocada. Si se generan en 9:16 se verán a pantalla completa
con más calidad.

Fuentes: Playfair Display y Montserrat (Google Fonts, licencia OFL).
