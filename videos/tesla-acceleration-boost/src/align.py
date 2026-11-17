"""Force-align the dialogue to a 16 kHz s16le mono raw file -> words.json [{w, s, e, line, spk}]."""
import sys, json, re
from pocketsphinx import Decoder
from script import LINES
SPOKEN = {"2000": "two thousand dollars", "400": "four hundred dollars", "44": "four point four", "39": "three point nine"}
disp, norm, idx = [], [], []
for li, (spk, text, _) in enumerate(LINES):
    for w in text.replace("...", " ").split():
        core = re.sub(r"[^A-Za-z0-9']", "", w)
        toks = SPOKEN.get(core.lower(), core.lower()).split()
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
d.set_align_text(" ".join(norm))
d.start_utt(); d.process_raw(open(sys.argv[1], "rb").read(), full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ("<s>", "</s>", "<sil>", "[NOISE]")]
assert len(segs) == len(norm), (len(segs), len(norm))
out = []
for k, (w, li, spk) in enumerate(disp):
    a = idx[k]; b = idx[k + 1] if k + 1 < len(idx) else len(norm)
    out.append(dict(w=w, s=round(segs[a][1], 2), e=round(segs[b - 1][2], 2), line=li, spk=spk))
json.dump(out, open(sys.argv[2], "w"))
import numpy as np                       # plausible = per-token duration in range AND voiced audio under the word
pcm = np.frombuffer(open(sys.argv[1], "rb").read(), np.int16).astype(np.float32)
floor = np.percentile(np.abs(pcm), 20) + 1
ntok = [(idx[k + 1] if k + 1 < len(idx) else len(norm)) - idx[k] for k in range(len(disp))]
def voiced(o): seg = pcm[int(o["s"] * 16000):int(o["e"] * 16000)]; return len(seg) and np.abs(seg).mean() > 4 * floor
ok = sum(1 for o, n in zip(out, ntok) if 0.03 <= o["e"] - o["s"] <= 0.8 * n and voiced(o))
print(f"words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%)")
for li in range(len(LINES)):
    ws = [o for o in out if o["line"] == li]; print(li, ws[0]["s"], ws[-1]["e"], ws[0]["w"], "..", ws[-1]["w"])
