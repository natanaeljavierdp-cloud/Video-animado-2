#!/usr/bin/env bash
# Monta el video final de Capital Curioso · Jensen Huang.
#   ./montar.sh                         -> video sin voz + versión con voz si existe audio/narracion.mp3
#   ./montar.sh otra_voz.mp3            -> usa ese archivo como narración
#   FORMATO=investigacion ./montar.sh   -> formato INVESTIGACIÓN (investigacion.html -> salida/investigacion/)
# Los tiempos de cada frase de la narración están en NARRACION (escena.html).
set -euo pipefail
cd "$(dirname "$0")"
FORMATO="${FORMATO:-noticiero}"
if [ "$FORMATO" = noticiero ]; then ESCENA=escena.html; D=salida; SUF=""; else ESCENA=$FORMATO.html; D=salida/$FORMATO; SUF="_$FORMATO"; fi
mkdir -p "$D"

[ -f "$D/_video_sin_audio.mp4" ] || node render.mjs --escena "$ESCENA" --out "$D"
python3 musica.py "$D/sfx.json" "$D/"

CIERRE=assets/cierre_capital_curioso.mp4
OUT=$D/capital_curioso_jensen_huang${SUF}_sin_voz.mp4

# noticia + cierre animado (3.5 s) y la pista de música/efectos
ffmpeg -y -v error -i "$D/_video_sin_audio.mp4" -i "$CIERRE" -i "$D/musica_y_efectos.wav" \
  -filter_complex "[0:v]fps=30,format=yuv420p,setsar=1[a];[1:v]fps=30,scale=1080:1920,format=yuv420p,setsar=1[b];[a][b]concat=n=2:v=1:a=0[v];[2:a]loudnorm=I=-18:TP=-1.5:LRA=11[m]" \
  -map "[v]" -map "[m]" -c:v libx264 -preset medium -crf 20 -maxrate 6M -bufsize 12M -pix_fmt yuv420p -c:a aac -b:a 192k -ar 44100 -movflags +faststart -shortest "$OUT"
echo "listo: $OUT"

VOZ="${1:-audio/narracion.mp3}"
if [ -f "$VOZ" ]; then
  OUTV=$D/capital_curioso_jensen_huang${SUF}.mp4
  # la música se agacha (sidechain) bajo la narración; mezcla final a -14 LUFS (estándar de TikTok/Reels)
  ffmpeg -y -v error -i "$OUT" -i "$VOZ" -filter_complex \
    "[1:a]aresample=44100,aformat=channel_layouts=stereo,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,asplit=2[v1][v2];\
     [0:a][v1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck];\
     [duck][v2]amix=inputs=2:duration=first:weights='0.55 1':normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart "$OUTV"
  echo "listo: $OUTV"
fi
