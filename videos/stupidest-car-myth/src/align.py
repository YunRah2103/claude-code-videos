import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Stop warming up your car for five minutes. That's an old method. Carburetor cars needed that. Modern cars don't. "
"Most manufacturers say thirty seconds is plenty. After that, drive gently. The engine warms up faster on the move. "
"Idling for ages just wastes fuel.")
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
