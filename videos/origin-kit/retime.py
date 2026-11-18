"""Cut the raw dialogue at the quietest point between lines and re-space it: first word at 0.3 s, tight line gaps, a
breath at scene changes, one silent beat before the line to the viewer. Gaps are scaled so the video lands near TARGET s.
Usage: python retime.py VIDEO_DIR RAW.wav RAW_WORDS.json VOICE.wav WORDS.json"""
import json, sys, wave, os, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('script', os.path.join(sys.argv[1], 'src', 'script.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
LINES = S.LINES
LEAD, GAP, SCENE_GAP, BEAT, TAIL, TARGET = 0.27, 0.24, 0.75, 1.1, 2.4, 45.0
src, wj, dst, wout = sys.argv[2:6]
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj))
first = {li: min(o["s"] for o in words if o["line"] == li) for li in range(len(LINES))}
last = {li: max(o["e"] for o in words if o["line"] == li) for li in range(len(LINES))}
def quiet(t0, t1):
    i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); n = int(.02 * sr)
    if i1 - i0 <= n: return (i0 + i1) // 2
    e = [np.abs(a[i:i + n]).mean() for i in range(i0, i1 - n, hop)]
    return i0 + hop * int(np.argmin(e)) + n // 2
cuts = [int(max(0, first[0] - .03) * sr)] + [quiet(last[li] - .08, first[li + 1] + .08) for li in range(len(LINES) - 1)] + [len(a)]
segs = []
for li in range(len(LINES)):
    c0 = max(cuts[li], int((first[li] - .06) * sr)) if li else cuts[0]
    c1 = min(cuts[li + 1], int((last[li] + .1) * sr))
    segs.append((c0, c1))
speech = sum(c1 - c0 for c0, c1 in segs) / sr
gaps = [BEAT if li + 1 == len(LINES) - 1 else SCENE_GAP if LINES[li + 1][2] != LINES[li][2] else GAP for li in range(len(LINES) - 1)]
k = min(1.8, max(.8, (TARGET - TAIL - LEAD - speech) / sum(gaps)))
print(f"speech {speech:.2f}s gap scale {k:.2f}")
out, t, shift = [np.zeros(int(LEAD * sr), np.float32)], LEAD, {}
fade = int(.006 * sr)
for li, (c0, c1) in enumerate(segs):
    seg = a[c0:c1].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    shift[li] = t - c0 / sr; out.append(seg); t += len(seg) / sr
    if li + 1 < len(LINES):
        g = gaps[li] * k
        out.append(np.zeros(int(g * sr), np.float32)); t += g
y = np.concatenate(out).astype(np.int16)
with wave.open(dst, "wb") as o: o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(y.tobytes())
for o in words: o["s"] = round(o["s"] + shift[o["line"]], 3); o["e"] = round(o["e"] + shift[o["line"]], 3)
json.dump(words, open(wout, "w"))
print("dur", round(len(y) / sr, 2), "first word", words[0]["s"], "last word end", words[-1]["e"], "video", round(words[-1]["e"] + TAIL, 2))
