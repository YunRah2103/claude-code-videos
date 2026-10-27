import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Your car roof looks pretty thin, right? Like it couldn't hold much at all. When a car rolls over, "
"that roof is the first thing that hits the ground. So engineers build it to carry the weight of the whole car. "
"Strong pillars of steel, and a cabin that keeps its shape. The outside can get crushed, but the space you're "
"sitting in, it stays intact. Honestly, that's kind of impressive. Tell me in the comments if you knew that.")
disp = SCRIPT.split()
norm = [re.sub(r"[^a-z']", "", w.lower()) for w in disp]
d = Decoder(samprate=16000, bestpath=False)
d.set_align_text(" ".join(norm))
data = open(sys.argv[1], 'rb').read()
d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame/100, (s.end_frame+1)/100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ('<s>', '</s>', '<sil>', '[NOISE]')]
out = []
for i, (w, st, en) in enumerate(segs):
    out.append(dict(w=disp[i], s=round(st, 2), e=round(en, 2)))
assert len(out) == len(disp), (len(out), len(disp))
json.dump(out, open(sys.argv[2], 'w'))
print(" ".join(f"{o['w']}[{o['s']}]" for o in out))
