#!/usr/bin/env bash
# Mezcla: voz (frases colocadas en su escena) + música con ducking, y la une al video.
# Uso: bash audio/mix.sh   (desde video/)
set -euo pipefail
VOZ=output/audio/voz-jaider.mp3
MUS=output/audio/musica.wav
VID=output/sandoval-legal-motion-web.mp4
OUT=output/sandoval-legal-motion-con-audio.mp4

# frase: inicio_en_voz fin_en_voz  velocidad  momento_en_video
SEG=(
  "0.00 0.90  1.05  0.75"   # Cada caso
  "1.24 2.23  1.05  4.00"   # tiene una historia
  "2.66 3.40  1.05  6.95"   # Justicia
  "3.64 4.34  1.05  7.90"   # Claridad
  "4.47 5.32  1.05  8.70"   # Compromiso
  "5.56 7.31  1.10  9.55"   # Comprometidos con tus derechos,
  "7.46 9.12  1.10 11.22"   # en cada paso del camino
  "9.44 10.48 1.10 12.85"   # Sandoval Legal
  "10.75 12.00 1.10 13.85"  # Solución Jurídica
)
F=""; MIX=""
for i in "${!SEG[@]}"; do
  read -r a b sp at <<<"${SEG[$i]}"
  ms=$(python3 -c "print(int($at*1000))")
  F+="[0:a]atrim=$a:$b,asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st=$(python3 -c "print(round($b-$a-0.04,3))"):d=0.04,atempo=$sp,adelay=${ms}|${ms}[v$i];"
  MIX+="[v$i]"
done
F+="${MIX}amix=inputs=${#SEG[@]}:normalize=0,aformat=channel_layouts=stereo,"
F+="highpass=f=80,equalizer=f=3000:t=q:w=1:g=2,loudnorm=I=-16:TP=-2:LRA=7,apad=whole_dur=15[voz];"
F+="[voz]asplit[vz1][vz2];"
F+="[1:a]volume=-5dB[mus];[mus][vz1]sidechaincompress=threshold=0.04:ratio=5:attack=20:release=350[duck];"
F+="[duck][vz2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,atrim=0:15,aresample=48000[a]"

ffmpeg -y -loglevel error -i "$VOZ" -i "$MUS" -filter_complex "$F" -map "[a]" -c:a pcm_s16le output/audio/mezcla.wav
ffmpeg -y -loglevel error -i "$VID" -i output/audio/mezcla.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT"
echo "Listo: $OUT"
