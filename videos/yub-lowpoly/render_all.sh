#!/bin/bash
# Render the three shorts (voice from ~/.cache/yub, music bed out/yub/music.wav) into out/yub/.
set -e
cd "$(dirname "$0")/src"; O=../../../out/yub; C=~/.cache/yub
for n in "toyota toyota_key_fob" "tesla tesla_acceleration_boost" "veyron veyron_tires"; do
  set -- $n
  python $1.py meta $O/$1_meta.json
  python $1.py video $C/$1_voice.wav $O/music.wav $O/$2.mp4 > $O/$1_render.log 2>&1
done
echo all done
