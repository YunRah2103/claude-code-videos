"""Split one full voiceover take into script lines: align the whole take, cut line_NN.wav at word
boundaries and write words.json (times relative to each clip). Then run vo_timing.py as usual.

  ../../../.venv/bin/python split_take.py TAKE.wav OUTDIR
"""
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from align import align

HERE = Path(__file__).parent
PAD_IN, PAD_OUT = .08, .14


def main(take, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    lines = json.load(open(HERE / 'script.json'))
    words = align(take, ' '.join(lines))
    with wave.open(str(take)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    res, k = [], 0
    for i, line in enumerate(lines):
        ws = words[k:k + len(line.split())]; k += len(ws)
        a, b = max(0, ws[0]['s'] - PAD_IN), min(len(x) / sr, ws[-1]['e'] + PAD_OUT)
        with wave.open(str(out / f'line_{i:02d}.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(x[int(a * sr):int(b * sr)].tobytes())
        res.append([dict(w=q['w'], s=round(q['s'] - a, 2), e=round(q['e'] - a, 2)) for q in ws])
        print(i, f"{a:6.2f}-{b:6.2f}", ' '.join(q['w'] for q in ws))
    assert k == len(words)
    json.dump(res, open(HERE / 'words.json', 'w'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
