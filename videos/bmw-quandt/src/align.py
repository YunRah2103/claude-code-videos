import sys, json, re
from pocketsphinx import Decoder
SCRIPT = ("BMW almost became part of Mercedes. Back in 1959, BMW was in serious trouble. The company was barely holding on, "
"and the story goes that Mercedes-Benz was ready to take it over. Then one man stepped in. Herbert Quandt. He pushed back, "
"bought more of the company, and BMW stayed BMW. Whether it went exactly like the legend, nobody agrees. But one thing's true. "
"A car brand you know today almost wasn't here at all.")  # the supplied audio ends here
disp = SCRIPT.split()
SPOKEN = {'1959': 'nineteen fifty nine'}  # digits cannot be aligned; display text keeps the digits
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
print(len(out), "words;", " ".join(f"{o['w']}[{o['s']}-{o['e']}]" for o in out))
