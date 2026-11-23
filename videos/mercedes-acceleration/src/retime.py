"""Cut the raw dialogue at the quietest point between lines, re-space it (tight line gaps, a breath at scene
changes, one silent beat before the last line) and shift word timings to match. -> vo.wav + words.json"""
import json, sys, wave
import numpy as np
from script import LINES
LEAD, GAP, SCENE_GAP, BEAT = 0.3, 0.12, 0.4, 0.35
HOLD = {3: 0.5, 4: 0.45, 6: 0.15}   # 3: subscription expires before the scream; 4: the stall
src, wj, dst, wout = sys.argv[1:5]
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj))
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
