"""Phase 2: place voiceover lines on the beat layout, write real word times into beats.json,
then build the audio mix (VO + sfx) for the render.

  ../../../.venv/bin/python align.py ../../../out/tyre-490/vo     # -> words.json
  python vo_timing.py ../../../out/tyre-490/vo                    # -> beats.json (+ render.py DUR)
  python vo_timing.py ../../../out/tyre-490/vo mix OUT.wav        # after timing: VO + sfx mix
"""
import json, math, re, sys, wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
GAP, LEAD0, TAIL = .12, .2, .9          # min gap between lines, first-line start, hold after last word
sys.path.insert(0, str(HERE.parent.parent / 'new-car-trap/src'))


def clip_len(p):
    with wave.open(str(p)) as w: return w.getnframes() / w.getframerate()


def timing(vo):
    B = json.load(open(HERE / 'beats.json'))
    lines = json.load(open(HERE / 'script.json'))
    words = json.load(open(HERE / 'words.json'))
    brief = [b.get('brief_start', b['start']) for b in B['beats']]
    assert len(brief) == len(lines) == len(words), 'one script line per beat'
    offs, end = [], 0.0
    for i, ws in enumerate(words):
        first = ws[0]['s']
        start = LEAD0 if i == 0 else max(end + GAP - first, brief[i] - first)   # line i speaks on beat i
        offs.append(round(start, 3))
        end = start + ws[-1]['e']
    flat, anchors = [], []
    for o, ws in zip(offs, words):
        anchors.append(len(flat))
        flat += [{'w': w['w'], 't': round(o + w['s'], 3), 'e': round(o + w['e'], 3), 'est': False} for w in ws]
    dur = math.ceil((end + TAIL) * 30) / 30
    for b, a, s in zip(B['beats'], anchors, brief):
        b['brief_start'], b['anchor_word'] = s, a
    B['beats'][0]['start'] = 0.0
    for b in B['beats'][1:]:
        b['start'] = flat[b['anchor_word']]['t']
    B.update(words=flat, dur=round(dur, 3), vo_offsets=offs, script=' '.join(lines),
             note='Phase 2: word times from PocketSphinx alignment of the Fenrir clips; beats start on their anchor word.')
    json.dump(B, open(HERE / 'beats.json', 'w'), indent=1)
    src = (HERE / 'render.py').read_text()
    (HERE / 'render.py').write_text(re.sub(r'^DUR = [0-9.]+', f'DUR = {round(dur, 3)}', src, count=1, flags=re.M))
    for b in B['beats']:
        print(f"{b['id']:10s} {b['start']:6.2f}  (brief {b['brief_start']})")
    print('voice ends', round(end, 2), 's -> DUR', round(dur, 3))


def mix(vo, out):
    import sfx
    import render as r
    B = json.load(open(HERE / 'beats.json'))
    SR = sfx.SR
    n = int(SR * r.DUR)
    voice = np.zeros(n)
    for i, o in enumerate(B['vo_offsets']):
        with wave.open(str(Path(vo) / f'line_{i:02d}.wav')) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.0
            x = np.interp(np.arange(int(len(x) * SR / w.getframerate())) * w.getframerate() / SR, np.arange(len(x)), x)
        a = int(o * SR); voice[a:a + len(x)] += x[:n - a]
    cues = [(0.0, 'boom', .7), (r.TC, 'vroom', .6), (r.t6, 'vroom', .6), (r.STAMP, 'stamp', .9),
            (r.EARLY[0], 'buzzer', .25), (r.t5 + .15, 'buzzer', .3), (r.t6 + 1.0, 'ding', .25), (r.t6 + 1.75, 'ding', .25)]
    cues += [(t - .15, 'whoosh', .5) for t in r.TRANSITIONS if 0 < t - .15 < r.DUR - .4]
    cues += [(k, 'thump', .3) for k in r.KICKS]
    fx = sfx.render(sorted(cues), r.DUR)[:n]
    fx = fx / (np.abs(fx).max() + 1e-9) * .5
    duck = 1 - .45 * np.clip(np.convolve(np.abs(voice) > .02, np.ones(SR // 10) / (SR // 10), 'same'), 0, 1)
    m = voice * .9 + fx * duck
    m = np.clip(m / (np.abs(m).max() + 1e-9) * .95, -1, 1)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((m * 32767).astype(np.int16).tobytes())
    print('mix', out, round(len(m) / SR, 2), 's')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'mix':
        mix(sys.argv[1], sys.argv[3])
    else:
        timing(sys.argv[1])
