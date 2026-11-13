#!/usr/bin/env bash
# Genera el video final: python3 + ffmpeg (pip install pycairo scipy numpy pillow)
set -euo pipefail
cd "$(dirname "$0")"
python3 render.py     # imágenes animadas  -> out/video_sin_audio.mp4
python3 audio.py      # música + efectos + voz -> out/mezcla.wav
# grano de película ligero + audio AAC, listo para TikTok / Reels / Shorts
ffmpeg -v error -y -i out/video_sin_audio.mp4 -i out/mezcla.wav \
  -vf "noise=alls=4:allf=t" -c:v libx264 -preset slow -crf 20 -maxrate 8M -bufsize 16M -pix_fmt yuv420p \
  -profile:v high -level 4.1 -movflags +faststart \
  -c:a aac -b:a 192k -ar 44100 -shortest \
  capital_curioso_bukele_haiti_rd.mp4
echo "Listo: capital_curioso_bukele_haiti_rd.mp4"
