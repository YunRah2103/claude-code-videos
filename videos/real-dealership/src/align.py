"""Force-align an episode's dialogue to a 16 kHz s16le mono raw file -> words.json [{w, s, e, line, spk}].
Usage: python align.py EPISODE_DIR RAW16 OUT.json"""
import sys, os, json, re
from pocketsphinx import Decoder
sys.path.insert(0, os.path.abspath(sys.argv[1]))
from script import LINES, SPOKEN
EXTRA = {"supra": "S UW P R AH", "gr": "G IY AA R", "bz": "B IY Z IY", "prius": "P R IY AH S", "cybertruck": "S AY B ER T R AH K",
         "roadster": "R OW D S T ER", "corolla": "K ER AA L AH", "subaru": "S UW B ER UW", "toyota": "T OY OW T AH",
         "tesla": "T EH S L AH", "phantom": "F AE N T AH M", "retrofit": "R EH T R OW F IH T", "touchscreen": "T AH CH S K R IY N"}
SP = {k.lower(): v for k, v in SPOKEN.items()}
disp, norm, idx = [], [], []
for li, (spk, text, _) in enumerate(LINES):
    for w in text.replace("...", " ").split():
        core = w.lower().strip(".,?!:;\"")
        core = SP.get(core, SP.get(re.sub(r"[^a-z0-9'$,-]", "", core), core))
        toks = [re.sub(r"[^a-z0-9']", "", t) for t in core.replace("-", " ").split()]
        toks = [t for t in toks if t]
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
for t in sorted(set(norm)):
    if d.lookup_word(t) is None:
        if t in EXTRA: d.add_word(t, EXTRA[t], True)
        else: sys.exit(f"OOV: {t}")
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
