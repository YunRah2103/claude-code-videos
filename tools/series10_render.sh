#!/bin/bash
# Render one series10 episode: video + cover + motion/loop numbers.  bash tools/series10_render.sh <episode>
set -e
e=$1; R=videos/$e/src/render.py; O=out/$e
python tools/video.py run --log out/logs/render_$e.log -- python $R video $O/voiceover.wav $O/$e.mp4
python $R cover $O/cover.png
python $R safecheck > $O/safecheck.txt || true
python - "$O/$e.mp4" > $O/checks.json <<'PY'
import json, subprocess, sys
import numpy as np
sys.path.insert(0, 'shared'); from motion_score import score
p = sys.argv[1]
m, _ = score(p, 0, 1)
def grab(ss):
    a = ['ffmpeg', '-v', 'error'] + (['-sseof', ss] if ss else []) + ['-i', p, '-vf', 'scale=108:192,format=gray', '-f', 'rawvideo', '-']
    raw = subprocess.run(a, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.float32)
first, last = grab(None)[0], grab('-0.1')[-1]
lufs = subprocess.run(['ffmpeg', '-i', p, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
I = [l for l in lufs.splitlines() if l.strip().startswith('I:')][-1].split()[1]
pr = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate,display_aspect_ratio,sample_rate,channels,bit_rate:format=duration', '-of', 'json', p]))
print(json.dumps(dict(motion_first_s=round(m, 1), loop_diff=round(float(np.abs(first - last).mean()), 2), lufs=float(I), probe=pr)))
PY
cat $O/checks.json | cut -c1-200; tail -1 $O/safecheck.txt
