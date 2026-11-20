#!/bin/bash
# mont.sh out.jpg t1 t2 ... (12 tiempos) -> mosaico 6x2
o=$1; shift; cd out
in=""; f=""; i=0
for t in "$@"; do in="$in -i still_$(printf %.2f $t).jpg"; f="$f[$i]scale=270:-1[s$i];"; i=$((i+1)); done
ffmpeg -v error -y $in -filter_complex "${f}[s0][s1][s2][s3][s4][s5]hstack=6[r1];[s6][s7][s8][s9][s10][s11]hstack=6[r2];[r1][r2]vstack" $o
