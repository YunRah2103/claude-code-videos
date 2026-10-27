import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("You just bought a brand new car. Congrats. Now look at that price tag again. Here's the thing. "
"The second you drive it off the lot, it's a used car. And used cars sell for way less. Most new cars lose around "
"twenty percent of their value in the first year. That's thousands of dollars, just gone. You didn't really pay for "
"the car. You paid for the new car smell. And that smell is free now. So how do you dodge it? Buy a car that's a year "
"or two old. Somebody else takes the hit. You get the car. Is a new car worth it? Only if you like paying extra to be "
"the one who takes the hit. Tell me what you think in the comments.")
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
