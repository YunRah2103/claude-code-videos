"""Force-align a voiceover to its script with pocketsphinx and write words.json ([{w, s, e}, ...]).

Display words can be spoken as several tokens ('1959' -> 'nineteen fifty nine'): pass SAY={'1959': '...'}.
Out-of-vocabulary names get phones through EXTRA={'issigonis': 'IH S IH G OW N IH S'}.
"""
import json, re, subprocess
from pocketsphinx import Decoder


def norm(w): return re.sub(r"[^a-z']", '', w.lower())


def align(script, mp3, out_json, say=None, extra=None):
    say = say or {}
    disp = script.split()
    spoken = [say.get(w.strip('.,:!?'), norm(w)).split() for w in disp]
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp3, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    d = Decoder(samprate=16000, bestpath=False)
    for w, ph in (extra or {}).items():
        d.add_word(w, ph, True)
    d.set_align_text(' '.join(t for s in spoken for t in s))
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    segs = [(s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg() if s.word not in ('<s>', '</s>', '<sil>', '[NOISE]')]
    assert len(segs) == sum(map(len, spoken)), (len(segs), sum(map(len, spoken)))
    out, j = [], 0
    for w, s in zip(disp, spoken):
        out.append(dict(w=w, s=round(segs[j][0], 2), e=round(segs[j + len(s) - 1][1], 2))); j += len(s)
    json.dump(out, open(out_json, 'w'))
    print(' '.join(f"{o['w']}[{o['s']}]" for o in out))
    return out
