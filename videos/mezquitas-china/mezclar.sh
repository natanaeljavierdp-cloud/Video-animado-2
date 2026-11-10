#!/bin/bash
# Mezcla voz + música (con ducking) y codifica el video final.
set -e
cd "$(dirname "$0")"
ffmpeg -v error -y -i build/video_sin_audio.mp4 -i assets/narracion.mp3 -i build/musica.wav -filter_complex "\
[1:a]aresample=44100,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,volume=1.0,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];\
[2:a]volume=0.30[m];\
[m][vsc]sidechaincompress=threshold=0.04:ratio=5:attack=30:release=500[md];\
[v][md]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,atrim=0:70.2[a]" \
 -map 0:v -map "[a]" -c:v libx264 -preset slow -b:v 5M -maxrate 7M -bufsize 10M -pix_fmt yuv420p -profile:v high -movflags +faststart \
 -c:a aac -b:a 192k -ar 44100 -t 70.2 capital_curioso_mezquitas_china.mp4
ls -la capital_curioso_mezquitas_china.mp4
