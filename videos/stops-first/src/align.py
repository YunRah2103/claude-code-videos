"""Transcribe the user's voiceover (faster-whisper, local) and align it to script.json -> words.json.

Every script word gets the start/end of the transcript word it matches; unmatched words are flagged
(`ok: false`) and interpolated. Exits 1 if fewer than 95% of script words are matched.
usage: python align.py VO.wav   (needs .venv with faster-whisper; model cached under out/hf)
"""
import difflib, json, os, re, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
NUM = {'twelve': '12', 'kilometres': 'kilometers', 'zero': '0'}
MIN_COVER = 0.95


def norm(w):
    w = re.sub(r"'s$", '', w.lower()); w = re.sub(r'[^a-z0-9]', '', w)
    return NUM.get(w, w)


def same(a, b): return a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def transcribe(wav):
    cache = Path(wav).with_suffix('.whisper.json')
    if cache.exists(): return json.load(open(cache))
    os.environ.setdefault('HF_HOME', str(HERE.parents[2] / 'out/hf'))
    from faster_whisper import WhisperModel
    a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(wav), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                                     capture_output=True, check=True).stdout, np.int16).astype(np.float32) / 32768
    seg, _ = WhisperModel('small.en', compute_type='int8').transcribe(a, word_timestamps=True)
    ws = [dict(w=w.word.strip(), s=round(float(w.start), 2), e=round(float(w.end), 2)) for s in seg for w in s.words]
    json.dump(ws, open(cache, 'w')); return ws


def align(script, heard):
    a, b = [norm(w) for w in script], [norm(w['w']) for w in heard]
    out = [dict(w=w, s=None, e=None, ok=False) for w in script]
    for tag, i0, i1, j0, j1 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i1 - i0 == j1 - j0):
            for i, j in zip(range(i0, i1), range(j0, j1)):
                if same(a[i], b[j]): out[i].update(s=heard[j]['s'], e=heard[j]['e'], ok=True)
    end = heard[-1]['e']
    for i, o in enumerate(out):                      # unmatched: place between neighbours (or after the last word)
        if not o['ok']:
            prev = next((out[k]['e'] for k in range(i - 1, -1, -1) if out[k]['e'] is not None), 0.0)
            o['s'] = o['e'] = round(max(prev, end if i > len(out) - 4 else prev), 2)
    return out


if __name__ == '__main__':
    script = json.load(open(HERE / 'script.json'))[0].split()
    heard = transcribe(sys.argv[1])
    words = align(script, heard)
    json.dump([words], open(HERE / 'words.json', 'w'))
    ok = sum(w['ok'] for w in words); cover = ok / len(words)
    print('transcript:', ' '.join(w['w'] for w in heard))
    print(f'aligned {ok}/{len(words)} script words = {cover:.1%}; missing:', [w['w'] for w in words if not w['ok']])
    sys.exit(0 if cover >= MIN_COVER else 1)
