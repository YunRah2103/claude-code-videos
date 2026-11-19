"""Force-align the dialogue to a 16 kHz s16le mono raw file -> words.json [{w, s, e, line, spk}]. Run from an episode's src.
script.py may define SPOKEN (display word -> spoken words) and DICT (extra pronunciations, CMU phones)."""
import json, os, re, sys
sys.path.insert(0, os.getcwd())
from pocketsphinx import Decoder
import script
LINES = script.LINES
SPOKEN = {k.lower(): v for k, v in getattr(script, 'SPOKEN', {}).items()}
disp, norm, idx = [], [], []
for li, (spk, text, *_r) in enumerate(LINES):
    for w in text.replace("...", "").split():
        w = w.lstrip('*')
        core = re.sub(r"[^A-Za-z0-9'\-]", "", w).strip("-")
        toks = SPOKEN.get(core.lower(), core.lower().replace('-', ' ')).split()
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
for word, ph in getattr(script, 'DICT', {}).items(): d.add_word(word, ph, True)
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
ntok = [(idx[k + 1] if k + 1 < len(idx) else len(norm)) - idx[k] for k in range(len(idx))]
# plausible: >= 30 ms for one-letter words ('a'), else >= 60 ms; <= 1.2 s per spoken token (e.g. "$999" = 5 tokens)
ok = sum(1 for o, n in zip(out, ntok) if (0.03 if len(o["w"].strip(".,?!")) == 1 else 0.06) <= o["e"] - o["s"] <= 1.2 * n)
print(f"words {len(out)} plausible {ok} ({100*ok/len(out):.1f}%)")
for li in range(len(LINES)):
    ws = [o for o in out if o["line"] == li]; print(li, ws[0]["s"], ws[-1]["e"], ws[0]["w"], "..", ws[-1]["w"])
