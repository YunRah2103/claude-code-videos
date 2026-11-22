"""Force-align the dialogue to a 16 kHz s16le mono raw file -> words.json [{w, s, e, line, spk}]."""
import sys, json, re
from pocketsphinx import Decoder
from script import LINES
SPOKEN = {"2022": "twenty twenty two", "2023": "twenty twenty three", "bmw": "b m w", "seventysix": "seventy six"}
disp, norm, idx = [], [], []
for li, (spk, text, _) in enumerate(LINES):
    for w in text.replace("...", "").split():
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
ok = sum(1 for o in out if 0.06 <= o["e"] - o["s"] <= 1.2)
print(f"words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%)")
for li in range(len(LINES)):
    ws = [o for o in out if o["line"] == li]; print(li, ws[0]["s"], ws[-1]["e"], ws[0]["w"], "..", ws[-1]["w"])
