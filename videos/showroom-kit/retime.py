"""Run from an episode src. First word lands at 0.30 s. Cut the raw dialogue at the quietest point between lines, re-space it (tight line gaps, a breath at scene
changes, one silent beat before the last line) and shift word timings to match. -> vo.wav + words.json"""
import json, sys, wave
import numpy as np
sys.path.insert(0, __import__("os").getcwd())
import script
LINES = script.LINES
PH, PT = getattr(script, "PAD", (0.06, 0.1))         # audio kept before the first / after the last word of a line
LEAD, GAP, SCENE_GAP, BEAT = 0.3 - min(0.03, PH), *getattr(script, "GAPS", (0.06, 0.4, 0.8))   # line, scene-change and final-beat gaps
HOLD = getattr(script, "HOLD", {})          # reveal holds after key answers
src, wj, dst, wout = sys.argv[1:5]
TEMPO = getattr(script, "TEMPO", 1.0)                # optional pitch-preserving speed-up of the whole read (ffmpeg atempo)
if TEMPO != 1.0:
    import subprocess
    fast = dst + ".tempo.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"atempo={TEMPO}", fast], check=True); src = fast
w = wave.open(src); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
words = json.load(open(wj))
for o in words: o["s"] = round(o["s"] / TEMPO, 3); o["e"] = round(o["e"] / TEMPO, 3)
first = {li: min(o["s"] for o in words if o["line"] == li) for li in range(len(LINES))}
last = {li: max(o["e"] for o in words if o["line"] == li) for li in range(len(LINES))}
def quiet(t0, t1):                       # quietest 20 ms window between t0 and t1
    i0, i1 = int(max(0, t0) * sr), int(t1 * sr); hop = int(.005 * sr); n = int(.02 * sr)
    if i1 - i0 <= n: return (i0 + i1) // 2
    e = [np.abs(a[i:i + n]).mean() for i in range(i0, i1 - n, hop)]
    return i0 + hop * int(np.argmin(e)) + n // 2
cuts = [int(max(0, first[0] - min(0.03, PH)) * sr)] + [quiet(last[li] - .08, first[li + 1] + .08) for li in range(len(LINES) - 1)] + [len(a)]
LEAD = 0.3 - (first[0] - cuts[0] / sr)                 # first word lands at exactly 0.30 s
out, t, shift = [np.zeros(int(LEAD * sr), np.float32)], LEAD, {}
fade = int(.006 * sr)
for li in range(len(LINES)):
    c0 = max(cuts[li], int((first[li] - PH) * sr)) if li else cuts[0]
    c1 = min(cuts[li + 1], int((last[li] + PT) * sr))     # trim the raw pause; the gap below sets the pace
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
