import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Once, everyone wanted a Jaguar. The E-Type was the car people dreamed about. "
"Then British Leyland got hold of it, and the quality fell apart. Ford bought it in 1989, and tried to make it cheaper and bigger. "
"The X-Type was built on a Ford Mondeo, and it never found its own identity. Now the brand is known more for jokes than for speed. "
"Follow for the next one.")
disp = SCRIPT.split()
SPOKEN = {'1989': 'nineteen eighty nine', 'Mondeo': 'mon day oh', 'Leyland': 'lay land'}  # digits and unknown names; display keeps the real text
groups = [[re.sub(r"[^a-z']", "", p) for p in SPOKEN.get(re.sub(r"[^0-9a-zA-Z']", "", w), w.lower().replace('-', ' ')).split()] for w in disp]
norm = [p for g in groups for p in g]
d = Decoder(samprate=16000, bestpath=False, beam=1e-60, pbeam=1e-60, wbeam=1e-40)
d.set_align_text(" ".join(norm))
data = open(sys.argv[1], 'rb').read()
d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame/100, (s.end_frame+1)/100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ('<s>', '</s>', '<sil>', '[NOISE]')]
assert len(segs) == len(norm), (len(segs), len(norm))
out, k = [], 0
for i, g in enumerate(groups):
    part = segs[k:k + len(g)]; k += len(g)
    out.append(dict(w=disp[i], s=round(part[0][1], 2), e=round(part[-1][2], 2)))
json.dump(out, open(sys.argv[2], 'w'))
print(len(out), "words")
