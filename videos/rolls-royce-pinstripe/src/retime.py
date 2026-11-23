"""Cut raw narration at the quietest point between lines, re-space it (tight gaps, a beat before the twist and the
question), speed it up with ffmpeg atempo (pitch kept) to TARGET seconds, start the first word at 0.3 s.
-> voice.wav + words.json"""
import json, subprocess, sys, wave
import numpy as np
from script import LINES
LEAD, GAP, TARGET, END = 0.3, 0.16, 34.4, 0.7
HOLD = {8: 0.25, 10: 0.12, 11: 0.35}          # extra pause after line index (before twist, deadpan, question)
src, wj, dst, wout = sys.argv[1:5]
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj)); n = len(LINES)
first = {li: min(o["s"] for o in words if o["line"] == li) for li in range(n)}
last = {li: max(o["e"] for o in words if o["line"] == li) for li in range(n)}
def quiet(t0, t1):
    i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); k = int(.02 * sr)
    if i1 - i0 <= k: return (i0 + i1) // 2
    e = [np.abs(a[i:i + k]).mean() for i in range(i0, i1 - k, hop)]
    return i0 + hop * int(np.argmin(e)) + k // 2
cuts = [int(max(0, first[0] - .03) * sr)] + [quiet(last[li] - .08, first[li + 1] + .08) for li in range(n - 1)] + [len(a)]
out, t, shift, fade = [], 0.0, {}, int(.006 * sr)
for li in range(n):
    c0 = max(cuts[li], int((first[li] - .05) * sr)) if li else cuts[0]
    c1 = min(cuts[li + 1], int((last[li] + .09) * sr))
    seg = a[c0:c1].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    shift[li] = t - c0 / sr; out.append(seg); t += len(seg) / sr
    if li + 1 < n:
        g = GAP + HOLD.get(li, 0.0); out.append(np.zeros(int(g * sr), np.float32)); t += g
y = np.concatenate(out)
f = t / (TARGET - LEAD - END)                  # tempo factor
tmp = dst + ".tmp.wav"
with wave.open(tmp, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", f"atempo={f:.4f},adelay={int(LEAD*1000)},apad=pad_dur={END}",
                "-ar", str(sr), "-ac", "1", dst], check=True)
for o in words:
    for k in ("s", "e"): o[k] = round((o[k] + shift[o["line"]]) / f + LEAD, 3)
json.dump(words, open(wout, "w"))
print("tempo", round(f, 3), "first word", words[0]["s"], "last word end", words[-1]["e"])
for li in range(n): print(li, min(o["s"] for o in words if o["line"] == li), max(o["e"] for o in words if o["line"] == li))
