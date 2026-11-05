"""faster-whisper forced word timings on a real voiceover, mapped onto the exact script words.
    python shared/align_fw.py voiceover.wav words.json "script text"
Recognised words are matched in order (difflib); unmatched script words are split by character count between their
known neighbours and marked est=1. (Generalised from videos/speed-limit-deal-2d/src/align_words.py.)"""
import difflib, json, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel


def norm(w): return re.sub(r"[^a-z0-9]", '', w.lower())


def align(wav, out_json, script, model='small.en'):
    pcm = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', wav, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'],
                                       capture_output=True, check=True).stdout, np.float32)
    segs, _ = WhisperModel(model, device='cpu', compute_type='int8').transcribe(pcm, word_timestamps=True, initial_prompt=script, language='en')
    rec = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    words = script.split(); a, b = [norm(w) for w in words], [norm(r[0]) for r in rec]
    out = [None] * len(words)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size): out[blk.a + k] = (rec[blk.b + k][1], rec[blk.b + k][2], 0)
    known = [i for i, o in enumerate(out) if o]
    for i, o in enumerate(out):
        if o: continue
        lo = max([k for k in known if k < i], default=None); hi = min([k for k in known if k > i], default=None)
        t0 = out[lo][1] if lo is not None else 0.1; t1 = out[hi][0] if hi is not None else t0 + 0.5
        run = list(range((lo + 1) if lo is not None else 0, hi if hi is not None else len(words)))
        tot = sum(len(words[k]) for k in run); acc = sum(len(words[k]) for k in run if k < i)
        out[i] = (t0 + (t1 - t0) * acc / tot, t0 + (t1 - t0) * (acc + len(words[i])) / tot, 1)
    res = [dict(w=w, s=round(s, 2), e=round(e, 2), **({'est': 1} if est else {})) for w, (s, e, est) in zip(words, out)]
    json.dump(res, open(out_json, 'w'), indent=0)
    return res


if __name__ == '__main__':
    r = align(*sys.argv[1:4])
    print(f"{len(r)} words, estimated: {[w['w'] for w in r if w.get('est')]}, last end {r[-1]['e']}")
