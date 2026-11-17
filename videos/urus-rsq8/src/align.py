"""Force-align the two-speaker skit. Usage: python align.py tts.wav words.json"""
import sys, json, re, subprocess
from pocketsphinx import Decoder
LINES = [
 ("B", "Why is this Lamborghini an Audi?!"),
 ("S", "...Technically, a cousin."),
 ("B", "How much?"),
 ("S", "About two hundred and thirty thousand dollars."),
 ("B", "And the Audi?"),
 ("S", "About half."),
 ("B", "Same engine?"),
 ("S", "Four-litre twin-turbo V8. Even the engine covers swap."),
 ("B", "Same platform?"),
 ("S", "Same platform."),
 ("B", "So what's the extra hundred grand for?"),
 ("S", "A little more power."),
 ("B", "Who owns both?"),
 ("S", "Volkswagen Group."),
 ("B", "So I'm paying for the badge?"),
 ("S", "And the shape."),
 ("B", "Fine. Which one would you pick?"),
 ("S", "Let them decide."),
]
ALIAS = {"litre": ["liter"], "v8": ["v", "eight"]}   # dictionary spellings for the aligner
if __name__ == '__main__':
    disp, who, line = [], [], []
    for i, (spk, txt) in enumerate(LINES):
        for w in txt.split():
            disp.append(w); who.append(spk); line.append(i)
    norm, owner = [], []
    for i, w in enumerate(disp):
        for part in w.split('-'):
            p = re.sub(r"[^a-z0-9']", "", part.lower())
            for q in ALIAS.get(p, [p]):
                norm.append(q); owner.append(i)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', '16000',
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    d = Decoder(samprate=16000, bestpath=False)
    d.set_align_text(" ".join(norm))
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    segs = [(s.word, s.start_frame/100, (s.end_frame+1)/100) for s in d.seg()]
    segs = [s for s in segs if s[0] not in ('<s>', '</s>', '<sil>', '[NOISE]') and not s[0].startswith('+')]
    ok = sum(1 for (w, _, _), n in zip(segs, norm) if re.sub(r"\(\d+\)", "", w) == n)
    print(f"aligned {ok}/{len(norm)} = {100*ok/len(norm):.1f}%")
    assert len(segs) == len(norm), (len(segs), len(norm))
    out = []
    for k, (_, st, en) in enumerate(segs):
        i = owner[k]
        if out and out[-1]['i'] == i:
            out[-1]['e'] = round(en, 2); continue
        out.append(dict(i=i, w=disp[i], s=round(st, 2), e=round(en, 2), spk=who[i], line=line[i]))
    json.dump(out, open(sys.argv[2], 'w'))
