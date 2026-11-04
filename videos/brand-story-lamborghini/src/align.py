"""Word timings from the real voiceover with faster-whisper (word_timestamps), mapped onto the exact script words.
    python videos/brand-story-lamborghini/src/align.py  -> src/words.json  [{"w", "s", "e"}]"""
import json, os, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_voiceover import SCRIPT, FINAL, TAG

def norm(w): return re.sub(r'[^a-z0-9]', '', w.lower())

model = WhisperModel(os.environ.get('WHISPER_MODEL', 'small.en'), device='cpu', compute_type='int8')
pcm = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', FINAL, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'],
                                   capture_output=True, check=True).stdout, np.float32)
segs, _ = model.transcribe(pcm, word_timestamps=True, language='en', condition_on_previous_text=False)
hyp = [(norm(w.word), w.start, w.end) for s in segs for w in s.words]
words = SCRIPT.split()
# align script words to recognised words (difflib); 1963 / 350 may be heard as other tokens -> filled below
import difflib
out = [dict(w=w, s=None, e=None) for w in words]
sm = difflib.SequenceMatcher(None, [norm(w) for w in words], [h[0] for h in hyp], autojunk=False)
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        h = hyp[blk.b + k]; out[blk.a + k].update(s=round(h[1], 3), e=round(h[2], 3))
# fill unmatched words between matched neighbours by character count (flagged as estimated)
for i, o in enumerate(out):
    if o['s'] is None:
        a = max(x for x in range(i) if out[x]['e'] is not None) if i else None
        b = next((x for x in range(i, len(out)) if out[x]['s'] is not None), len(out))
        t0 = out[a]['e'] if a is not None else 0.1; t1 = out[b]['s'] if b < len(out) else hyp[-1][2]
        run = list(range((a + 1) if a is not None else 0, b)); tot = sum(len(out[x]['w']) for x in run)
        t = t0
        for x in run:
            d = (t1 - t0) * len(out[x]['w']) / tot; out[x].update(s=round(t, 3), e=round(t + d, 3), est=True); t += d
print('unmatched:', [o['w'] for o in out if o.get('est')], '| heard tail:', [h[0] for h in hyp[-8:]])
json.dump(out, open(os.path.join(HERE, f'words{TAG}.json'), 'w'), indent=0)
print(len(out), 'words;', sum(1 for o in out if o.get('est')), 'estimated; last end', out[-1]['e'])
print(' '.join(f"{o['w']}@{o['s']}" for o in out if o['w'][0].isupper() or o['w'][0].isdigit()))
