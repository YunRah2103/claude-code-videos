"""Word timings for the shipped voiceover: faster-whisper (base.en, word_timestamps) on out/speed-limit-deal-3d/voiceover.wav,
mapped onto the exact script words (recognised words matched in order; unmatched script words interpolated, marked est=1)."""
import difflib, json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from voiceover import SCRIPT, OUT

def norm(w): return re.sub(r"[^a-z0-9]", '', w.lower().replace('one hundred fifty-five', '155'))
pcm = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(OUT, 'voiceover.wav'), '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'],
                                    capture_output=True, check=True).stdout, np.float32)
segs, _ = WhisperModel('base.en', device='cpu', compute_type='int8').transcribe(
    pcm, word_timestamps=True, initial_prompt=SCRIPT, language='en')
rec = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
script = SCRIPT.split()
a, b = [norm(w) for w in script], [norm(w[0]) for w in rec]
out = [None] * len(script)
for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
    for k in range(blk.size): out[blk.a + k] = (rec[blk.b + k][1], rec[blk.b + k][2], 0)
known = [i for i, o in enumerate(out) if o]
for i, o in enumerate(out):                      # fill gaps by character count between known neighbours
    if o: continue
    lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
    t0 = out[lo][1] if lo is not None else 0.1; t1 = out[hi][0] if hi is not None else t0 + 0.5
    run = list(range((lo + 1) if lo is not None else 0, hi if hi is not None else len(script)))
    tot = sum(len(script[k]) for k in run); acc = sum(len(script[k]) for k in run if k < i)
    out[i] = (t0 + (t1 - t0) * acc / tot, t0 + (t1 - t0) * (acc + len(script[i])) / tot, 1)
words = [dict(w=w, s=round(s, 2), e=round(e, 2), **({'est': 1} if est else {})) for w, (s, e, est) in zip(script, out)]
json.dump(words, open(os.path.join(HERE, 'words.json'), 'w'), indent=0)
print('recognised:', ' '.join(r[0] for r in rec)); print('estimated:', [w['w'] for w in words if w.get('est')])
print(' '.join(f"{w['w']}@{w['s']}" for w in words))
