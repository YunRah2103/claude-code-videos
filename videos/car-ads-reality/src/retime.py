"""Cut each scene's raw dialogue at the quietest point between lines, re-space it (tight line gaps, a breath plus
transition room at scene changes, holds after reveals) and shift word timings to match.
Usage: python retime.py CACHE_DIR voice.wav words.json  (uses raw{s}.wav + words{s}.json for every scene present, from 0)"""
import json, os, sys, wave
import numpy as np
from script import LINES
LEAD, GAP, SCENE_GAP = 0.27, 0.2, 4.6         # scene gap = whip + 3 s parody-ad cutaway + whip
HOLD = {0: .25, 1: .3, 3: .35, 6: .3, 10: .5, 13: .4, 17: .35, 19: .7, 22: .3, 26: .6, 30: .4, 32: .3, 36: .6, 38: .4,
        42: .6, 43: .3, 46: .3, 48: 2.3, 52: .3, 53: .4, 55: .7, 58: .35, 60: .3, 64: .3, 66: .6,
        67: .5, 68: .3, 69: .4, 70: .4, 71: .3, 72: 1.0}
cache, dst, wout = sys.argv[1:4]
scenes = []
while os.path.exists(os.path.join(cache, f'raw{len(scenes)}.wav')) and os.path.exists(os.path.join(cache, f'words{len(scenes)}.json')):
    scenes.append(len(scenes))
out, t, allw, sr = [], LEAD, [], 24000
out.append(np.zeros(int(LEAD * sr), np.float32))
for sc in scenes:
    w = wave.open(os.path.join(cache, f'raw{sc}.wav')); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    words = json.load(open(os.path.join(cache, f'words{sc}.json')))
    lines = sorted({o['line'] for o in words})
    first = {li: min(o["s"] for o in words if o["line"] == li) for li in lines}
    last = {li: max(o["e"] for o in words if o["line"] == li) for li in lines}
    def quiet(t0, t1):
        i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); n = int(.02 * sr)
        if i1 - i0 <= n: return (i0 + i1) // 2
        e = [np.abs(a[i:i + n]).mean() for i in range(i0, i1 - n, hop)]
        return i0 + hop * int(np.argmin(e)) + n // 2
    cuts = [int(max(0, first[lines[0]] - .03) * sr)] + [quiet(last[l] - .08, first[m] + .08) for l, m in zip(lines, lines[1:])] + [len(a)]
    fade = int(.006 * sr); shift = {}
    for k, li in enumerate(lines):
        c0 = max(cuts[k], int((first[li] - .06) * sr)) if k else cuts[0]
        c1 = min(cuts[k + 1], int((last[li] + .1) * sr))
        seg = a[c0:c1].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
        shift[li] = t - c0 / sr; out.append(seg); t += len(seg) / sr
        g = (SCENE_GAP if k == len(lines) - 1 else GAP) + HOLD.get(li, 0.0)
        if not (sc == scenes[-1] and k == len(lines) - 1):
            out.append(np.zeros(int(g * sr), np.float32)); t += g
    for o in words: o["s"] = round(o["s"] + shift[o["line"]], 3); o["e"] = round(o["e"] + shift[o["line"]], 3)
    allw += words
y = np.concatenate(out).astype(np.int16)
with wave.open(dst, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes())
json.dump(allw, open(wout, "w"))
print("scenes", scenes, "dur", round(len(y) / sr, 2), "first word", allw[0]["s"], "last word end", allw[-1]["e"])
