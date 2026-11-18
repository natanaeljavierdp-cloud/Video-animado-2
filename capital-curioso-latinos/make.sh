#!/usr/bin/env bash
# Construye capital_curioso_latinos.mp4 (1080x1920, 30 fps) desde cero.
set -euo pipefail
cd "$(dirname "$0")"
node render.mjs frames          # fotogramas de las escenas (0–58,5 s)
python3 audio.py                # música + efectos sintetizados
ffmpeg -v error -y \
  -framerate 30 -i build/frames/f%05d.jpg \
  -i assets/cierre.mp4 \
  -i assets/audio/narracion.mp3 -i build/musica.wav -i build/sfx.wav \
  -filter_complex "\
[0:v]format=yuv420p,setsar=1[a];\
[1:v]fps=30,scale=1080:1920,format=yuv420p,setsar=1,tpad=stop_mode=clone:stop_duration=1[b];\
[a][b]concat=n=2:v=1:a=0[v];\
[2:a]aresample=48000,pan=stereo|c0=c0|c1=c0,volume=1.0[voz];\
[3:a]volume=0.16[mus];\
[4:a]volume=0.42[fx];\
[voz][mus][fx]amix=inputs=3:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[au]" \
  -map "[v]" -map "[au]" -c:v libx264 -preset slow -crf 18 -profile:v high -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 192k -movflags +faststart -t 63 capital_curioso_latinos.mp4
echo "Listo: capital_curioso_latinos.mp4"
