#!/usr/bin/env bash
# Normaliza el audio a -14 LUFS (TikTok/IG/FB) sin re-codificar el video y copia los entregables.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p entrega
ffmpeg -v error -y -i out/render-bruto.mp4 -c:v copy -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -movflags +faststart entrega/peajes-sin-casetas.mp4
cp out/miniatura.png entrega/miniatura-peajes.png
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact entrega/peajes-sin-casetas.mp4
