import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("Your airbag fires faster than you can blink. A crash sensor spots a sudden stop, and in about thirty milliseconds, "
"a gas charge fills the bag. Then it deflates just as fast, so you can see the road again. "
"That's why it only works with a seatbelt on. It's built to catch you, not hit you.")
disp = SCRIPT.split()
norm = [re.sub(r"[^a-z']", "", w.lower()) for w in disp]
d = Decoder(samprate=16000, bestpath=False)
EXTRA = {'deflates': 'D IH F L EY T S', 'airbag': 'EH R B AE G', 'seatbelt': 'S IY T B EH L T',
         'milliseconds': 'M IH L IH S EH K AH N D Z'}
for w in set(norm):
    if d.lookup_word(w) is None and w in EXTRA:
        d.add_word(w, EXTRA[w], True)
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
