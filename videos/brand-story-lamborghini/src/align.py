"""Word timings from the real voiceover with faster-whisper (word_timestamps), mapped onto the exact script words.
    python videos/brand-story-lamborghini/src/align.py  -> src/words.json  [{"w", "s", "e"}]"""
import json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_voiceover import SCRIPT, FINAL

def norm(w): return re.sub(r'[^a-z0-9]', '', w.lower())

model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small.en'), device='cpu', compute_type='int8')
pcm = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', FINAL, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'],
                                   capture_output=True, check=True).stdout, np.float32)
segs, _ = model.transcribe(pcm, word_timestamps=True, language='en', initial_prompt=SCRIPT)
hyp = [(norm(w.word), w.start, w.end) for s in segs for w in s.words]
words = SCRIPT.split()
# greedy match script words to recognised words; 1963 / 350 may be heard as several tokens
out, j = [], 0
for i, w in enumerate(words):
    n = norm(w); k = j
    while k < len(hyp) and k < j + 4 and hyp[k][0] != n: k += 1
    if k < len(hyp) and hyp[k][0] == n: out.append(dict(w=w, s=round(hyp[k][1], 3), e=round(hyp[k][2], 3))); j = k + 1
    else: out.append(dict(w=w, s=None, e=None))
# fill unmatched words between matched neighbours by character count (flagged as estimated)
for i, o in enumerate(out):
    if o['s'] is None:
        a = max(x for x in range(i) if out[x]['e'] is not None) if i else None
        b = next(x for x in range(i, len(out)) if out[x]['s'] is not None)
        t0 = out[a]['e'] if a is not None else 0.1; t1 = out[b]['s']
        run = list(range((a + 1) if a is not None else 0, b)); tot = sum(len(out[x]['w']) for x in run)
        t = t0
        for x in run:
            d = (t1 - t0) * len(out[x]['w']) / tot; out[x].update(s=round(t, 3), e=round(t + d, 3), est=True); t += d
json.dump(out, open(os.path.join(HERE, 'words.json'), 'w'), indent=0)
print(len(out), 'words;', sum(1 for o in out if o.get('est')), 'estimated; last end', out[-1]['e'])
print(' '.join(f"{o['w']}@{o['s']}" for o in out if o['w'][0].isupper() or o['w'][0].isdigit()))
