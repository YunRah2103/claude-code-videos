import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Those grooves on your tyres aren't decoration. In the rain, the tread pushes water out from under "
"the rubber, so it can grip the road. Worn tyres can't do that, and the car can start to slide. Most places the "
"legal minimum is 1.6 millimetres.")
SAY = {'tyres': 'tires', '1.6': 'one point six', 'millimetres': 'millimeters'}
disp = SCRIPT.split()
key = lambda w: re.sub(r"[^a-z0-9.']", "", w.lower()).strip('.')
parts = [SAY.get(key(w), key(w)).split() for w in disp]
norm = [p for ps in parts for p in ps]
d = Decoder(samprate=16000, bestpath=False)
d.set_align_text(" ".join(norm))
data = open(sys.argv[1], 'rb').read()
d.start_utt(); d.process_raw(data, full_utt=True); d.end_utt()
segs = [(s.word, s.start_frame/100, (s.end_frame+1)/100) for s in d.seg()]
segs = [s for s in segs if s[0] not in ('<s>', '</s>', '<sil>', '[NOISE]')]
assert len(segs) == len(norm), (len(segs), len(norm))
out, j = [], 0
for w, ps in zip(disp, parts):  # merge multi-word spoken forms back into one display word
    out.append(dict(w=w, s=round(segs[j][1], 2), e=round(segs[j + len(ps) - 1][2], 2))); j += len(ps)
assert len(out) == len(disp), (len(out), len(disp))
json.dump(out, open(sys.argv[2], 'w'))
print(" ".join(f"{o['w']}[{o['s']}]" for o in out))
