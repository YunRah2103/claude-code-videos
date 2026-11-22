"""Cut the raw dialogue at the quietest point between phrases, re-space it (tight line gaps, a breath at scene changes,
a short comic beat for long pauses inside a line, one silent beat before the last line) and shift word timings to
match. -> vo.wav + words.json"""
import json, sys, wave
import numpy as np
from script import LINES
LEAD, GAP, SCENE_GAP, BEAT, INNER, SPLIT = 0.3, 0.08, 0.36, 0.75, 0.36, 0.5
HOLD = {0: 0.1, 4: 0.1, 11: 0.15}                                  # reveal holds after key lines
src, wj, dst, wout = sys.argv[1:5]
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj))
units = []                               # phrases: split a line where the raw voice pauses for longer than SPLIT
for i, o in enumerate(words):
    if i and o["line"] == words[i - 1]["line"] and o["s"] - words[i - 1]["e"] <= SPLIT:
        units[-1].append(i)
    else:
        units.append([i])
def quiet(t0, t1):                       # quietest 20 ms window between t0 and t1
    i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); n = int(.02 * sr)
    if i1 - i0 <= n: return (i0 + i1) // 2
    e = [np.abs(a[i:i + n]).mean() for i in range(i0, i1 - n, hop)]
    return i0 + hop * int(np.argmin(e)) + n // 2
F = [words[u[0]]["s"] for u in units]; L = [words[u[-1]]["e"] for u in units]
cuts = [int(max(0, F[0] - .03) * sr)] + [quiet(L[k] - .08, F[k + 1] + .08) for k in range(len(units) - 1)] + [len(a)]
out, t, shift = [np.zeros(int(LEAD * sr), np.float32)], LEAD, {}
fade = int(.006 * sr)
for k, u in enumerate(units):
    c0 = max(cuts[k], int((F[k] - .04) * sr)) if k else cuts[0]
    c1 = min(cuts[k + 1], int((L[k] + .07) * sr))
    seg = a[c0:c1].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    for i in u: shift[i] = t - c0 / sr
    out.append(seg); t += len(seg) / sr
    if k + 1 < len(units):
        li, ln = words[u[0]]["line"], words[units[k + 1][0]]["line"]
        if li == ln: g = INNER
        else:
            g = BEAT if ln == len(LINES) - 1 else SCENE_GAP if LINES[ln][2] != LINES[li][2] else GAP
            g += HOLD.get(li, 0.0)
        out.append(np.zeros(int(g * sr), np.float32)); t += g
y = np.concatenate(out).astype(np.int16)
with wave.open(dst, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes())
for i, o in enumerate(words): o["s"] = round(o["s"] + shift[i], 3); o["e"] = round(o["e"] + shift[i], 3)
json.dump(words, open(wout, "w"))
print("dur", round(len(y) / sr, 2), "first word", words[0]["s"], "last word end", words[-1]["e"])
for li in range(len(LINES)):
    ws = [o for o in words if o["line"] == li]; print(li, ws[0]["s"], ws[-1]["e"])
