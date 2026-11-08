#!/bin/bash
# frames + mix -> out/seatbelt-fight/seatbelt-fight.mp4 (H.264 yuv420p CRF 17 slow, 60 fps, AAC 256k, 9:16)
set -e; O=out/seatbelt-fight
ffmpeg -v error -y -framerate 60 -i $O/frames/f_%05d.png -i $O/mix.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 17 \
  -pix_fmt yuv420p -vf "setsar=1" -aspect 9:16 -r 60 -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart $O/seatbelt-fight.mp4
