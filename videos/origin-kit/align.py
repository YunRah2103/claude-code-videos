"""Force-align the dialogue to a 16 kHz s16le mono raw file -> words.json [{w, s, e, line, spk}].
Usage: python align.py VIDEO_DIR RAW16 OUT.json | python align.py VIDEO_DIR check  (lists words missing from the dictionary)"""
import sys, json, re, os, importlib.util
from pocketsphinx import Decoder
spec = importlib.util.spec_from_file_location('script', os.path.join(sys.argv[1], 'src', 'script.py'))
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
disp, norm, idx = [], [], []
for li, (spk, text, _) in enumerate(S.LINES):
    for w in text.replace("...", "").split():
        core = re.sub(r"[^A-Za-z0-9']", "", w).lower()
        toks = S.SPOKEN.get(core, core).split()
        disp.append((w, li, spk)); idx.append(len(norm)); norm += toks
d = Decoder(samprate=16000, bestpath=False)
for wd, ph in S.PHONES.items(): d.add_word(wd, ph, True)
if sys.argv[2] == 'check':
    print('missing:', sorted({t for t in norm if d.lookup_word(t) is None})); sys.exit()
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
