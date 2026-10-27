#!/bin/bash
# Renders the film in chunks (resumable), then concatenates. usage: render_all.sh outdir
OUT=$1; cd "$(dirname "$0")/.."
N=9135; CH=1523
for i in 0 1 2 3 4 5; do
  A=$((i*CH)); B=$(( (i+1)*CH-1 )); [ $B -ge $N ] && B=$((N-1))
  F=$OUT/part$i.mp4
  [ -s $F ] && continue
  ./render.sh $F.tmp.mp4 $A $B 1 --image-format=jpeg --jpeg-quality=95 --crf=16 --pixel-format=yuv420p > $OUT/part$i.log 2>&1 && mv $F.tmp.mp4 $F
done
for i in 0 1 2 3 4 5; do echo "file 'part$i.mp4'"; done > $OUT/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $OUT/list.txt -c copy $OUT/video_silent.mp4 && echo ALLDONE > $OUT/done.flag
