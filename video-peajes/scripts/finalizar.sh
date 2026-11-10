#!/usr/bin/env bash
# Une las partes de video, añade el audio normalizado a -14 LUFS (TikTok/IG/FB) y copia los entregables.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p entrega
ls out/partes/parte-*.mp4 | sed "s#^out/partes/#file '#; s#\$#'#" > out/partes/lista.txt
ffmpeg -v error -y -f concat -safe 0 -i out/partes/lista.txt -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart entrega/peajes-sin-casetas.mp4
cp out/miniatura.png entrega/miniatura-peajes.png
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact entrega/peajes-sin-casetas.mp4
