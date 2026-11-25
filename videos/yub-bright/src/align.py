"""Force-align a narration (16 kHz s16le mono raw) -> words json [{w, s, e, line}]. python align.py NAME in.raw out.json"""
import sys, json, re
import numpy as np
from pocketsphinx import Decoder
from script import V
name, raw, dst = sys.argv[1:4]
LINES, SPOKEN = V[name]["lines"], V[name]["spoken"]
disp, norm, idx = [], [], []
for li, text in enumerate(LINES):
    for w in text.split():
        core = re.sub(r"[^A-Za-z0-9']", "", w)
        toks = SPOKEN.get(core.lower(), core.lower()).split()
        disp.append((w, li)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
d.set_align_text(" ".join(norm))
pcm = open(raw, "rb").read()
d.start_utt(); d.process_raw(pcm, full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ("<s>", "</s>", "<sil>", "[NOISE]")]
assert len(segs) == len(norm), (len(segs), len(norm))
out = []
for k, (w, li) in enumerate(disp):
    a = idx[k]; b = idx[k + 1] if k + 1 < len(idx) else len(norm)
    out.append(dict(w=w, s=round(segs[a][1], 2), e=round(segs[b - 1][2], 2), line=li))
# the aligner tends to start the first word at 0.0: use the real energy onset instead
x = np.abs(np.frombuffer(pcm, np.int16).astype(np.float32)); env = np.convolve(x, np.ones(160) / 160, "same")
on = int(np.argmax(env > 0.06 * env.max())) / 16000
out[0]["s"] = round(max(out[0]["s"], on - 0.02), 2)
json.dump(out, open(dst, "w"))
ok = sum(1 for o in out if 0.06 <= o["e"] - o["s"] <= 1.2)
print(f"words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%) onset {on:.2f}")
