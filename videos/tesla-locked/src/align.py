"""Force-align the two-speaker skit. Usage: python align.py tts.wav words.json"""
import sys, json, re, subprocess
from pocketsphinx import Decoder
LINES = [
 ("S", "Sir, your Tesla has a bigger battery than you paid for."),
 ("B", "What?"),
 ("S", "You bought the sixty. The battery inside is seventy-five."),
 ("B", "So where's the other fifteen?"),
 ("S", "Locked. By software."),
 ("B", "Then unlock it!"),
 ("S", "Sure. Four and a half to nine thousand dollars."),
 ("B", "For a battery I'm already carrying?!"),
 ("S", "Correct."),
 ("B", "No way."),
 ("B", "Tesla? There's a hurricane! I need thirty more miles to get out!"),
 ("S", "...Let me see what I can do."),
 ("S", "Done. Free. For owners in the storm's path."),
 ("B", "My car says seventy-five! Almost forty more miles!"),
 ("S", "Enjoy it."),
 ("B", "Thank you!"),
 ("S", "Until the sixteenth."),
 ("B", "Then what?"),
 ("S", "Locked again."),
]
if __name__ == '__main__':
    disp, who, line = [], [], []
    for i, (spk, txt) in enumerate(LINES):
        for w in txt.split():
            disp.append(w); who.append(spk); line.append(i)
    norm, owner = [], []
    for i, w in enumerate(disp):
        for part in w.split('-'):
            norm.append(re.sub(r"[^a-z']", "", part.lower())); owner.append(i)
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
