"""Cut the raw dialogue between lines, re-space it (tight gaps, a breath at scene changes, holds after punchlines, one
beat before the last line) and shift word timings. Usage: python retime.py EPISODE_DIR raw.wav raw_words.json voice.wav words.json"""
import json, sys, wave
import numpy as np
sys.path.insert(0, __import__("os").path.abspath(sys.argv[1]))
from script import LINES, HOLD
try: from script import CUT
except ImportError: CUT = {}
LEAD, GAP, SCENE_GAP, BEAT = 0.27, 0.06, 0.45, 0.9
src, wj, dst, wout = sys.argv[2:6]
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj))
# drop filler words (CUT = {line: [word index, ...]}): excise their audio up to the next word and shift what follows
for li, idxs in CUT.items():
    lw = [o for o in words if o["line"] == li]
    for i in sorted(idxs, reverse=True):
        o = lw[i]; nxt = lw[i + 1]["s"] if i + 1 < len(lw) else o["e"]
        i0, i1 = int(o["s"] * sr), int(nxt * sr); dt = (i1 - i0) / sr
        a = np.concatenate([a[:i0], a[i1:]])
        for q in words:
            if q["s"] >= nxt - 1e-6: q["s"] = round(q["s"] - dt, 3); q["e"] = round(q["e"] - dt, 3)
        words.remove(o)
first = {li: min(o["s"] for o in words if o["line"] == li) for li in range(len(LINES))}
last = {li: max(o["e"] for o in words if o["line"] == li) for li in range(len(LINES))}
def quiet(t0, t1):                       # quietest 20 ms window between t0 and t1
    i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); n = int(.02 * sr)
    if i1 - i0 <= n: return (i0 + i1) // 2
    e = [np.abs(a[i:i + n]).mean() for i in range(i0, i1 - n, hop)]
    return i0 + hop * int(np.argmin(e)) + n // 2
cuts = [int(max(0, first[0] - .03) * sr)] + [quiet(last[li] - .08, first[li + 1] + .08) for li in range(len(LINES) - 1)] + [len(a)]
out, t, shift = [np.zeros(int(LEAD * sr), np.float32)], LEAD, {}
fade = int(.006 * sr)
for li in range(len(LINES)):
    c0 = max(cuts[li], int((first[li] - .06) * sr)) if li else cuts[0]
    c1 = min(cuts[li + 1], int((last[li] + .1) * sr))     # trim the raw pause; the gap below sets the pace
    seg = a[c0:c1].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    shift[li] = t - c0 / sr; out.append(seg); t += len(seg) / sr
    if li + 1 < len(LINES):
        g = BEAT if li + 1 == len(LINES) - 1 else SCENE_GAP if LINES[li + 1][2] != LINES[li][2] else GAP
        g += HOLD.get(li, 0.0)
        out.append(np.zeros(int(g * sr), np.float32)); t += g
y = np.concatenate(out).astype(np.int16)
with wave.open(dst, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes())
for o in words: o["s"] = round(o["s"] + shift[o["line"]], 3); o["e"] = round(o["e"] + shift[o["line"]], 3)
json.dump(words, open(wout, "w"))
print("dur", round(len(y) / sr, 2), "first word", words[0]["s"], "last word end", words[-1]["e"])
for li in range(len(LINES)): print(li, round(first[li] + shift[li], 2), round(last[li] + shift[li], 2))
