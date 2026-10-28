import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Crumpling the front of a car on purpose is how it keeps you alive. Watch. Two identical cars hit "
"the same wall at the same speed. This one stays solid. This one folds like an accordion. That fold is a "
"crumple zone. It soaks up the energy of the crash, so less of it reaches you. The middle of the car, the "
"part you sit in, is built to stay rigid. So the car gets destroyed, and you don't.")
disp = SCRIPT.split()
norm = [re.sub(r"[^a-z']", "", w.lower()) for w in disp]
d = Decoder(samprate=16000, bestpath=False)
d.add_word('crumpling', 'K R AH M P L IH NG', True)
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
