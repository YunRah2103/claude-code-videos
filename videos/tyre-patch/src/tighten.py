"""Shorten long pauses in the single VO take (keeps every word), then speed up 1.08x with pitch kept. vo.wav -> vo_tight.wav"""
import json, subprocess, sys
import numpy as np
from scipy.io import wavfile
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
sr, x = wavfile.read(src); x = x.astype(np.float32) / 32768
w = json.load(open(Path(__file__).with_name('words.json')))
keep, cur = [], 0.0
for a, b in zip(w, w[1:]):
    gap = b['s'] - a['e']
    want = 0.42 if b is w[-9] else 0.24
    if gap > want + 0.08:
        cut0 = a['e'] + want / 2 + 0.04
        cut1 = b['s'] - want / 2 + 0.04
        keep.append((cur, cut0)); cur = cut1
keep.append((cur, len(x) / sr))
f = int(0.006 * sr); ramp = np.linspace(0, 1, f)
parts = []
for s0, s1 in keep:
    seg = x[int(s0 * sr):int(s1 * sr)].copy()
    seg[:f] *= ramp; seg[-f:] *= ramp[::-1]
    parts.append(seg)
y = np.concatenate(parts)
tmp = dst.with_suffix('.tmp.wav'); wavfile.write(tmp, sr, (y * 32767).astype(np.int16))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-af', 'atempo=1.08', '-ar', str(sr), str(dst)], check=True)
tmp.unlink()
print('tight', round(len(y) / sr / 1.08, 2), 's')
