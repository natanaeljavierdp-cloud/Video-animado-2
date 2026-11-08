#!/bin/bash
# Uso: scripts/stills.sh nombre frame1 frame2 frame3 frame4  -> genera una cuadrícula 2x2
export REMOTION_BROWSER=${REMOTION_BROWSER:-/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell}
OUT=${STILLS_DIR:-out/stills}; mkdir -p $OUT
name=$1; shift
files=()
for fr in "$@"; do
  npx remotion still src/index.ts GranjaIntegrada $OUT/${name}_$fr.jpg --frame=$fr --scale=0.5 2>&1 | grep -v "^\s*at " | grep -iE "rror" | head -5
  files+=(-i $OUT/${name}_$fr.jpg)
done
ffmpeg -loglevel error -y "${files[@]}" -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack" $OUT/${name}_grid.jpg
