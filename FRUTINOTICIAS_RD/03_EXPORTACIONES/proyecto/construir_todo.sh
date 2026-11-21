#!/usr/bin/env bash
# Reconstruye el lanzamiento completo de FRUTINOTICIASRD desde los clips originales.
# Requisitos: ffmpeg/ffprobe, python3 con numpy, scipy, pillow, opencv-python-headless, faster-whisper.
# Fuentes: fuentes Inter / Inter Display en /usr/share/fonts/opentype/inter/
set -euo pipefail
cd "$(dirname "$0")"
SRC=../../01_ESCENAS_EN_ORDEN
[ -f build/transcripcion_large-v3.json ] || python3 scripts/01_transcribir.py "$SRC" build/transcripcion_large-v3.json large-v3
[ -f build/zonas_cabeza.json ]           || python3 scripts/02_analizar_zonas.py "$SRC" build/zonas_cabeza.json
# (03_extraer_mapa_rd.py solo hace falta si se regenera assets/rd_silueta.json desde world-atlas)
python3 scripts/04_audio.py      # voz igualada + música/SFX originales + ducking -> build/mezcla.wav
python3 scripts/05_render.py     # gráficos, subtítulos, transiciones y exportación H.264/AAC
python3 scripts/06_verificar.py  # transcribe el MP4 final y genera hojas de contacto
