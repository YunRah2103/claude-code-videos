"""Force-align one scene's dialogue to a 16 kHz s16le mono raw file -> words json [{w, s, e, line, spk}].
Usage: python align.py SCENE raw16.raw out.json   (line = global index into script.LINES)"""
import sys, json, re
from pocketsphinx import Decoder
from script import LINES, SPOKEN
EXTRA = {"insanely": "IH N S EY N L IY", "ecoboost": "IY K OW B UW S T", "hellcat": "HH EH L K AE T",
         "fratzonic": "F R AE T S AA N IH K", "motortrend": "M OW T ER T R EH N D"}
def toks(w):
    core = w.strip('!?.,;:')
    key = core.lower() if core.lower() in SPOKEN else core
    if key in SPOKEN: return SPOKEN[key].split()
    return re.sub(r"[^A-Za-z0-9' ]", "", core.replace('-', ' ')).lower().split()
scene = int(sys.argv[1])
disp, norm, idx = [], [], []
for li, (spk, text, sc) in enumerate(LINES):
    if sc != scene: continue
    for w in text.split():
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks(w)
d = Decoder(samprate=16000, bestpath=False)
for k, v in EXTRA.items(): d.add_word(k, v, True)
d.set_align_text(" ".join(norm))
d.start_utt(); d.process_raw(open(sys.argv[2], "rb").read(), full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ("<s>", "</s>", "<sil>", "[NOISE]")]
assert len(segs) == len(norm), (len(segs), len(norm))
out = []
for k, (w, li, spk) in enumerate(disp):
    a = idx[k]; b = idx[k + 1] if k + 1 < len(idx) else len(norm)
    out.append(dict(w=w, s=round(segs[a][1], 2), e=round(segs[b - 1][2], 2), line=li, spk=spk))
json.dump(out, open(sys.argv[3], "w"))
ok = sum(1 for o in out if 0.06 <= o["e"] - o["s"] <= 1.6)
print(f"scene {scene} words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%)")
