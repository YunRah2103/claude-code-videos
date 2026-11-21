"""Force-align VIDEO_DIR dialogue to a 16 kHz s16le mono raw file -> words.json. Usage: align.py VIDEO_DIR RAW OUT.json"""
import sys, json, re
from pocketsphinx import Decoder
from cfgload import load
C = load(sys.argv[1]); LINES = C.LINES
SPOKEN = C.SPOKEN
disp, norm, idx = [], [], []
for li, (spk, text) in enumerate((l[0], l[1]) for l in LINES):
    for w in text.replace("...", "").split():
        core = re.sub(r"[^A-Za-z0-9']", "", w)
        toks = SPOKEN.get(core.lower(), core.lower()).split()
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
for wd, ph in getattr(C, "DICT", {}).items():
    if d.lookup_word(wd) is None: d.add_word(wd, ph, True)
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
ok = sum(1 for o in out if 0.06 <= o["e"] - o["s"] <= 1.2)
print(f"words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%)")
for li in range(len(LINES)):
    ws = [o for o in out if o["line"] == li]; print(li, ws[0]["s"], ws[-1]["e"], ws[0]["w"], "..", ws[-1]["w"])
